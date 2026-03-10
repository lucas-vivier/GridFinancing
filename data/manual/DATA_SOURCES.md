# Manual Data Sources — Provenance and Methodology

This document describes how each file in `data/manual/` was compiled, what sources were used, and what caveats apply. All files were generated on 2026-03-10 as seed datasets for the interconnection financing triage analysis.

---

## tso_credit_reference.csv

**Purpose:** TSO credit ratings, regulated asset bases, sovereign ratings, fiscal indicators, and cohesion-country flags for all countries involved in TYNDP cross-border interconnection projects.

**Coverage:** 30 countries — EU27 plus UK, Norway, Switzerland.

**How it was compiled:**

| Field | Source | Method |
|-------|--------|--------|
| `tso_name` | ENTSO-E member list, TSO websites | Identified the main electricity transmission system operator per country |
| `tso_credit_rating` | S&P, Moody's, Fitch via TSO investor relations pages and bond databases | Searched each TSO's investor/debt page for the most recent rating. 16 of 30 TSOs have a public credit rating; the remaining 14 are typically 100% state-owned entities with no public bond issuance |
| `tso_rab_beur` | TSO annual reports, CEER Regulatory Frameworks Report (Jan 2026), regulatory filings | Used the most recent reported regulated asset base in EUR billions. For TSOs without published RAB, estimated from available regulatory data (marked in `notes`) |
| `sovereign_rating` | S&P sovereign ratings (preferred), supplemented by Moody's/Fitch | Used countryeconomy.com sovereign ratings tracker cross-referenced with agency press releases |
| `debt_to_gdp_pct` | Eurostat government finance statistics, 2024 data release (Oct 2025) | General government gross debt as % of GDP |
| `deficit_to_gdp_pct` | Eurostat government finance statistics, 2024 data release (Oct 2025) | General government net lending/borrowing as % of GDP; negative = deficit |
| `cohesion_country` | EU Cohesion Policy 2021–2027 eligibility list | Countries with GNI per capita < 90% of EU average: BG, CZ, EE, GR, HR, CY, LV, LT, HU, MT, PL, PT, RO, SI, SK |

**Key caveats:**
- RAB values for smaller/unrated TSOs are estimates and should be verified against primary regulatory filings
- Some sovereign ratings reflect late-2025 actions (e.g., France downgraded to A+ by S&P in Oct 2025)
- Germany has 4 TSOs (TenneT DE, 50Hertz, Amprion, TransnetBW); the file lists TenneT as the primary entry but notes the others. RAB shown is for TenneT DE only
- Italy: Terna was upgraded from BBB+ to A- by S&P in Apr 2025 following Italy's sovereign upgrade
- TSOs marked "not rated" are typically 100% state-owned; their credit capacity should be assessed via sovereign rating and fiscal headroom
- Effective date is 2025-Q4 across all rows; refresh when newer data becomes available

**Primary source URLs used:**
- RTE: https://www.rte-france.com/en/finance/financing-rating
- Terna: https://www.terna.it/en/investors/debt-rating/rating
- TenneT: https://www.tennet.eu/about-tennet/investor-relations/credit-rating
- Redeia: https://www.redeia.com/en/shareholders-and-investors/financing/rating
- Elia: https://investor.eliagroup.eu/en/financial-position/
- Fingrid: https://www.fingrid.fi/en/pages/investors/credit-ratings/
- Statnett: https://www.statnett.no/en/about-statnett/
- National Grid: https://www.nationalgrid.com/investors/debt-investors/credit-ratings
- Eurostat debt/deficit: https://ec.europa.eu/eurostat/web/products-euro-indicators/w/2-21102025-ap

---

## project_participants.csv

**Purpose:** Per-project country/TSO participation records, including CAPEX share assignments and primary border-side flags for all 100 cross-border transmission projects in the TYNDP 2024.

**Coverage:** 100 cross-border projects × 2–8 participant rows each = ~220 rows.

**How it was compiled:**

| Field | Source | Method |
|-------|--------|--------|
| `project_id` | TYNDP 2024 `Trans.Projects` sheet, `Project ID` column | Direct extraction |
| `country_code` | TYNDP 2024 `Trans.Projects` sheet, `Country` column | Parsed from semicolon-delimited ISO 2-letter codes (e.g., `ES ;FR` → `ES`, `FR`) |
| `tso_name` | ENTSO-E member list cross-referenced with country | Assigned the main TSO per country. For non-EU countries (ME, RS, BA, TN, etc.), TSO name left blank |
| `capex_share_pct` | Default assumption | **50/50 for two-country projects** (standard absent a specific CBCA decision). For multi-country projects (3+), shares split equally as a starting estimate. These are placeholders; actual CBCA or sponsor-specific cost allocations should override when known |
| `is_primary_border_side` | TYNDP 2024 Border field, project ordering | First-listed country marked as primary; this is a convention, not a definitive assignment |
| `participant_order` | Ordering within the Country field | Sequential numbering per project |

**Key caveats:**
- **CAPEX shares are default assumptions, not verified CBCA allocations.** The 50/50 split is the standard regulatory default but many projects have negotiated different splits. Override via `project_overrides.csv` when actual CBCA data is available
- For multi-country projects (40, 124, 170, 219, 227, 335, 1200, 1208, 1211, 1226), shares are split equally as a placeholder
- Non-EU countries (ME, RS, BA, TN, DZ, EG, IL, MK, AL, MA, UA, GE, TR, CH, GB, NO) are included as participants but may not have TSO credit data in the reference table
- TSO names may need refinement for countries with multiple TSOs or recent reorganizations
- The current notebook pipeline is still **bilateral** for the credit-constraint step: it sorts participants by `participant_order`, maps the first record to side `A` and the second to side `B`, and ignores third and later participants in the side-level score. For genuine multi-country projects, this is a simplification rather than a faithful financing allocation

**How this should be better covered:**
- Replace default `capex_share_pct` placeholders with verified CBCA decisions, sponsor agreements, or project-specific investment splits
- Move from the current `A/B` side abstraction to a true participant-level financing model that scores every participant country or TSO separately and then aggregates at project level
- Add an explicit field distinguishing the **primary price border** used for congestion-rent estimation from the **full participant set** used for financing allocation, since these are not always the same thing

---

## border_zone_map.csv

**Purpose:** Maps each cross-border project to its primary bidding-zone pair for use in the price-differential pipeline.

**Coverage:** 100 cross-border projects, one primary border mapping each.

**How it was compiled:**

| Field | Source | Method |
|-------|--------|--------|
| `project_id` | TYNDP 2024 `Trans.Projects` sheet | Direct extraction |
| `zone_a`, `zone_b` | TYNDP 2024 `Trans.Projects` sheet, `Border` column | Extracted directly from the border code field, which uses ENTSO-E bidding zone identifiers (e.g., `ES00-FR00`, `DE00-SE04`). For multi-border projects, the first-listed border was selected as the primary pair |
| `country_a`, `country_b` | Derived from zone codes | The ISO country code embedded in the zone identifier |
| `price_scenario` | Set to `proxy_2023` | Indicates these mappings are for use with historical 2023 price data or proxy values |
| `mapping_method` | All set to `TYNDP border code` | Indicates the zone mapping comes directly from the TYNDP workbook rather than manual assignment |

**ENTSO-E bidding zone code conventions used:**
- `XX00` = main zone for country XX (e.g., `FR00` = France, `DE00` = Germany)
- `SE01`–`SE04` = Sweden north to south (SE01=Luleå, SE02=Sundsvall, SE03=Stockholm, SE04=Malmö)
- `ITN1` = Italy north, `ITCN` = Italy central-north, `ITS1` = Italy south, `ITSI` = Sicily, `ITSA` = Sardinia, `ITCO` = Corsica (FR-managed)
- `DKW1` = Denmark west, `DKE1` = Denmark east
- `NOS0` = Norway south, `NON1` = Norway north
- `FR15` = Corsica
- `UKNI` = UK Northern Ireland, `UK00` = UK mainland
- `LUG1` = Luxembourg
- `GR03` = Greece-Crete
- Suffixes like `Isolated` or `OBZ` indicate non-standard market coupling modes

**Key caveats:**
- Multi-border projects (94, 144, 227, 299, 1088, 1092, 1106, 1208, 1226) have multiple border codes in the workbook; only the primary border is mapped here. The price pipeline should handle this as a simplification
- Projects 1239 and 1240 (SK-UA and RO-UA) have no border code in the TYNDP workbook and blank transfer capacities
- Some zone codes (e.g., `DK/NL00` for project 335) are non-standard combined codes from the TYNDP; the price pipeline should map these to actual ENTSO-E zones
- The `proxy_2023` scenario tag indicates these are baseline mappings; forward-looking scenarios (2030, 2040) would use the same zone pairs but different price data

---

## General notes

- All three files were seeded programmatically from the TYNDP 2024 Excel workbook (`data/tyndp2024_project_sheets.xlsx`, sheets `Trans.Projects` and `Trans.Investments`) plus public reference sources
- The TSO credit data was compiled from TSO investor relations pages, Eurostat fiscal statistics, and sovereign rating trackers as of 2025-Q4
- These are **seed files intended for review and refinement** — the analysis pipeline will flag where data is missing or where default assumptions (like 50/50 CAPEX splits) may produce inaccurate results
- When better data becomes available (actual CBCA decisions, verified RAB figures, updated ratings), update the relevant CSV and re-run the notebook
