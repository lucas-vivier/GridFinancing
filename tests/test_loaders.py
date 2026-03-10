from __future__ import annotations

import pandas as pd

from grid_financing.loaders import (
    aggregate_project_capex,
    build_project_master_table,
    load_local_hourly_price_data,
    load_transmission_investments,
    load_transmission_projects,
    load_tyndp_2022_cba,
    load_tyndp_2024_cba,
    normalize_headers,
)
from grid_financing.source_registry import resolve_existing_path


def test_resolve_existing_path_prefers_canonical(tmp_path) -> None:
    canonical = tmp_path / "canonical.txt"
    legacy = tmp_path / "legacy.txt"
    canonical.write_text("x")
    legacy.write_text("y")
    path, variant = resolve_existing_path((canonical,), (legacy,))
    assert path == canonical
    assert variant == "canonical"


def test_normalize_headers_combines_levels() -> None:
    headers = normalize_headers([("Project ID", "ΔSEW", None), (None, "weighted avg", "max")])
    assert headers == ["project_id", "dsew_weighted_avg", "max"]


def test_load_workbooks_and_sheet_signatures(tyndp2024_path, tyndp2022_path) -> None:
    projects = load_transmission_projects()
    investments = load_transmission_investments()
    cba_2024 = load_tyndp_2024_cba()
    cba_2022 = load_tyndp_2022_cba()
    assert not projects.empty
    assert not investments.empty
    assert {"project_id", "country_a", "country_b"} <= set(projects.columns)
    assert {"project_id", "capex_meur"} <= set(aggregate_project_capex(investments).columns)
    assert {"dsew_2030nt_eu27_meur_per_year", "dsew_2040de_eu27_meur_per_year"} <= set(cba_2024.columns)
    assert {"dsew_nt2030_2022_meur_per_year", "dsew_de2040_2022_meur_per_year"} <= set(cba_2022.columns)


def test_cross_border_count_and_blank_transfer_flags(tyndp2024_path, tyndp2022_path, local_hourly_price_path) -> None:
    master = build_project_master_table()
    assert len(master) == 100
    assert master["project_id"].nunique() == 100
    blank_transfer = master["data_quality_flags"].fillna("").str.contains("missing_transfer_capacity")
    assert int(blank_transfer.sum()) == 6


def test_capex_aggregation_matches_known_biscay_value(tyndp2024_path) -> None:
    investments = load_transmission_investments()
    aggregated = aggregate_project_capex(investments)
    value = aggregated.loc[aggregated["project_id"] == 16, "capex_meur"].item()
    assert value == 3100


def test_local_hourly_price_loader_schema(local_hourly_price_path) -> None:
    prices = load_local_hourly_price_data()
    assert {"iso3_code", "datetime_utc", "price_eur_per_mwh", "data_year"} <= set(prices.columns)
    assert prices["data_year"].max() >= 2025
