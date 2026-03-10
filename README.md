# Grid Financing

Notebook-first analysis workflow for classifying EU cross-border interconnection projects into financing tracks.

## Setup

Create a Python 3.11+ environment and install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Launch the analyst notebook:

```bash
jupyter notebook notebooks/financing_triage.ipynb
```

Run the test suite:

```bash
pytest
```

## Repository Flow

- `notebooks/financing_triage.ipynb` is the analyst-facing orchestration layer.
- `src/grid_financing/` holds the reusable loading, calculation, classification, and export logic.
- `data/raw/` is the canonical location for raw workbooks.
- Legacy workbook paths directly under `data/` are still supported and reported by the loaders.
- `data/manual/` holds manual lookup tables and fallback inputs that are not reliably fetchable.
- `data/processed/`, `outputs/tables/`, and `outputs/charts/` hold generated artifacts.

## Required Local Inputs

The first working notebook run only requires the local workbooks already in this repository plus the local hourly price dataset:

- `data/raw/TYNDP2022_CBA_EU27_all-scenarios.xlsx` or legacy `data/TYNDP2022_CBA_EU27_all-scenarios.xlsx`
- `data/raw/tyndp2024_project_sheets.xlsx` or legacy `data/tyndp2024_project_sheets.xlsx`
- `data/european_wholesale_electricity_price_data_hourly/all_countries.csv`

The notebook defaults to the local hourly price folder as a development-mode proxy for cross-border price spreads.

## Manual Tables

Place the following CSV files under `data/manual/` when available:

- `tso_credit_reference.csv`
- `project_participants.csv`
- `project_overrides.csv`
- `border_zone_map.csv`
- `dayahead_price_inputs.csv`

If any of these files are missing, the notebook reports the missing file and continues where possible with explicit data-quality flags instead of silently dropping projects.

## Manual Schema Summary

`tso_credit_reference.csv`

- `country_code`
- `tso_name`
- `tso_credit_rating`
- `tso_credit_rating_agency`
- `tso_rab_beur`
- `sovereign_rating`
- `sovereign_rating_agency`
- `debt_to_gdp_pct`
- `deficit_to_gdp_pct`
- `cohesion_country`
- `effective_date`
- `source_url`
- `notes`

`project_participants.csv`

- `project_id`
- `country_code`
- `tso_name`
- `capex_share_pct`
- `is_primary_border_side`
- `participant_order`
- `source`
- `notes`

`project_overrides.csv`

- `project_id`
- `countries_override`
- `primary_border_a`
- `primary_border_b`
- `transfer_capacity_ab_mw_override`
- `transfer_capacity_ba_mw_override`
- `cef_grant_pct_override`
- `manual_track_override`
- `override_reason`
- `source`
- `notes`

`border_zone_map.csv`

- `project_id`
- `price_scenario`
- `zone_a`
- `zone_b`
- `country_a`
- `country_b`
- `mapping_method`
- `source`
- `notes`

`dayahead_price_inputs.csv`

- `project_id`
- `price_scenario`
- `data_year`
- `zone_a`
- `zone_b`
- `avg_abs_price_diff_eur_per_mwh`
- `price_volatility_a_eur_per_mwh`
- `price_volatility_b_eur_per_mwh`
- `price_correlation`
- `directional_flow_a_to_b_share`
- `source_name`
- `source_url`
- `notes`

## Outputs

Notebook and module exports write to deterministic locations:

- `data/processed/project_master_table.csv`
- `data/processed/aggregate_summary.csv`
- `outputs/tables/project_level_results.xlsx`
- `outputs/tables/aggregate_summary.xlsx`
- `outputs/charts/triage_scatter.html`
- `outputs/charts/aggregate_financing_stack.html`

Exported tables include assumptions, source provenance, and data-quality flags so reviewers can trace derived metrics back to the workbook formulas and proxy price inputs.

## Operating Notes

- The 2024 workbook is the primary source for project metadata, transfer capacities, CAPEX aggregation, and EU27 CBA values.
- The 2022 workbook is loaded as fallback and validation context.
- The local hourly price dataset is country-level, not bidding-zone-level. Outputs mark it as a development-mode proxy.
- Multi-country projects remain in the output even when they cannot be fully classified; those rows are flagged for manual participant or border-mapping completion.
- External ENTSO-E fetching is not required for v1. If later enabled, the normalized price-metric interface remains the same.
