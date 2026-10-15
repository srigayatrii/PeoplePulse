# PeoplePulse — HR Data Analytics Pipeline

**People data as a product:** an automated ETL pipeline that combines three messy HR data sources (HRIS export, payroll CSV, and compliance database) into a monthly workforce report and interactive dashboard covering headcount, turnover, tenure, payroll variance, and compliance gaps.

This project demonstrates a reproducible approach to HR data processing, validation, and reporting using synthetic data.

> All data in this project is synthetic. No real employee records or company data are used.

---

## What It Does

Run the pipeline with one command:

```bash
python run_pipeline.py --period 2026-07
```

1. **Generate:** Creates three heterogeneous, deliberately dirty data sources on the first run.
2. **Extract:** Reads Excel, CSV, and SQLite data into Pandas.
3. **Clean:** Standardizes keys, whitespace, casing, duplicates, and data types. Corrections are recorded in a data-quality log.
4. **Transform:** Combines employee, payroll, and compliance records using LEFT JOINs implemented in both Pandas and SQL. The results are checked for consistency. Calculates headcount by site and department, a 12-month turnover trend, average tenure, payroll variance, and compliance gaps.
5. **Validate:** Checks business rules, including unique IDs, negative salaries, payroll records without matching employees, contracts nearing expiry, and termination dates preceding hire dates.
6. **Report:** Generates a formatted Excel report with seven sheets and a self-contained interactive Plotly dashboard.

## Architecture

```text
data/raw/
    |
    v
extract.py
    |
    v
clean.py  ---> Data-quality log
    |
    v
transform.py
    |-- Pandas LEFT JOIN
    |-- SQL LEFT JOIN (SQLite)
    |-- Workforce metrics
    |
    v
validate.py
    |
    v
report.py  ---> output/people_report_<YYYYMM>.xlsx
    |
    v
dashboard.py ---> output/dashboard.html

run_pipeline.py orchestrates the workflow.
tests/ verifies cleaning, joins, and validation.
```

## Quickstart

Python 3.10 or later is required.

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies and run the pipeline:

```bash
python -m pip install -r requirements.txt
python run_pipeline.py --period 2026-07
python run_pipeline.py --engine sql
python -m pytest -q
```

Additional options:

```bash
python run_pipeline.py --regenerate --strict
```

The `--regenerate` option creates fresh synthetic data, while `--strict` makes validation errors cause the run to exit with a failure status.

## Sample Output

The pipeline processes synthetic data across three sources.

```text
[extract]   employees=300  payroll=267  compliance=295
[clean]     employees=300  payroll=258  compliance=295  corrections_logged=400
[transform] engine=pandas  master_rows=300  (pandas == sql: OK)
            active_headcount=254  turnover=0.39%  avg_tenure=3.48y  payroll_variance=-1.81%
[validate]  findings=8  errors=1  warnings=7
            ERROR no_negative_salary: EMP-0007 -> gross_pay_mxn = -1500.0
[report]    output/people_report_202607.xlsx
[dashboard] output/dashboard.html
```

The sample run intentionally includes invalid data to demonstrate validation. A negative salary is flagged as an error, but the pipeline still generates its reports unless strict mode causes the run to fail.

## Excel Report

The generated workbook contains seven formatted sheets:

- **Summary:** Key workforce metrics and KPIs.
- **Headcount:** Employee counts by department and site.
- **Turnover:** Monthly headcount, hires, terminations, and turnover rate.
- **Payroll_Variance:** Payroll variance by department, with review flags.
- **Compliance_Alerts:** Missing documentation, contract alerts, and other compliance gaps.
- **Validation:** Business-rule validation findings.
- **Data_Quality_Log:** Recorded cleaning operations and corrections.

The workbook includes formatted headers, frozen panes, and filters.

## Interactive Dashboard

The self-contained `output/dashboard.html` dashboard includes:

- Workforce KPI cards.
- Headcount by site and department.
- Monthly turnover trends.
- Payroll variance charts.
- Compliance alerts.

The HTML dashboard can be opened locally in a browser.

## Data-Quality Approach

The input payroll data intentionally contains inconsistencies to demonstrate data-cleaning techniques.

| Source issue | Handling |
|---|---|
| Different employee ID and department column names | Maps source-specific columns to canonical names |
| Inconsistent employee ID formatting | Normalizes employee IDs |
| Mixed-case department names and extra whitespace | Trims whitespace and standardizes casing |
| Numeric values stored as text | Converts values to numeric types |
| Duplicate records | Removes duplicates and records cleaning actions |
| Missing employee IDs | Removes affected payroll rows and records the issue |
| Payroll records without matching HRIS employees | Flags unmatched payroll records during validation |
| Negative salary values | Reports a validation error |

**Core principles:**

- Record data corrections rather than silently modifying values.
- Preserve the employee dataset as the master dataset during LEFT JOIN operations.
- Separate mechanical cleaning from business-rule validation.
- Make data-quality issues visible so they can be reviewed and addressed.

## Why This Project Matters

HR reporting often requires reconciling information from multiple systems. Inconsistent identifiers, duplicate records, missing documentation, and mismatched payroll data can make monthly reporting unreliable.

This pipeline demonstrates how data cleaning, source reconciliation, SQL joins, automated validation, and report generation can make workforce reporting more consistent and reproducible.

The project uses synthetic data for demonstration; its sample metrics are not claims about a real company's workforce.

## Possible Extensions

- **Scheduling:** Run the pipeline automatically using cron or GitHub Actions.
- **Database integration:** Store processed metrics in PostgreSQL or a cloud data warehouse.
- **Business intelligence:** Connect the processed data to a BI tool.
- **Automated summaries:** Generate explanatory summaries of validation findings.
- **Additional validation:** Add salary outlier detection, probation-period checks, and manager span-of-control rules.

## Project Structure

```text
PeoplePulse/
├── run_pipeline.py
├── data/
│   ├── generate_sample_data.py
│   └── raw/
├── hr_pipeline/
│   ├── extract.py
│   ├── clean.py
│   ├── transform.py
│   ├── validate.py
│   ├── report.py
│   └── dashboard.py
├── tests/
├── output/
├── requirements.txt
├── README.md
└── .gitignore
```

## Tech Stack

- **Programming:** Python
- **Data Processing:** Pandas
- **Querying:** SQL, SQLite
- **Reporting:** Excel, OpenPyXL
- **Visualization:** Plotly
- **Testing:** Pytest

## Testing

Run the test suite with:

```bash
python -m pytest -q
```

The existing test suite contains 12 tests covering data cleaning, join integrity, and validation behavior.

