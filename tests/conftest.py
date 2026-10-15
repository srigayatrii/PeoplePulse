import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.generate_sample_data import generate  # noqa: E402
from hr_pipeline.clean import clean_all  # noqa: E402
from hr_pipeline.extract import extract_all  # noqa: E402

PERIOD = "2026-07"


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw")
    generate(PERIOD, n_employees=120, seed=7, raw_dir=d)
    return d


@pytest.fixture(scope="session")
def raw(raw_dir):
    return extract_all(raw_dir, PERIOD)


@pytest.fixture(scope="session")
def cleaned(raw):
    clean, log = clean_all(raw)
    return clean, log


@pytest.fixture
def as_of():
    return pd.Timestamp("2026-07-31")
