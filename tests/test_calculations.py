from __future__ import annotations

import math

import pandas as pd

from grid_financing.calculations import (
    build_sensitivity_cases,
    calculate_project_metrics,
    capital_recovery_factor,
    credit_constraint_score,
    estimated_annual_congestion_rent,
    social_bcr,
)


def test_capital_recovery_factor_matches_spec_default() -> None:
    crf = capital_recovery_factor(0.05, 40)
    assert math.isclose(crf, 0.058278, rel_tol=1e-4)


def test_congestion_rent_formula() -> None:
    rent = estimated_annual_congestion_rent(10, 1000, 0.60)
    assert math.isclose(rent, 52.56, rel_tol=1e-6)


def test_congestion_rent_formula_uses_hourly_sum_when_available() -> None:
    rent = estimated_annual_congestion_rent(999, 1000, 0.60, hourly_abs_price_diff_sum_eur_per_mwh=87_600)
    assert math.isclose(rent, 52.56, rel_tol=1e-6)


def test_social_bcr_ratio() -> None:
    assert social_bcr(200, 100) == 2


def test_credit_constraint_score_uses_rab_in_beur() -> None:
    score = credit_constraint_score(300, 2)
    assert math.isclose(score, 0.15, rel_tol=1e-9)


def test_calculate_project_metrics_populates_core_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "project_id": 1,
                "capex_meur": 2000,
                "capacity_mw": 1000,
                "avg_price_diff_eur_per_mwh": 10,
                "hourly_abs_price_diff_sum_eur_per_mwh": 87_600,
                "dsew_2030nt_eu27_meur_per_year": 150,
                "project_capex_share_a_meur": 1000,
                "project_capex_share_b_meur": 1000,
                "tso_a_rab_beur": 20,
                "tso_b_rab_beur": 5,
                "tso_a_rating": "A-",
                "tso_b_rating": "BB",
                "sovereign_a_debt_to_gdp_pct": 60,
                "sovereign_b_debt_to_gdp_pct": 120,
                "sovereign_a_deficit_to_gdp_pct": 2,
                "sovereign_b_deficit_to_gdp_pct": 4,
            }
        ]
    )
    result = calculate_project_metrics(df)
    row = result.iloc[0]
    assert row["annualized_capex_meur_per_year"] > 0
    assert row["estimated_congestion_rent_meur_per_year"] > 0
    assert row["congestion_rent_basis"] == "hourly_price_sum"
    assert row["commercial_ratio"] > 0
    assert row["social_bcr"] > 0
    assert math.isclose(row["credit_constraint_score_b"], 0.2, rel_tol=1e-9)
    assert bool(row["credit_constrained"]) is True


def test_build_sensitivity_cases_expands_dimensions() -> None:
    df = pd.DataFrame(
        [
            {
                "project_id": 1,
                "price_scenario": "historical_proxy",
                "capex_meur": 1000,
                "capacity_mw": 500,
                "avg_price_diff_eur_per_mwh": 8,
                "dsew_2030nt_eu27_meur_per_year": 100,
            }
        ]
    )
    result = build_sensitivity_cases(
        df,
        discount_rates=(0.04, 0.05),
        utilization_factors=(0.50, 0.60),
        credit_thresholds=(0.10, 0.15),
        price_scenarios=("historical_proxy",),
    )
    assert len(result) == 8
    assert result["sensitivity_case"].nunique() == 8
