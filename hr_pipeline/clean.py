"""Cleaning: canonical keys, trimming, casing, dedupe, type coercion.

Every correction is recorded in a DataQualityLog so the report can show
what the pipeline changed and why (auditability is the point).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class DataQualityLog:
    entries: list[dict] = field(default_factory=list)

    def add(self, source: str, rule: str, affected: int, detail: str = "") -> None:
        if affected:
            self.entries.append({"source": source, "rule": rule, "rows_affected": int(affected), "detail": detail})

    def to_frame(self) -> pd.DataFrame:
        cols = ["source", "rule", "rows_affected", "detail"]
        return pd.DataFrame(self.entries, columns=cols)


PAYROLL_KEY_MAP = {
    "EmpID": "employee_id",
    "Nombre": "full_name",
    "Depto": "department",
    "Sede": "site",
    "SalarioBase": "base_salary_mxn",
    "Variable": "variable_pay_mxn",
    "Bruto": "gross_pay_mxn",
    "BrutoMesAnterior": "gross_pay_prev_mxn",
    "Periodo": "period",
}
COMPLIANCE_KEY_MAP = {"emp_id": "employee_id"}

_ID_RE = re.compile(r"^EMP-?(\d{1,4})$", re.IGNORECASE)


def normalize_id(value) -> str | None:
    """'  emp0012 ' -> 'EMP-0012'. Returns None for blanks / unparsable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    m = _ID_RE.match(s)
    return f"EMP-{int(m.group(1)):04d}" if m else s.upper()


def to_number(value) -> float | None:
    """'48,500.00' -> 48500.0 ; '' -> None."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace("$", "")
    if not s or s.lower() in {"nan", "none"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _title_case_trim(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.title()


def clean_employees(df: pd.DataFrame, log: DataQualityLog) -> pd.DataFrame:
    df = df.copy()
    before = len(df)
    df["employee_id"] = df["employee_id"].map(normalize_id)
    df = df.drop_duplicates("employee_id")
    log.add("employees", "duplicate_employee_id_removed", before - len(df))
    for col in ("hire_date", "termination_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["monthly_salary_mxn"] = pd.to_numeric(df["monthly_salary_mxn"], errors="coerce")
    df["imss_registered"] = df["imss_registered"].astype(bool)
    df["department"] = _title_case_trim(df["department"])
    return df.reset_index(drop=True)


def clean_payroll(df: pd.DataFrame, log: DataQualityLog) -> pd.DataFrame:
    df = df.rename(columns=PAYROLL_KEY_MAP).copy()

    raw_ids = df["employee_id"]
    df["employee_id"] = raw_ids.map(normalize_id)
    changed = int((raw_ids.fillna("").astype(str) != df["employee_id"].fillna("")).sum())
    log.add("payroll", "employee_id_normalized", changed, "trim / casing / EMP-#### padding")

    missing = df["employee_id"].isna()
    log.add("payroll", "missing_employee_id_dropped", int(missing.sum()))
    df = df[~missing]

    raw_dept = df["department"]
    df["department"] = _title_case_trim(raw_dept)
    log.add("payroll", "department_casing_whitespace_fixed", int((raw_dept != df["department"]).sum()))
    df["site"] = df["site"].astype(str).str.strip()
    df["full_name"] = df["full_name"].astype(str).str.strip()

    for col in ("base_salary_mxn", "variable_pay_mxn", "gross_pay_mxn", "gross_pay_prev_mxn"):
        raw = df[col]
        df[col] = raw.map(to_number)
        non_numeric_fixed = int(((raw.astype(str).str.contains(",|\\$")) & df[col].notna()).sum())
        log.add("payroll", f"{col}_numeric_coercion", non_numeric_fixed, "thousands separators / currency symbols")
        log.add("payroll", f"{col}_unparseable_set_null", int(df[col].isna().sum()))

    before = len(df)
    df = df.drop_duplicates()
    log.add("payroll", "exact_duplicate_rows_removed", before - len(df))
    before = len(df)
    df = df.drop_duplicates("employee_id", keep="first")
    log.add("payroll", "duplicate_employee_id_kept_first", before - len(df))
    return df.reset_index(drop=True)


def clean_compliance(df: pd.DataFrame, log: DataQualityLog) -> pd.DataFrame:
    df = df.rename(columns=COMPLIANCE_KEY_MAP).copy()
    df["employee_id"] = df["employee_id"].map(normalize_id)
    for col in ("imss_status", "infonavit_status"):
        df[col] = df[col].astype(str).str.strip().str.upper()
    for col in ("contract_end_date", "last_audit"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    before = len(df)
    df = df.drop_duplicates("employee_id")
    log.add("compliance", "duplicate_employee_id_removed", before - len(df))
    return df.reset_index(drop=True)


def clean_all(raw: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], DataQualityLog]:
    log = DataQualityLog()
    return {
        "employees": clean_employees(raw["employees"], log),
        "payroll": clean_payroll(raw["payroll"], log),
        "compliance": clean_compliance(raw["compliance"], log),
    }, log
