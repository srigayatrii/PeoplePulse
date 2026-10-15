#!/usr/bin/env python3
"""CLI entry point.

    python3 run_pipeline.py --period 2026-07 [--regenerate] [--engine pandas|sql]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from data.generate_sample_data import generate  # noqa: E402
from hr_pipeline.clean import clean_all  # noqa: E402
from hr_pipeline.dashboard import build_dashboard  # noqa: E402
from hr_pipeline.extract import extract_all  # noqa: E402
from hr_pipeline.report import write_report  # noqa: E402
from hr_pipeline.transform import build_metrics, join_pandas, join_sql, period_bounds  # noqa: E402
from hr_pipeline.validate import validate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HR data pipeline: extract -> clean -> transform -> validate -> report")
    ap.add_argument("--period", default="2026-07", help="Payroll period YYYY-MM")
    ap.add_argument("--raw-dir", default=ROOT / "data" / "raw", type=Path)
    ap.add_argument("--out-dir", default=ROOT / "output", type=Path)
    ap.add_argument("--engine", choices=["pandas", "sql"], default="pandas", help="Join engine for the master table")
    ap.add_argument("--regenerate", action="store_true", help="Force regeneration of synthetic sources")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when validation errors are found")
    args = ap.parse_args(argv)
    t0 = time.perf_counter()

    # 0. generate
    payroll_file = args.raw_dir / f"payroll_{args.period.replace('-', '_')}.csv"
    needed = [args.raw_dir / "employees.xlsx", payroll_file, args.raw_dir / "compliance.sqlite"]
    if args.regenerate or not all(p.exists() for p in needed):
        generate(args.period, raw_dir=args.raw_dir)
        print(f"[generate]  synthetic sources written to {args.raw_dir}")

    # 1. extract
    raw = extract_all(args.raw_dir, args.period)
    print(f"[extract]   employees={len(raw['employees'])}  payroll={len(raw['payroll'])}  compliance={len(raw['compliance'])}")

    # 2. clean
    clean, dq = clean_all(raw)
    print(f"[clean]     employees={len(clean['employees'])}  payroll={len(clean['payroll'])}  "
          f"compliance={len(clean['compliance'])}  corrections_logged={int(dq.to_frame()['rows_affected'].sum())}")

    # 3. transform (both engines must agree)
    m_pd = join_pandas(clean["employees"], clean["payroll"], clean["compliance"])
    m_sql = join_sql(clean["employees"], clean["payroll"], clean["compliance"])
    assert len(m_pd) == len(m_sql) == len(clean["employees"]), "join engines disagree"
    metrics = build_metrics(clean, args.period, engine=args.engine)
    s = metrics.summary
    print(f"[transform] engine={args.engine}  master_rows={len(metrics.master)}  (pandas == sql: OK)")
    print(f"            active_headcount={s['active_headcount']}  turnover={s['monthly_turnover_pct']}%  "
          f"avg_tenure={s['average_tenure_years']}y  payroll_variance={s['payroll_variance_pct']:+}%")

    # 4. validate
    as_of = pd.Timestamp(period_bounds(args.period)[1])
    vres = validate(clean, metrics.master, as_of)
    n_err = len(vres.errors)
    print(f"[validate]  findings={len(vres.findings)}  errors={n_err}  warnings={len(vres.findings) - n_err}")
    for f in vres.errors:
        print(f"            ERROR {f['rule']}: {f['employee_id']} -> {f['detail']}")

    # 5. report + 6. dashboard
    report = write_report(metrics, dq.to_frame(), vres.to_frame(), args.out_dir, args.period)
    dash = build_dashboard(metrics, args.out_dir, args.period)
    print(f"[report]    {report}")
    print(f"[dashboard] {dash}")
    print(f"\nDone in {time.perf_counter() - t0:.1f}s  |  compliance alerts: {s['compliance_alerts']} "
          f"({s['compliance_alerts_high']} high)  |  payroll rows without employee: {s['payroll_rows_without_employee']}")
    return 1 if (args.strict and n_err) else 0


if __name__ == "__main__":
    sys.exit(main())
