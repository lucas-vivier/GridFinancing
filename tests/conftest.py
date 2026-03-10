from __future__ import annotations

from pathlib import Path

import pytest

from grid_financing.source_registry import PROJECT_ROOT, resolve_source


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def tyndp2024_path() -> Path:
    resolved = resolve_source("tyndp2024_workbook")
    if not resolved.exists or resolved.path is None:
        pytest.skip("TYNDP 2024 workbook not available in this checkout.")
    return resolved.path


@pytest.fixture(scope="session")
def tyndp2022_path() -> Path:
    resolved = resolve_source("tyndp2022_workbook")
    if not resolved.exists or resolved.path is None:
        pytest.skip("TYNDP 2022 workbook not available in this checkout.")
    return resolved.path


@pytest.fixture(scope="session")
def local_hourly_price_path() -> Path:
    resolved = resolve_source("local_hourly_prices")
    if not resolved.exists or resolved.path is None:
        pytest.skip("Local hourly price dataset not available in this checkout.")
    return resolved.path
