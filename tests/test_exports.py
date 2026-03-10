from __future__ import annotations

from pathlib import Path

import pandas as pd

from grid_financing.exports import (
    build_aggregate_summary,
    build_financing_stack_dataset,
    build_triage_scatter_dataset,
    export_outputs,
)


def sample_project_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "project_id": 1,
                "project_name": "A",
                "capex_meur": 100,
                "commercial_ratio": 0.8,
                "credit_constraint_score": 0.02,
                "social_bcr": 2.0,
                "financing_track": "Track 1: Market-financed (merchant/hybrid)",
                "estimated_cef_grant_meur": 0.0,
                "estimated_eib_loan_meur": 0.0,
                "estimated_private_meur": 100.0,
                "estimated_tso_balance_sheet_meur": 0.0,
                "data_quality_flags": pd.NA,
            },
            {
                "project_id": 2,
                "project_name": "B",
                "capex_meur": 200,
                "commercial_ratio": 0.2,
                "credit_constraint_score": 0.2,
                "social_bcr": 1.5,
                "financing_track": "Track 3: Credit-constrained - targeted EU support",
                "estimated_cef_grant_meur": 100.0,
                "estimated_eib_loan_meur": 40.0,
                "estimated_private_meur": 0.0,
                "estimated_tso_balance_sheet_meur": 60.0,
                "data_quality_flags": "missing_credit_reference",
            },
        ]
    )


def test_aggregate_summary_schema() -> None:
    summary = build_aggregate_summary(sample_project_frame())
    assert {"financing_track", "project_count", "total_capex_beur", "total_cef_beur"} <= set(summary.columns)
    assert "Total" in summary["financing_track"].tolist()


def test_chart_dataset_schema() -> None:
    project_df = sample_project_frame()
    summary = build_aggregate_summary(project_df)
    scatter = build_triage_scatter_dataset(project_df)
    stack = build_financing_stack_dataset(summary)
    assert {"commercial_ratio", "credit_constraint_score", "capex_meur"} <= set(scatter.columns)
    assert {"financing_track", "financing_component", "value_beur"} <= set(stack.columns)


def test_export_outputs_creates_expected_files(tmp_path: Path) -> None:
    result = export_outputs(sample_project_frame(), base_path=tmp_path)
    for path in result.values():
        assert Path(path).exists()
