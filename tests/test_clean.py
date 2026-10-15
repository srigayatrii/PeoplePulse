import pandas as pd

from hr_pipeline.clean import DataQualityLog, clean_payroll, normalize_id, to_number


def test_normalize_id_variants():
    assert normalize_id("  emp0012 ") == "EMP-0012"
    assert normalize_id("EMP-0012\t") == "EMP-0012"
    assert normalize_id("emp-12") == "EMP-0012"
    assert normalize_id("") is None
    assert normalize_id(None) is None
    assert normalize_id(float("nan")) is None


def test_to_number_handles_separators_and_blanks():
    assert to_number("48,500.00") == 48500.0
    assert to_number("$1,000") == 1000.0
    assert to_number("") is None
    assert to_number("abc") is None


def test_clean_payroll_dedupes_and_drops_missing_ids():
    raw = pd.DataFrame({
        "EmpID": ["EMP-0001", " emp-0001 ", "EMP0002", None, ""],
        "Nombre": ["A", "A", "B", "C", "D"],
        "Depto": [" engineering ", "ENGINEERING", "Risk", "Risk", "Risk"],
        "Sede": ["CDMX"] * 5, "SalarioBase": ["10"] * 5, "Variable": ["0"] * 5,
        "Bruto": ["10", "11", "1,000", "5", "5"], "BrutoMesAnterior": ["9"] * 5, "Periodo": ["2026-07"] * 5,
    })
    log = DataQualityLog()
    out = clean_payroll(raw, log)
    assert list(out["employee_id"]) == ["EMP-0001", "EMP-0002"]
    assert set(out["department"]) == {"Engineering", "Risk"}
    assert out.loc[out["employee_id"] == "EMP-0002", "gross_pay_mxn"].item() == 1000.0
    rules = {e["rule"]: e["rows_affected"] for e in log.entries}
    assert rules["missing_employee_id_dropped"] == 2
    assert rules["duplicate_employee_id_kept_first"] == 1


def test_cleaned_sources_have_unique_ids(cleaned):
    clean, log = cleaned
    for name in ("employees", "payroll", "compliance"):
        assert clean[name]["employee_id"].is_unique, name
        assert clean[name]["employee_id"].notna().all(), name
    assert not log.to_frame().empty  # dirty input must produce a log
