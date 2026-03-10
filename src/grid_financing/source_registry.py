from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    kind: str
    canonical_paths: tuple[Path, ...]
    legacy_paths: tuple[Path, ...] = ()
    required_sheets: dict[str, tuple[str, ...]] | None = None
    missing_message: str = ""
    schema: tuple[str, ...] = ()

    def candidates(self) -> tuple[Path, ...]:
        return self.canonical_paths + self.legacy_paths


@dataclass(frozen=True)
class ResolvedSource:
    descriptor: SourceDescriptor
    path: Path | None
    variant: str

    @property
    def exists(self) -> bool:
        return self.path is not None and self.path.exists()


MANUAL_SCHEMAS: dict[str, tuple[str, ...]] = {
    "tso_credit_reference": (
        "country_code",
        "tso_name",
        "tso_credit_rating",
        "tso_credit_rating_agency",
        "tso_rab_beur",
        "sovereign_rating",
        "sovereign_rating_agency",
        "debt_to_gdp_pct",
        "deficit_to_gdp_pct",
        "cohesion_country",
        "effective_date",
        "source_url",
        "notes",
    ),
    "project_participants": (
        "project_id",
        "country_code",
        "tso_name",
        "capex_share_pct",
        "is_primary_border_side",
        "participant_order",
        "source",
        "notes",
    ),
    "project_overrides": (
        "project_id",
        "countries_override",
        "primary_border_a",
        "primary_border_b",
        "transfer_capacity_ab_mw_override",
        "transfer_capacity_ba_mw_override",
        "cef_grant_pct_override",
        "manual_track_override",
        "override_reason",
        "source",
        "notes",
    ),
    "border_zone_map": (
        "project_id",
        "price_scenario",
        "zone_a",
        "zone_b",
        "country_a",
        "country_b",
        "mapping_method",
        "source",
        "notes",
    ),
    "dayahead_price_inputs": (
        "project_id",
        "price_scenario",
        "data_year",
        "zone_a",
        "zone_b",
        "avg_abs_price_diff_eur_per_mwh",
        "price_volatility_a_eur_per_mwh",
        "price_volatility_b_eur_per_mwh",
        "price_correlation",
        "directional_flow_a_to_b_share",
        "source_name",
        "source_url",
        "notes",
    ),
}

WORKBOOK_SIGNATURES: dict[str, dict[str, tuple[str, ...]]] = {
    "tyndp2024": {
        "Trans.Projects": (
            "project_id",
            "project_name",
            "country",
            "status_id_1_under_consideration_2_in_planning_but_not_permitting_3_in_permitting_4_under_construction",
            "is_the_project_cross_border",
            "border",
            "transfer_capacity_increase_a_b_mw",
            "transfer_capacity_increase_b_a_mw",
        ),
        "Trans.Investments": (
            "investment_number",
            "this_investment_belongs_to_project_number",
            "estimated_capex_meur",
            "capacity_of_the_investment_mw",
        ),
        "2030NT-EU27": ("project_id", "project_name", "dsew_weighted_avg"),
        "2040NT-EU27": ("project_id", "project_name", "dsew_weighted_avg"),
        "2040DE-EU27": ("project_id", "project_name", "dsew_weighted_avg"),
    },
    "tyndp2022": {
        "NT2030_EU": ("project_id", "project_name", "dsew_weighted_avg"),
        "DE2030_EU": ("project_id", "project_name", "dsew_weighted_avg"),
        "DE2040_EU": ("project_id", "project_name", "dsew_weighted_avg"),
    },
}

SOURCE_REGISTRY: dict[str, SourceDescriptor] = {
    "tyndp2022_workbook": SourceDescriptor(
        source_id="tyndp2022_workbook",
        kind="local",
        canonical_paths=(PROJECT_ROOT / "data" / "raw" / "TYNDP2022_CBA_EU27_all-scenarios.xlsx",),
        legacy_paths=(PROJECT_ROOT / "data" / "TYNDP2022_CBA_EU27_all-scenarios.xlsx",),
        required_sheets=WORKBOOK_SIGNATURES["tyndp2022"],
        missing_message=(
            "Missing TYNDP 2022 workbook. Place "
            "`TYNDP2022_CBA_EU27_all-scenarios.xlsx` in `data/raw/` "
            "or keep the legacy copy under `data/`."
        ),
    ),
    "tyndp2024_workbook": SourceDescriptor(
        source_id="tyndp2024_workbook",
        kind="local",
        canonical_paths=(PROJECT_ROOT / "data" / "raw" / "tyndp2024_project_sheets.xlsx",),
        legacy_paths=(PROJECT_ROOT / "data" / "tyndp2024_project_sheets.xlsx",),
        required_sheets=WORKBOOK_SIGNATURES["tyndp2024"],
        missing_message=(
            "Missing TYNDP 2024 workbook. Place `tyndp2024_project_sheets.xlsx` "
            "in `data/raw/` or keep the legacy copy under `data/`."
        ),
    ),
    "local_hourly_prices": SourceDescriptor(
        source_id="local_hourly_prices",
        kind="local",
        canonical_paths=(PROJECT_ROOT / "data" / "european_wholesale_electricity_price_data_hourly" / "all_countries.csv",),
        missing_message=(
            "Missing local hourly price proxy dataset. Place `all_countries.csv` in "
            "`data/european_wholesale_electricity_price_data_hourly/`."
        ),
        schema=("Country", "ISO3 Code", "Datetime (UTC)", "Datetime (Local)", "Price (EUR/MWhe)"),
    ),
    "tso_credit_reference": SourceDescriptor(
        source_id="tso_credit_reference",
        kind="manual-download-required",
        canonical_paths=(PROJECT_ROOT / "data" / "manual" / "tso_credit_reference.csv",),
        missing_message=(
            "Missing `data/manual/tso_credit_reference.csv`. Add the manual TSO and sovereign "
            "credit reference table there to enable credit-constraint scoring."
        ),
        schema=MANUAL_SCHEMAS["tso_credit_reference"],
    ),
    "project_participants": SourceDescriptor(
        source_id="project_participants",
        kind="manual-download-required",
        canonical_paths=(PROJECT_ROOT / "data" / "manual" / "project_participants.csv",),
        missing_message=(
            "Missing `data/manual/project_participants.csv`. Add the seeded participant ordering "
            "and CAPEX split assumptions there, then replace them with project-specific CBCA or "
            "sponsor allocations where known."
        ),
        schema=MANUAL_SCHEMAS["project_participants"],
    ),
    "project_overrides": SourceDescriptor(
        source_id="project_overrides",
        kind="manual-download-required",
        canonical_paths=(PROJECT_ROOT / "data" / "manual" / "project_overrides.csv",),
        missing_message=(
            "Missing `data/manual/project_overrides.csv`. Add approved manual overrides there for "
            "capacity gaps, country mapping corrections, and explicit track overrides."
        ),
        schema=MANUAL_SCHEMAS["project_overrides"],
    ),
    "border_zone_map": SourceDescriptor(
        source_id="border_zone_map",
        kind="manual-download-required",
        canonical_paths=(PROJECT_ROOT / "data" / "manual" / "border_zone_map.csv",),
        missing_message=(
            "Missing `data/manual/border_zone_map.csv`. Add project-to-border or zone mappings there "
            "for exact price processing or multi-country projects."
        ),
        schema=MANUAL_SCHEMAS["border_zone_map"],
    ),
    "dayahead_price_inputs": SourceDescriptor(
        source_id="dayahead_price_inputs",
        kind="manual-download-required",
        canonical_paths=(PROJECT_ROOT / "data" / "manual" / "dayahead_price_inputs.csv",),
        missing_message=(
            "Missing `data/manual/dayahead_price_inputs.csv`. Add normalized project-level price "
            "metrics there when local proxy prices are not the intended source."
        ),
        schema=MANUAL_SCHEMAS["dayahead_price_inputs"],
    ),
}


def resolve_existing_path(
    canonical_paths: Iterable[Path],
    legacy_paths: Iterable[Path] = (),
) -> tuple[Path | None, str]:
    for path in canonical_paths:
        if path.exists():
            return path, "canonical"
    for path in legacy_paths:
        if path.exists():
            return path, "legacy"
    return None, "missing"


def resolve_source(source_id: str) -> ResolvedSource:
    descriptor = SOURCE_REGISTRY[source_id]
    path, variant = resolve_existing_path(descriptor.canonical_paths, descriptor.legacy_paths)
    return ResolvedSource(descriptor=descriptor, path=path, variant=variant)


def manual_source_status() -> list[dict[str, str | bool]]:
    statuses: list[dict[str, str | bool]] = []
    for source_id, descriptor in SOURCE_REGISTRY.items():
        resolved = resolve_source(source_id)
        statuses.append(
            {
                "source_id": source_id,
                "kind": descriptor.kind,
                "exists": resolved.exists,
                "variant": resolved.variant,
                "path": str(resolved.path) if resolved.path else "",
                "message": "" if resolved.exists else descriptor.missing_message,
            }
        )
    return statuses


def ensure_columns_present(columns: Iterable[str], required: Iterable[str], context: str) -> None:
    missing = [column for column in required if column not in columns]
    if missing:
        raise ValueError(f"{context} is missing required columns: {', '.join(missing)}")
