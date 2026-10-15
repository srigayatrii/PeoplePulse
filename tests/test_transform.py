import pandas as pd

from hr_pipeline.transform import build_metrics, join_pandas, join_sql


def test_left_join_preserves_employee_count(cleaned):
    clean, _ = cleaned
    master = join_pandas(clean["employees"], clean["payroll"], clean["compliance"])
    assert len(master) == len(clean["employees"])
    assert master["employee_id"].is_unique
    # orphan payroll rows (EMP-9xxx) must NOT appear in the master
    assert not master["employee_id"].str.startswith("EMP-9").any()


def test_sql_and_pandas_joins_agree(cleaned):
    clean, _ = cleaned
    a = join_pandas(clean["employees"], clean["payroll"], clean["compliance"])
    b = join_sql(clean["employees"], clean["payroll"], clean["compliance"])
    assert len(a) == len(b)
    assert list(a["employee_id"]) == list(b["employee_id"])
    pd.testing.assert_series_equal(a["gross_pay_mxn"].fillna(-1), b["gross_pay_mxn"].fillna(-1), check_names=False)
    assert a["imss_status"].isna().sum() == b["imss_status"].isna().sum()


def test_metrics_are_consistent(cleaned):
    clean, _ = cleaned
    m = build_metrics(clean, "2026-07")
    s = m.summary
    total_row = m.headcount[m.headcount["department"] == "Total"].iloc[0]
    assert int(total_row["Total"]) == s["active_headcount"]
    assert len(m.turnover) == 12
    assert (m.turnover["turnover_rate_pct"] >= 0).all()
    assert s["average_tenure_years"] > 0
    assert s["payroll_rows_without_employee"] == len(m.unmatched_payroll)
    assert set(m.compliance_gaps["severity"]) <= {"HIGH", "MEDIUM", "LOW"}
