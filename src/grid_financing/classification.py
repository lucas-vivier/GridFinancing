from __future__ import annotations

import pandas as pd

TRACK_1 = "Track 1: Market-financed (merchant/hybrid)"
TRACK_2 = "Track 2: Regulated + CBCA"
TRACK_3 = "Track 3: Credit-constrained - targeted EU support"
UNCLASSIFIED = "Unclassified: insufficient data"


def classify_project(
    commercial_ratio: object,
    credit_constrained: object,
    *,
    manual_track_override: object = None,
    commercial_threshold: float = 1.0,
) -> str:
    if manual_track_override is not None and not pd.isna(manual_track_override) and str(manual_track_override).strip():
        return str(manual_track_override)
    if pd.isna(commercial_ratio) or pd.isna(credit_constrained):
        return UNCLASSIFIED
    if float(commercial_ratio) > commercial_threshold:
        return TRACK_1
    if bool(credit_constrained):
        return TRACK_3
    return TRACK_2


def estimate_financing_stack(
    capex_meur: object,
    financing_track: str,
    *,
    cohesion_country: bool = False,
    cef_grant_pct_override: object = None,
) -> dict[str, float]:
    if pd.isna(capex_meur):
        capex = 0.0
    else:
        capex = float(capex_meur)

    if financing_track == TRACK_1:
        cef_pct, eib_pct, private_pct, tso_pct = 0.0, 0.0, 1.0, 0.0
    elif financing_track == TRACK_2:
        cef_pct, eib_pct, private_pct, tso_pct = 0.0, 0.0, 0.0, 1.0
    elif financing_track == TRACK_3:
        cef_pct = float(cef_grant_pct_override) / 100 if not pd.isna(cef_grant_pct_override) else (0.85 if cohesion_country else 0.50)
        eib_pct, private_pct = 0.20, 0.0
        tso_pct = max(0.0, 1.0 - cef_pct - eib_pct)
    else:
        cef_pct, eib_pct, private_pct, tso_pct = 0.0, 0.0, 0.0, 0.0

    return {
        "estimated_cef_grant_meur": capex * cef_pct,
        "estimated_eib_loan_meur": capex * eib_pct,
        "estimated_private_meur": capex * private_pct,
        "estimated_tso_balance_sheet_meur": capex * tso_pct,
        "estimated_public_cost_meur": capex * cef_pct,
        "assumed_cef_grant_pct": cef_pct,
        "assumed_eib_pct": eib_pct,
        "assumed_private_pct": private_pct,
        "assumed_tso_pct": tso_pct,
    }


def classify_projects(
    project_df: pd.DataFrame,
    *,
    commercial_threshold: float = 1.0,
) -> pd.DataFrame:
    df = project_df.copy()
    df["financing_track"] = df.apply(
        lambda row: classify_project(
            row.get("commercial_ratio"),
            row.get("credit_constrained"),
            manual_track_override=row.get("manual_track_override"),
            commercial_threshold=commercial_threshold,
        ),
        axis=1,
    )
    df["classification_blocked"] = df["financing_track"].eq(UNCLASSIFIED)

    def _binding_cohesion(row: pd.Series) -> bool:
        side = row.get("binding_credit_side")
        if side is not None and not pd.isna(side) and str(side) in ("a", "b"):
            side = str(side)
            return bool(row.get(f"cohesion_country_{side}", False))
        return bool(row.get("cohesion_country_a", False) or row.get("cohesion_country_b", False))

    stacks = df.apply(
        lambda row: estimate_financing_stack(
            row.get("capex_meur"),
            row["financing_track"],
            cohesion_country=_binding_cohesion(row),
            cef_grant_pct_override=row.get("cef_grant_pct_override"),
        ),
        axis=1,
        result_type="expand",
    )
    return pd.concat([df, stacks], axis=1)
