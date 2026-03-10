from __future__ import annotations

from typing import Iterable

import pandas as pd

DEFAULT_DISCOUNT_RATE = 0.05
DEFAULT_ASSET_LIFETIME_YEARS = 25
DEFAULT_UTILIZATION_FACTOR = 0.60
DEFAULT_CREDIT_THRESHOLD = 0.15
DEFAULT_DISCOUNT_SENSITIVITIES = (0.04, 0.05, 0.06)
DEFAULT_UTILIZATION_SENSITIVITIES = (0.50, 0.60, 0.70)
DEFAULT_CREDIT_THRESHOLDS = (0.10, 0.15, 0.20)

SOCIAL_BCR_SOURCE_COLUMNS = (
    "dsew_2030nt_eu27_meur_per_year",
    "dsew_2040nt_eu27_meur_per_year",
    "dsew_2040de_eu27_meur_per_year",
    "dsew_nt2030_2022_meur_per_year",
    "dsew_de2030_2022_meur_per_year",
    "dsew_de2040_2022_meur_per_year",
)


def capital_recovery_factor(discount_rate: float = DEFAULT_DISCOUNT_RATE, asset_lifetime_years: int = DEFAULT_ASSET_LIFETIME_YEARS) -> float:
    if discount_rate <= -1:
        raise ValueError("discount_rate must be greater than -1")
    if asset_lifetime_years <= 0:
        raise ValueError("asset_lifetime_years must be positive")
    if discount_rate == 0:
        return 1 / asset_lifetime_years
    return discount_rate / (1 - (1 + discount_rate) ** (-asset_lifetime_years))


def annualized_capex(capex_meur: float | pd.Series, discount_rate: float = DEFAULT_DISCOUNT_RATE, asset_lifetime_years: int = DEFAULT_ASSET_LIFETIME_YEARS) -> float | pd.Series:
    return capex_meur * capital_recovery_factor(discount_rate=discount_rate, asset_lifetime_years=asset_lifetime_years)


def estimated_annual_congestion_rent(
    avg_abs_price_diff_eur_per_mwh: float | pd.Series,
    capacity_mw: float | pd.Series,
    utilization_factor: float = DEFAULT_UTILIZATION_FACTOR,
    hourly_abs_price_diff_sum_eur_per_mwh: float | pd.Series | None = None,
) -> float | pd.Series:
    if hourly_abs_price_diff_sum_eur_per_mwh is not None:
        return hourly_abs_price_diff_sum_eur_per_mwh * capacity_mw * utilization_factor / 1_000_000
    return avg_abs_price_diff_eur_per_mwh * capacity_mw * utilization_factor * 8760 / 1_000_000


def safe_ratio(numerator: float | pd.Series, denominator: float | pd.Series) -> float | pd.Series:
    if isinstance(denominator, pd.Series):
        return numerator.div(denominator.where(denominator != 0))
    return numerator / denominator if denominator not in (0, None) else float("nan")


def social_bcr(dsew_meur_per_year: float | pd.Series, annualized_capex_meur_per_year: float | pd.Series) -> float | pd.Series:
    return safe_ratio(dsew_meur_per_year, annualized_capex_meur_per_year)


def normalize_credit_rating(rating: object) -> str:
    if rating is None or (isinstance(rating, float) and pd.isna(rating)):
        return ""
    return str(rating).strip().upper().replace(" ", "")


def is_sub_investment_grade(rating: object) -> bool:
    normalized = normalize_credit_rating(rating)
    if not normalized:
        return False
    prefixes = ("AAA", "AA", "A", "BBB", "BAA")
    return not normalized.startswith(prefixes)


def is_fiscally_constrained(debt_to_gdp_pct: object, deficit_to_gdp_pct: object) -> bool:
    if pd.isna(debt_to_gdp_pct) or pd.isna(deficit_to_gdp_pct):
        return False
    return float(debt_to_gdp_pct) > 100 and float(deficit_to_gdp_pct) > 3


def credit_constraint_score(capex_share_meur: float | pd.Series, tso_rab_beur: float | pd.Series) -> float | pd.Series:
    rab_meur = tso_rab_beur * 1000
    return safe_ratio(capex_share_meur, rab_meur)


def calculate_project_metrics(
    project_df: pd.DataFrame,
    *,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    asset_lifetime_years: int = DEFAULT_ASSET_LIFETIME_YEARS,
    utilization_factor: float = DEFAULT_UTILIZATION_FACTOR,
    credit_threshold: float = DEFAULT_CREDIT_THRESHOLD,
) -> pd.DataFrame:
    df = project_df.copy()
    df["discount_rate"] = discount_rate
    df["asset_lifetime_years"] = asset_lifetime_years
    df["utilization_factor"] = utilization_factor
    df["credit_threshold"] = credit_threshold
    df["capital_recovery_factor"] = capital_recovery_factor(discount_rate, asset_lifetime_years)
    df["annualized_capex_meur_per_year"] = annualized_capex(df["capex_meur"], discount_rate, asset_lifetime_years)
    df["estimated_congestion_rent_meur_per_year"] = estimated_annual_congestion_rent(
        df["avg_price_diff_eur_per_mwh"],
        df["capacity_mw"],
        utilization_factor,
        hourly_abs_price_diff_sum_eur_per_mwh=df.get("hourly_abs_price_diff_sum_eur_per_mwh"),
    )
    df["congestion_rent_basis"] = (
        "hourly_price_sum" if "hourly_abs_price_diff_sum_eur_per_mwh" in df.columns else "annualized_average_spread"
    )
    df["commercial_ratio"] = safe_ratio(
        df["estimated_congestion_rent_meur_per_year"],
        df["annualized_capex_meur_per_year"],
    )

    for column in SOCIAL_BCR_SOURCE_COLUMNS:
        if column in df.columns:
            suffix = column.replace("dsew_", "").replace("_meur_per_year", "")
            df[f"social_bcr_{suffix}"] = social_bcr(df[column], df["annualized_capex_meur_per_year"])

    if "social_bcr_2030nt_eu27" in df.columns:
        df["social_bcr"] = df["social_bcr_2030nt_eu27"]
    else:
        social_columns = [column for column in df.columns if column.startswith("social_bcr_")]
        df["social_bcr"] = df[social_columns].bfill(axis=1).iloc[:, 0] if social_columns else pd.NA

    for side in ("a", "b"):
        capex_share_column = f"project_capex_share_{side}_meur"
        rab_column = f"tso_{side}_rab_beur"
        if capex_share_column in df.columns and rab_column in df.columns:
            df[f"credit_constraint_score_{side}"] = credit_constraint_score(df[capex_share_column], df[rab_column])
        rating_column = f"tso_{side}_rating"
        debt_column = f"sovereign_{side}_debt_to_gdp_pct"
        deficit_column = f"sovereign_{side}_deficit_to_gdp_pct"
        if rating_column in df.columns:
            df[f"tso_{side}_sub_investment_grade"] = df[rating_column].apply(is_sub_investment_grade)
        if debt_column in df.columns and deficit_column in df.columns:
            df[f"sovereign_{side}_fiscally_constrained"] = df.apply(
                lambda row: is_fiscally_constrained(row[debt_column], row[deficit_column]),
                axis=1,
            )

    score_columns = [column for column in ("credit_constraint_score_a", "credit_constraint_score_b") if column in df.columns]
    if score_columns:
        df["credit_constraint_score"] = df[score_columns].max(axis=1, skipna=True)
        non_empty_scores = df[score_columns].notna().any(axis=1)
        df["binding_credit_side"] = pd.NA
        df.loc[non_empty_scores, "binding_credit_side"] = df.loc[non_empty_scores, score_columns].idxmax(axis=1).str[-1]
    else:
        df["credit_constraint_score"] = pd.NA
        df["binding_credit_side"] = pd.NA

    constraint_flags = []
    for side in ("a", "b"):
        side_flags = []
        score_column = f"credit_constraint_score_{side}"
        sub_ig_column = f"tso_{side}_sub_investment_grade"
        fiscal_column = f"sovereign_{side}_fiscally_constrained"
        if score_column in df.columns:
            side_flags.append(df[score_column].fillna(-1) > credit_threshold)
        if sub_ig_column in df.columns:
            side_flags.append(df[sub_ig_column].fillna(False))
        if fiscal_column in df.columns:
            side_flags.append(df[fiscal_column].fillna(False))
        if side_flags:
            constraint_flags.append(pd.concat(side_flags, axis=1).any(axis=1))

    if constraint_flags:
        df["credit_constrained"] = pd.concat(constraint_flags, axis=1).any(axis=1)
    else:
        df["credit_constrained"] = pd.Series(False, index=df.index)

    return df


def build_sensitivity_cases(
    project_df: pd.DataFrame,
    *,
    discount_rates: Iterable[float] = DEFAULT_DISCOUNT_SENSITIVITIES,
    utilization_factors: Iterable[float] = DEFAULT_UTILIZATION_SENSITIVITIES,
    credit_thresholds: Iterable[float] = DEFAULT_CREDIT_THRESHOLDS,
    price_scenarios: Iterable[str] | None = None,
) -> pd.DataFrame:
    scenarios = []
    scenario_values = tuple(price_scenarios) if price_scenarios is not None else tuple(
        value for value in project_df.get("price_scenario", pd.Series(dtype=str)).dropna().unique().tolist()
    )
    scenario_values = scenario_values or ("historical_proxy",)

    for price_scenario in scenario_values:
        scenario_frame = project_df.copy()
        if "price_scenario" in scenario_frame.columns:
            scenario_frame = scenario_frame[scenario_frame["price_scenario"].fillna("historical_proxy") == price_scenario]
        for discount_rate in discount_rates:
            for utilization_factor in utilization_factors:
                for credit_threshold in credit_thresholds:
                    case = calculate_project_metrics(
                        scenario_frame,
                        discount_rate=discount_rate,
                        utilization_factor=utilization_factor,
                        credit_threshold=credit_threshold,
                    )
                    case["sensitivity_case"] = (
                        f"price={price_scenario}|discount={discount_rate:.2%}|"
                        f"utilization={utilization_factor:.0%}|credit={credit_threshold:.0%}"
                    )
                    scenarios.append(case)

    return pd.concat(scenarios, ignore_index=True) if scenarios else pd.DataFrame()
