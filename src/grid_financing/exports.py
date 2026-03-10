from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px

from .classification import TRACK_1, TRACK_2, TRACK_3
from .source_registry import PROJECT_ROOT

TRACK_LABELS = {
    TRACK_1: "Track 1: Market-financed",
    TRACK_2: "Track 2: TSO-financed",
    TRACK_3: "Track 3: Targeted EU support",
}

TRACK_AXIS_LABELS = {
    TRACK_1: "Track 1<br>Market-financed",
    TRACK_2: "Track 2<br>TSO-financed",
    TRACK_3: "Track 3<br>Targeted EU support",
}


def ensure_output_dirs(base_path: Path = PROJECT_ROOT) -> dict[str, Path]:
    paths = {
        "processed": base_path / "data" / "processed",
        "tables": base_path / "outputs" / "tables",
        "charts": base_path / "outputs" / "charts",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def build_aggregate_summary(project_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        project_df.groupby("financing_track", dropna=False)
        .agg(
            project_count=("project_id", "nunique"),
            total_capex_meur=("capex_meur", "sum"),
            total_cef_meur=("estimated_cef_grant_meur", "sum"),
            total_eib_meur=("estimated_eib_loan_meur", "sum"),
            total_private_meur=("estimated_private_meur", "sum"),
            total_tso_meur=("estimated_tso_balance_sheet_meur", "sum"),
        )
        .reset_index()
    )
    for source, target in (
        ("total_capex_meur", "total_capex_beur"),
        ("total_cef_meur", "total_cef_beur"),
        ("total_eib_meur", "total_eib_beur"),
        ("total_private_meur", "total_private_beur"),
        ("total_tso_meur", "total_tso_beur"),
    ):
        summary[target] = summary[source] / 1000

    total_row = pd.DataFrame(
        [
            {
                "financing_track": "Total",
                "project_count": summary["project_count"].sum(),
                "total_capex_meur": summary["total_capex_meur"].sum(),
                "total_cef_meur": summary["total_cef_meur"].sum(),
                "total_eib_meur": summary["total_eib_meur"].sum(),
                "total_private_meur": summary["total_private_meur"].sum(),
                "total_tso_meur": summary["total_tso_meur"].sum(),
                "total_capex_beur": summary["total_capex_beur"].sum(),
                "total_cef_beur": summary["total_cef_beur"].sum(),
                "total_eib_beur": summary["total_eib_beur"].sum(),
                "total_private_beur": summary["total_private_beur"].sum(),
                "total_tso_beur": summary["total_tso_beur"].sum(),
            }
        ]
    )
    return pd.concat([summary, total_row], ignore_index=True)


def build_triage_scatter_dataset(project_df: pd.DataFrame) -> pd.DataFrame:
    scatter = project_df.copy()
    for column in ("country_a", "country_b"):
        if column not in scatter.columns:
            scatter[column] = pd.NA

    scatter["corridor_label"] = scatter.apply(
        lambda row: (
            f"{row['country_a']} - {row['country_b']}"
            if pd.notna(row.get("country_a")) and pd.notna(row.get("country_b"))
            else row.get("project_name")
        ),
        axis=1,
    )

    return scatter[
        [
            "project_id",
            "project_name",
            "country_a",
            "country_b",
            "corridor_label",
            "commercial_ratio",
            "credit_constraint_score",
            "capex_meur",
            "financing_track",
            "social_bcr",
            "data_quality_flags",
        ]
    ].copy()


def build_financing_stack_dataset(summary_df: pd.DataFrame) -> pd.DataFrame:
    subset = summary_df[summary_df["financing_track"].isin({TRACK_1, TRACK_2, TRACK_3})].copy()
    melted = subset.melt(
        id_vars=["financing_track"],
        value_vars=["total_cef_beur", "total_eib_beur", "total_private_beur", "total_tso_beur"],
        var_name="financing_component",
        value_name="value_beur",
    )
    melted["financing_component"] = melted["financing_component"].map(
        {
            "total_cef_beur": "CEF grants",
            "total_eib_beur": "EIB loans",
            "total_private_beur": "Private capital",
            "total_tso_beur": "TSO balance sheet",
        }
    )
    melted["financing_track_label"] = melted["financing_track"].map(TRACK_AXIS_LABELS)
    melted["financing_track_display"] = melted["financing_track"].map(TRACK_LABELS)
    return melted


def export_outputs(project_df: pd.DataFrame, *, base_path: Path = PROJECT_ROOT) -> dict[str, str]:
    paths = ensure_output_dirs(base_path)
    summary_df = build_aggregate_summary(project_df)
    scatter_df = build_triage_scatter_dataset(project_df)
    stack_df = build_financing_stack_dataset(summary_df)

    processed_project_csv = paths["processed"] / "project_master_table.csv"
    processed_summary_csv = paths["processed"] / "aggregate_summary.csv"
    project_excel = paths["tables"] / "project_level_results.xlsx"
    summary_excel = paths["tables"] / "aggregate_summary.xlsx"
    scatter_dataset_csv = paths["charts"] / "triage_scatter_dataset.csv"
    stack_dataset_csv = paths["charts"] / "aggregate_financing_stack_dataset.csv"
    scatter_html = paths["charts"] / "triage_scatter.html"
    stack_html = paths["charts"] / "aggregate_financing_stack.html"

    project_df.to_csv(processed_project_csv, index=False)
    summary_df.to_csv(processed_summary_csv, index=False)
    project_df.to_excel(project_excel, index=False)
    summary_df.to_excel(summary_excel, index=False)
    scatter_df.to_csv(scatter_dataset_csv, index=False)
    stack_df.to_csv(stack_dataset_csv, index=False)

    scatter_plot = (
        scatter_df[
            scatter_df["commercial_ratio"].notna() & scatter_df["credit_constraint_score"].notna()
        ]
        .copy()
        .assign(
            financing_track_display=lambda df: df["financing_track"].map(TRACK_LABELS),
            commercial_ratio_display=lambda df: df["commercial_ratio"].clip(upper=10),
            credit_constraint_score_display=lambda df: df["credit_constraint_score"].clip(upper=1.0),
        )
    )
    scatter_fig = px.scatter(
        scatter_plot,
        x="commercial_ratio_display",
        y="credit_constraint_score_display",
        size="capex_meur",
        color="financing_track_display",
        hover_name="corridor_label",
        custom_data=[
            "project_name",
            "commercial_ratio",
            "credit_constraint_score",
            "social_bcr",
            "capex_meur",
        ],
        title="Financing triage scatter",
        labels={
            "project_name": "Project",
            "commercial_ratio": "Commercial viability ratio",
            "credit_constraint_score": "Binding credit-constraint score",
            "social_bcr": "Social BCR",
            "capex_meur": "CAPEX (MEUR)",
            "commercial_ratio_display": "Commercial viability ratio",
            "credit_constraint_score_display": "Binding credit-constraint score",
            "financing_track_display": "Financing track",
        },
        category_orders={
            "financing_track_display": list(TRACK_LABELS.values())
        },
    )
    scatter_fig.add_vline(x=1.0)
    scatter_fig.add_hline(y=0.15)
    scatter_fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Project: %{customdata[0]}<br>"
            "Financing track: %{fullData.name}<br>"
            "Commercial viability ratio: %{customdata[1]:.2f}<br>"
            "Binding credit-constraint score: %{customdata[2]:.3f}<br>"
            "Social BCR: %{customdata[3]:.2f}<br>"
            "CAPEX: %{customdata[4]:,.0f} MEUR"
            "<extra></extra>"
        )
    )
    scatter_fig.update_xaxes(
        range=[0, 10],
        title_text="Commercial viability ratio<br><sup>Congestion rent / annualized CAPEX</sup>",
    )
    scatter_fig.update_yaxes(
        range=[0, 1.0],
        title_text="Binding credit-constraint score<br><sup>Project CAPEX share / TSO RAB</sup>",
    )
    scatter_fig.write_html(scatter_html)

    stack_fig = px.bar(
        stack_df,
        x="financing_track_label",
        y="value_beur",
        color="financing_component",
        barmode="stack",
        custom_data=["financing_track_display"],
        title="Aggregate financing stack",
        labels={
            "financing_track_label": "Financing track",
            "value_beur": "Amount (bn EUR)",
            "financing_component": "Funding source",
        },
        category_orders={"financing_track_label": [TRACK_AXIS_LABELS[track] for track in TRACK_LABELS]},
    )
    stack_fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Funding source: %{fullData.name}<br>"
            "Amount: %{y:.2f} bn EUR"
            "<extra></extra>"
        )
    )
    stack_fig.update_layout(legend_title_text="Funding source")
    stack_fig.update_xaxes(title_text="Financing track")
    stack_fig.update_yaxes(title_text="Amount (bn EUR)")
    stack_fig.write_html(stack_html)

    return {
        "project_master_table_csv": str(processed_project_csv),
        "aggregate_summary_csv": str(processed_summary_csv),
        "project_level_results_xlsx": str(project_excel),
        "aggregate_summary_xlsx": str(summary_excel),
        "triage_scatter_html": str(scatter_html),
        "aggregate_financing_stack_html": str(stack_html),
    }
