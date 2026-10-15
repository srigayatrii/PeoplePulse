"""Readers for the three heterogeneous sources (xlsx, csv, sqlite)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def read_employees(path: Path | str, sheet: str = "Employees") -> pd.DataFrame:
    """HRIS export (Excel)."""
    return pd.read_excel(path, sheet_name=sheet)


def read_payroll(path: Path | str) -> pd.DataFrame:
    """Payroll export (CSV). Everything is read as text: cleaning coerces types."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_compliance(path: Path | str, table: str = "compliance") -> pd.DataFrame:
    """Compliance database (SQLite)."""
    with sqlite3.connect(path) as con:
        return pd.read_sql(f"SELECT * FROM {table}", con)


def extract_all(raw_dir: Path | str, period: str) -> dict[str, pd.DataFrame]:
    raw_dir = Path(raw_dir)
    return {
        "employees": read_employees(raw_dir / "employees.xlsx"),
        "payroll": read_payroll(raw_dir / f"payroll_{period.replace('-', '_')}.csv"),
        "compliance": read_compliance(raw_dir / "compliance.sqlite"),
    }
