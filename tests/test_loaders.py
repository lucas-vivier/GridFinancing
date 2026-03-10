from __future__ import annotations

from pathlib import Path

import pandas as pd

from grid_financing.loaders import (
    _build_pair_metrics_for_year,
    build_price_metrics,
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


def test_build_pair_metrics_for_year_uses_full_hourly_overlap() -> None:
    hours = pd.date_range("2020-01-01", "2020-12-31 23:00:00", freq="h", tz="UTC")
    spread_pattern = [float(index % 24) for index in range(len(hours))]
    price_df = pd.DataFrame(
        {
            "iso3_code": ["FRA"] * len(hours) + ["DEU"] * len(hours),
            "datetime_utc": list(hours) + list(hours),
            "price_eur_per_mwh": [40.0 + value for value in spread_pattern] + [30.0 + value for value in spread_pattern],
            "data_year": [2020] * (2 * len(hours)),
        }
    )

    metrics = _build_pair_metrics_for_year(price_df, "FR", "DE", 2020)

    assert metrics["hourly_observation_count"] == 8784
    assert metrics["avg_price_diff_eur_per_mwh"] == 10
    assert metrics["hourly_abs_price_diff_sum_eur_per_mwh"] == 87_840


def test_build_price_metrics_expands_requested_years(monkeypatch) -> None:
    project_df = pd.DataFrame([{"project_id": 1, "country_a": "FR", "country_b": "DE"}])
    hours_2020 = pd.date_range("2020-01-01", "2020-12-31 23:00:00", freq="h", tz="UTC")
    hours_2021 = pd.date_range("2021-01-01", "2021-12-31 23:00:00", freq="h", tz="UTC")
    pattern_2020 = [float(index % 24) for index in range(len(hours_2020))]
    pattern_2021 = [float(index % 12) for index in range(len(hours_2021))]
    price_df = pd.DataFrame(
        {
            "iso3_code": (
                ["FRA"] * len(hours_2020)
                + ["DEU"] * len(hours_2020)
                + ["FRA"] * len(hours_2021)
                + ["DEU"] * len(hours_2021)
            ),
            "datetime_utc": list(hours_2020) + list(hours_2020) + list(hours_2021) + list(hours_2021),
            "price_eur_per_mwh": (
                [40.0 + value for value in pattern_2020]
                + [30.0 + value for value in pattern_2020]
                + [45.0 + value for value in pattern_2021]
                + [35.0 + value for value in pattern_2021]
            ),
            "data_year": [2020] * (2 * len(hours_2020)) + [2021] * (2 * len(hours_2021)),
        }
    )

    monkeypatch.setattr("grid_financing.loaders.load_manual_csv", lambda _: pd.DataFrame())
    monkeypatch.setattr("grid_financing.loaders.load_local_hourly_price_data", lambda: price_df)
    monkeypatch.setattr(
        "grid_financing.loaders.resolve_source",
        lambda _: type("ResolvedSource", (), {"path": Path("data/european_wholesale_electricity_price_data_hourly/all_countries.csv")})(),
    )

    metrics = build_price_metrics(project_df, price_years=(2020, 2021))

    assert len(metrics) == 2
    assert metrics["price_scenario"].tolist() == ["proxy_2020", "proxy_2021"]
    assert metrics["hourly_observation_count"].tolist() == [8784, 8760]


def test_build_price_metrics_base_case_labels_actual_selected_year(monkeypatch) -> None:
    project_df = pd.DataFrame([{"project_id": 1, "country_a": "FR", "country_b": "DE"}])
    hours_2020 = pd.date_range("2020-01-01", "2020-12-31 23:00:00", freq="h", tz="UTC")
    hours_2021 = pd.date_range("2021-01-01", "2021-12-31 23:00:00", freq="h", tz="UTC")
    pattern_2020 = [float(index % 24) for index in range(len(hours_2020))]
    pattern_2021 = [float(index % 12) for index in range(len(hours_2021))]
    price_df = pd.DataFrame(
        {
            "iso3_code": (
                ["FRA"] * len(hours_2020)
                + ["DEU"] * len(hours_2020)
                + ["FRA"] * len(hours_2021)
                + ["DEU"] * len(hours_2021)
            ),
            "datetime_utc": list(hours_2020) + list(hours_2020) + list(hours_2021) + list(hours_2021),
            "price_eur_per_mwh": (
                [40.0 + value for value in pattern_2020]
                + [30.0 + value for value in pattern_2020]
                + [45.0 + value for value in pattern_2021]
                + [35.0 + value for value in pattern_2021]
            ),
            "data_year": [2020] * (2 * len(hours_2020)) + [2021] * (2 * len(hours_2021)),
        }
    )
    border_map = pd.DataFrame([{"project_id": 1, "price_scenario": "proxy_2020"}])

    monkeypatch.setattr(
        "grid_financing.loaders.load_manual_csv",
        lambda source_id: border_map if source_id == "border_zone_map" else pd.DataFrame(),
    )
    monkeypatch.setattr("grid_financing.loaders.load_local_hourly_price_data", lambda: price_df)
    monkeypatch.setattr(
        "grid_financing.loaders.resolve_source",
        lambda _: type("ResolvedSource", (), {"path": Path("data/european_wholesale_electricity_price_data_hourly/all_countries.csv")})(),
    )

    metrics = build_price_metrics(project_df)

    assert metrics.loc[0, "data_year"] == 2021
    assert metrics.loc[0, "price_scenario"] == "proxy_2021"


def test_build_price_metrics_base_case_leaves_missing_scenario_when_no_full_year(monkeypatch) -> None:
    project_df = pd.DataFrame([{"project_id": 1, "country_a": "FR", "country_b": "DE"}])
    partial_hours = pd.date_range("2021-01-01", periods=24, freq="h", tz="UTC")
    price_df = pd.DataFrame(
        {
            "iso3_code": ["FRA"] * len(partial_hours) + ["DEU"] * len(partial_hours),
            "datetime_utc": list(partial_hours) + list(partial_hours),
            "price_eur_per_mwh": [40.0] * len(partial_hours) + [30.0] * len(partial_hours),
            "data_year": [2021] * (2 * len(partial_hours)),
        }
    )

    monkeypatch.setattr("grid_financing.loaders.load_manual_csv", lambda _: pd.DataFrame())
    monkeypatch.setattr("grid_financing.loaders.load_local_hourly_price_data", lambda: price_df)
    monkeypatch.setattr(
        "grid_financing.loaders.resolve_source",
        lambda _: type("ResolvedSource", (), {"path": Path("data/european_wholesale_electricity_price_data_hourly/all_countries.csv")})(),
    )

    metrics = build_price_metrics(project_df)

    assert pd.isna(metrics.loc[0, "price_scenario"])
    assert pd.isna(metrics.loc[0, "data_year"])
