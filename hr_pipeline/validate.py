"""Business rules checked after the join. Each rule yields zero or more findings."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    findings: list[dict] = field(default_factory=list)

    def add(self, rule: str, severity: str, employee_id: str | None, detail: str) -> None:
        self.findings.append({"rule": rule, "severity": severity, "employee_id": employee_id, "detail": detail})

    @property
    def errors(self) -> list[dict]:
        return [f for f in self.findings if f["severity"] == "ERROR"]

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.findings, columns=["rule", "severity", "employee_id", "detail"])


def rule_unique_ids(df: pd.DataFrame, res: ValidationResult, source: str) -> None:
    dup = df[df["employee_id"].duplicated(keep=False)]
    for eid in dup["employee_id"].unique():
        res.add("unique_employee_id", "ERROR", eid, f"duplicated in {source}")


def rule_no_negative_salaries(df: pd.DataFrame, res: ValidationResult) -> None:
    cols = [c for c in ("monthly_salary_mxn", "gross_pay_mxn", "base_salary_mxn") if c in df.columns]
    for col in cols:
        for _, r in df[df[col].lt(0)].iterrows():
            res.add("no_negative_salary", "ERROR", r["employee_id"], f"{col} = {r[col]}")


def rule_payroll_without_employee(payroll: pd.DataFrame, employees: pd.DataFrame, res: ValidationResult) -> None:
    orphans = payroll[~payroll["employee_id"].isin(employees["employee_id"])]
    for _, r in orphans.iterrows():
        res.add("payroll_row_without_employee", "WARNING", r["employee_id"],
                f"paid {r.get('gross_pay_mxn')} MXN but not found in HRIS")


def rule_contracts_expiring(master: pd.DataFrame, as_of: pd.Timestamp, res: ValidationResult, days: int = 30) -> None:
    active = master["termination_date"].isna() | (master["termination_date"] > as_of)
    window = master["contract_end_date"].between(as_of, as_of + pd.Timedelta(days=days))
    for _, r in master[active & window].iterrows():
        res.add("contract_expiring_30d", "WARNING", r["employee_id"],
                f"contract ends {r['contract_end_date'].date()}")


def rule_hire_before_termination(master: pd.DataFrame, res: ValidationResult) -> None:
    bad = master["termination_date"].notna() & (master["termination_date"] < master["hire_date"])
    for _, r in master[bad].iterrows():
        res.add("termination_after_hire", "ERROR", r["employee_id"], "termination_date < hire_date")


def validate(clean: dict[str, pd.DataFrame], master: pd.DataFrame, as_of: pd.Timestamp) -> ValidationResult:
    res = ValidationResult()
    rule_unique_ids(clean["employees"], res, "employees")
    rule_unique_ids(clean["payroll"], res, "payroll")
    rule_no_negative_salaries(clean["employees"], res)
    rule_no_negative_salaries(clean["payroll"], res)
    rule_payroll_without_employee(clean["payroll"], clean["employees"], res)
    rule_contracts_expiring(master, as_of, res)
    rule_hire_before_termination(master, res)
    return res
