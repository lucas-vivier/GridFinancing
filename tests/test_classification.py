from __future__ import annotations

import pandas as pd

from grid_financing.classification import (
    TRACK_1,
    TRACK_2,
    TRACK_3,
    UNCLASSIFIED,
    classify_project,
    classify_projects,
)


def test_classify_project_track_1() -> None:
    assert classify_project(0.71, False) == TRACK_1


def test_classify_project_track_2() -> None:
    assert classify_project(0.69, False) == TRACK_2


def test_classify_project_track_3() -> None:
    assert classify_project(0.69, True) == TRACK_3


def test_classify_project_insufficient_data() -> None:
    assert classify_project(pd.NA, True) == UNCLASSIFIED


def test_classification_ignores_social_bcr_and_applies_financing_defaults() -> None:
    df = pd.DataFrame(
        [
            {
                "project_id": 1,
                "commercial_ratio": 0.71,
                "credit_constrained": True,
                "social_bcr": 10,
                "capex_meur": 100,
                "cohesion_country_a": False,
                "cohesion_country_b": False,
            },
            {
                "project_id": 2,
                "commercial_ratio": 0.20,
                "credit_constrained": True,
                "social_bcr": 0.2,
                "capex_meur": 100,
                "cohesion_country_a": True,
                "cohesion_country_b": False,
                "binding_credit_side": "a",
            },
        ]
    )
    result = classify_projects(df)
    assert result.loc[result["project_id"] == 1, "financing_track"].item() == TRACK_1
    assert result.loc[result["project_id"] == 2, "financing_track"].item() == TRACK_3
    assert result.loc[result["project_id"] == 2, "estimated_cef_grant_meur"].item() == 85
