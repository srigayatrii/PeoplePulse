import pandas as pd

from hr_pipeline.transform import join_pandas
from hr_pipeline.validate import (ValidationResult, rule_contracts_expiring, rule_no_negative_salaries,
                                  rule_payroll_without_employee, rule_unique_ids, validate)


def test_negative_salary_is_error():
    df = pd.DataFrame({"employee_id": ["EMP-0001", "EMP-0002"], "gross_pay_mxn": [100.0, -5.0]})
    res = ValidationResult()
    rule_no_negative_salaries(df, res)
    assert [f["employee_id"] for f in res.errors] == ["EMP-0002"]


def test_duplicate_ids_are_error():
    df = pd.DataFrame({"employee_id": ["EMP-0001", "EMP-0001", "EMP-0002"]})
    res = ValidationResult()
    rule_unique_ids(df, res, "employees")
    assert len(res.errors) == 1 and res.errors[0]["employee_id"] == "EMP-0001"


def test_payroll_without_employee_is_flagged():
    emp = pd.DataFrame({"employee_id": ["EMP-0001"]})
    pay = pd.DataFrame({"employee_id": ["EMP-0001", "EMP-9001"], "gross_pay_mxn": [1.0, 2.0]})
    res = ValidationResult()
    rule_payroll_without_employee(pay, emp, res)
    assert [f["employee_id"] for f in res.findings] == ["EMP-9001"]
    assert res.findings[0]["severity"] == "WARNING"


def test_contract_expiring_window(as_of):
    master = pd.DataFrame({
        "employee_id": ["A", "B", "C", "D"],
        "termination_date": [pd.NaT, pd.NaT, pd.NaT, pd.Timestamp("2026-01-01")],
        "contract_end_date": [as_of + pd.Timedelta(days=10), as_of + pd.Timedelta(days=45),
                              pd.NaT, as_of + pd.Timedelta(days=5)],
    })
    res = ValidationResult()
    rule_contracts_expiring(master, as_of, res)
    assert [f["employee_id"] for f in res.findings] == ["A"]  # B outside window, C none, D terminated


def test_validate_on_synthetic_data_catches_seeded_issues(cleaned, as_of):
    clean, _ = cleaned
    master = join_pandas(clean["employees"], clean["payroll"], clean["compliance"])
    res = validate(clean, master, as_of)
    rules = {f["rule"] for f in res.findings}
    assert "no_negative_salary" in rules          # seeded negative salary
    assert "payroll_row_without_employee" in rules  # seeded EMP-9xxx orphans
    assert "unique_employee_id" not in rules        # cleaning removed duplicates
