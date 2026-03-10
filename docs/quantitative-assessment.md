# Project Requirements: Interconnection Financing Triage Analysis

## Objective

Build a data pipeline that takes all planned EU cross-border electricity interconnection projects, computes two key ratios per project, classifies each project into one of three financing tracks, and estimates aggregate financing needs per track. The output supports a policy brief arguing that EU legislation should assign different financing instruments to different types of interconnectors.

---

## 1. Data Sources

### 1.1 TYNDP CBA Results (Benefits per project)

**Source:** TYNDP 2022 CBA Excel — already available locally
- File: `TYNDP2022_CBA_EU27_all-scenarios.xlsx`
- Sheets: `NT2030_EU`, `DE2030_EU`, `DE2040_EU`
- Key columns:
  - `Project ID` (col A)
  - `Project name` (col B)
  - `ΔSEW` weighted avg (col D) — Annual Socio-Economic Welfare increase in M€/year. This is the **gross annual benefit** (reduction in system generation costs), NOT net of project CAPEX.
  - `ΔSEW_CO2` weighted avg (col G) — Additional welfare from CO₂ reduction
  - `ΔRES` weighted avg (col W) — Avoided curtailment in GWh/year
  - `ΔCO2_market` weighted avg (col M) — CO₂ reduction in ktonnes/year

**Processing:**
- Extract all projects from `NT2030_EU` and `DE2040_EU` sheets
- For each project, take ΔSEW from both scenarios. Use the average or present both.
- Filter to **cross-border projects only** (projects connecting two different countries). This requires mapping project names to countries — see Section 1.5.

**Fallback for TYNDP 2024:** If TYNDP 2024 project sheets become available with CBA results (from https://tyndp.entsoe.eu/), prefer those. The 2022 data is what we have now.

### 1.2 TYNDP Project CAPEX (Cost per project)

**Source:** TYNDP 2024 Project Sheets — available on the TYNDP platform
- URL: https://tyndp.entsoe.eu/ (interactive platform with project sheets)
- Each project sheet contains: CAPEX (€M), capacity (MW), commissioning date, status (construction / permitting / planning / consideration), countries involved

**Alternative source:** Ember's analysis in "Money on the line" (Dec 2025) — available as uploaded PDF. Ember extracted CAPEX and status data from TYNDP 2024 project sheets and computed per-border investment costs.

**Processing:**
- For each project, extract: total CAPEX (€M), capacity (MW), countries involved, project status
- If TYNDP 2024 CAPEX is not available for a project, use Ember's per-border CAPEX estimates as fallback
- Compute **annualized CAPEX** = CAPEX × CRF (Capital Recovery Factor)
  - CRF = r / (1 - (1+r)^(-n))
  - Where r = discount rate (use 5% real, consistent with TYNDP methodology)
  - n = asset lifetime (use 40 years for HVDC interconnectors)
  - CRF at 5% / 40 years ≈ 0.0583
  - Example: €2bn CAPEX → annualized ≈ €117M/year

### 1.3 Day-Ahead Electricity Prices (for congestion rent estimation)

**Source:** ENTSO-E Transparency Platform
- URL: https://transparency.entsoe.eu/
- Dataset: "Day-ahead prices" per bidding zone, hourly resolution
- Period: most recent full year available (2023 or 2024)
- Bidding zones needed: all EU zones involved in planned interconnectors

**Alternative/simplified source:** If hourly data extraction is too heavy, use annual average day-ahead prices per country from Eurostat or ACER Market Monitoring Reports.

**Processing:**
- For each border (country pair), compute:
  - **Average absolute price differential** = mean over all hours of |Price_A(h) - Price_B(h)|, in €/MWh
  - **Price volatility** per zone = standard deviation of hourly prices, in €/MWh
  - **Price correlation** between zones = Pearson correlation coefficient of hourly price series
  - **Directional flow indicator** = share of hours where A→B vs. B→A (indicates whether trade is one-directional or bidirectional)

### 1.4 TSO and Sovereign Credit Data (for financing capacity classification)

**Source:** Multiple — compile manually into a reference table

For each relevant country/TSO:
- **TSO name** and **credit rating** (from S&P, Moody's, or Fitch — available in TSO annual reports or Scope Ratings grid operator reports)
- **TSO Regulated Asset Base (RAB)** in €bn — from annual reports or CEER Regulatory Frameworks report (Jan 2026)
- **Sovereign credit rating** of the country
- **Government debt-to-GDP ratio** (from Eurostat)
- **Whether the country is a "cohesion country"** under EU rules (GNI < 90% of EU average) — this determines CEF Transport eligibility for 85% co-financing

**Reference table (to be compiled):**

| Country | Main TSO | TSO Credit Rating | TSO RAB (€bn) | Sovereign Rating | Debt/GDP (%) | Cohesion country? |
|---|---|---|---|---|---|---|
| France | RTE | A+ (S&P) | ~17 | AA- | ~112% | No |
| Germany | TenneT DE / 50Hertz / Amprion / TransnetBW | Various, mostly A range | Large | AAA | ~64% | No |
| Spain | Red Eléctrica (Redeia) | A- | ~10 | A | ~107% | No |
| Italy | Terna | BBB+ | ~18 | BBB | ~140% | Parts (South) |
| Ireland | EirGrid | A range (semi-state) | ~3 | A+ | ~42% | No |
| Greece | IPTO (ADMIE) | BB range | ~2 | BBB- | ~160% | Yes |
| Cyprus | TSOC (EAC) | Not rated / sub-IG | <1 | BBB- | ~105% | Yes |
| Poland | PSE | Not widely rated | ~3 | A- | ~50% | Yes |
| Estonia | Elering | A range | <1 | A+ (sov) | ~19% | Yes |
| Finland | Fingrid | Aa range | ~3 | Aa1 | ~75% | No |

**Note:** This table needs verification from primary sources. The coding agent should flag where data is missing and provide a template for manual completion.

### 1.5 Project-to-Country Mapping

**Source:** Derive from project names in TYNDP + manual verification

**Processing:**
- Parse TYNDP project names to identify the two (or more) countries involved
- Example: "Biscay Gulf" → France, Spain. "Celtic Interconnector" → Ireland, France. "EuroAsia Interconnector" → Greece, Cyprus.
- Some projects are internal (within one country) — these should be flagged and excluded from the cross-border analysis
- Create a lookup table: `project_id → [country_A, country_B]`

---

## 2. Calculations

### 2.1 Commercial Viability Ratio (per project)

**Purpose:** Can congestion rents plausibly cover the project cost? This determines whether the merchant model is viable.

**Formula:**

```
Commercial_Viability_Ratio = Estimated_Annual_Congestion_Rent / Annualized_CAPEX
```

Where:

```
Estimated_Annual_Congestion_Rent = Avg_Absolute_Price_Differential (€/MWh) 
                                   × Capacity (MW) 
                                   × Utilization_Factor 
                                   × 8,760 (hours/year)
                                   / 1,000,000 (to convert to M€)
```

Parameters:
- `Avg_Absolute_Price_Differential`: from Section 1.3, for the relevant border
- `Capacity`: from TYNDP project sheet (MW)
- `Utilization_Factor`: assume 0.60 (60%) as base case. This is conservative — ElecLink achieved >98% availability but not all hours have positive price differential. Sensitivity: test 0.50 and 0.70.
- `Annualized_CAPEX`: from Section 1.2

**Interpretation:**
- Ratio > 1.0: project likely self-financing through congestion rents → merchant candidate
- Ratio 0.7–1.0: borderline — may work with hybrid model (cap-and-floor) or modest public support
- Ratio < 0.7: not commercially viable on congestion rents alone → needs regulated model

**Important caveats (to be noted in output):**
- This is a conservative lower bound — excludes capacity market revenues and ancillary services
- Uses current/recent price data — forward-looking analysis (with PyPSA) would be needed for projects commissioning in the 2030s
- Price differentials will change as more interconnection is built (cannibalization effect)

### 2.2 Social Benefit-Cost Ratio (per project)

**Purpose:** Does the project deliver positive welfare for Europe? This confirms the project merits public support if it can't attract private capital.

**Formula:**

```
Social_BCR = ΔSEW / Annualized_CAPEX
```

Where:
- `ΔSEW`: from TYNDP CBA (Section 1.1), in M€/year
- `Annualized_CAPEX`: from Section 1.2

**Interpretation:**
- Ratio > 1.0: project delivers positive net welfare → should be built
- Ratio > 2.0: high-value project — strong case for public support if commercially unviable
- Ratio < 1.0: marginal or negative — revisit assumptions, may not merit public funding

**Note:** ΔSEW is the gross annual benefit (not net of CAPEX). So Social_BCR > 1 means benefits exceed annualized costs. This is the standard CBA test.

### 2.3 Credit Constraint Indicator (per project)

**Purpose:** Can the project promoters actually raise the money? This determines whether the credit-constrained track applies.

**Formula (simplified):**

```
Credit_Constraint_Score = Project_CAPEX_Share / TSO_RAB
```

Computed for each side of the interconnector separately. The binding constraint is on the weaker side.

Where:
- `Project_CAPEX_Share`: the TSO's share of total project CAPEX (assume 50/50 if no CBCA exists, or use known CBCA split)
- `TSO_RAB`: the TSO's Regulated Asset Base (from Section 1.4)

**Interpretation:**
- Score < 0.05 (project is <5% of TSO's RAB): TSO can comfortably finance → not credit-constrained
- Score 0.05–0.15: significant but manageable with market debt
- Score > 0.15: project represents >15% of TSO's asset base → credit-constrained, needs public support

**Additional flags:**
- TSO credit rating below investment grade (BBB-) → automatically credit-constrained
- Sovereign unable to provide guarantees (debt/GDP > 100% AND deficit > 3%) → flag as fiscally constrained
- Cohesion country status → eligible for differentiated CEF co-financing

### 2.4 Financing Track Classification

**Decision logic (per project):**

```python
def classify_project(commercial_ratio, social_bcr, credit_constrained):
    if commercial_ratio > 0.7:
        return "Track 1: Market-financed (merchant/hybrid)"
    elif not credit_constrained:
        return "Track 2: Regulated + CBCA"
    else:
        return "Track 3: Credit-constrained — targeted EU support"
```

Where:
- `commercial_ratio` = from Section 2.1
- `social_bcr` = from Section 2.2 (used for prioritization within tracks, not classification)
- `credit_constrained` = True if Credit_Constraint_Score > 0.15 OR TSO sub-investment-grade OR sovereign fiscally constrained (from Section 2.3)

### 2.5 Financing Needs Estimation (per project and aggregate)

For each project, estimate the financing stack based on its track:

**Track 1 (Merchant):**
```
EU_Grant = 0
EIB_Loan = 0 (or small InvestEU guarantee if hybrid)
Private_Capital = 100% of CAPEX
Public_Cost = 0
```

**Track 2 (Regulated + CBCA):**
```
CEF_Grant = 30% of CAPEX (historical average, ~31.5%)
EIB_Loan = 25% of CAPEX
TSO_Balance_Sheet = 45% of CAPEX (via tariffs)
Public_Cost = CEF_Grant
```

**Track 3 (Credit-constrained):**
```
CEF_Grant = 50-85% of CAPEX (variable, higher for cohesion countries)
EIB_Loan = 20% of CAPEX (with first-loss guarantee)
TSO_Balance_Sheet = remainder
Public_Cost = CEF_Grant + EIB guarantee cost
```

**Aggregate:**
- Sum CEF_Grant across all projects → total CEF-E need
- Sum by track → shows how much public money is needed per financing model
- Compare total CEF-E need with proposed budget (~€17bn for electricity) → quantify the remaining gap
- Show how much of the gap is eliminated by letting Track 1 projects use private capital (freeing CEF resources for Track 3)

---

## 3. Outputs

### 3.1 Project-Level Table (main output)

A CSV/Excel table with one row per project:

| Column | Description |
|---|---|
| project_id | TYNDP project ID |
| project_name | Project name |
| country_a | Country A |
| country_b | Country B |
| capacity_mw | Interconnector capacity (MW) |
| capex_meur | Total CAPEX (M€) |
| annualized_capex_meur | Annualized CAPEX (M€/year) |
| dsew_nt2030 | ΔSEW NT2030 scenario (M€/year) |
| dsew_de2040 | ΔSEW DE2040 scenario (M€/year) |
| avg_price_diff | Average absolute price differential (€/MWh) |
| price_correlation | Price correlation between zones |
| estimated_congestion_rent | Estimated annual congestion rent (M€/year) |
| commercial_viability_ratio | Congestion rent / annualized CAPEX |
| social_bcr_nt2030 | ΔSEW NT2030 / annualized CAPEX |
| social_bcr_de2040 | ΔSEW DE2040 / annualized CAPEX |
| tso_a_rating | TSO A credit rating |
| tso_b_rating | TSO B credit rating |
| tso_a_rab | TSO A RAB (€bn) |
| tso_b_rab | TSO B RAB (€bn) |
| credit_constraint_score | Max of both sides |
| credit_constrained | Boolean |
| financing_track | Track 1 / Track 2 / Track 3 |
| estimated_cef_grant | Estimated CEF grant need (M€) |
| estimated_eib_loan | Estimated EIB loan (M€) |
| estimated_private | Estimated private financing (M€) |
| project_status | Construction / Permitting / Planning / Consideration / Missing |

### 3.2 Aggregate Summary Table

| Financing track | Number of projects | Total CAPEX (€bn) | Total CEF need (€bn) | Total EIB need (€bn) | Total private (€bn) |
|---|---|---|---|---|---|
| Track 1: Merchant | | | 0 | 0 | |
| Track 2: Regulated + CBCA | | | | | |
| Track 3: Credit-constrained | | | | | |
| **Total** | | **~150** | | | |

Key metric: **How much CEF money is freed up by letting Track 1 projects use private capital?** This is the main policy-relevant number.

### 3.3 Charts (for the policy brief)

**Chart A — Financing triage scatter plot:**
- X-axis: Commercial Viability Ratio (congestion rent / annualized CAPEX)
- Y-axis: Credit Constraint Score (project CAPEX share / binding TSO RAB)
- Dot size: total CAPEX
- Dot color: financing track (green = merchant, blue = regulated, red = constrained)
- Vertical line at x = 1.0 (merchant threshold)
- Horizontal line at y = 0.15 (credit constraint threshold)
- Label key projects (ElecLink, Celtic, GSI, Bay of Biscay, Pyrenees, NeuConnect)

**Chart B — Aggregate financing stack:**
- Stacked bar chart showing €150bn total, broken down by track
- Within each track: CEF grant / EIB loan / private capital / TSO balance sheet
- Compare with: current CEF-E proposed budget (€17bn electricity share)

**Chart C — Interconnection gap by country:**
- From Ember data — countries vs. 15% target
- Bubble size = generation capacity
- Color = financing track of the main missing interconnector for that country

---

## 4. Sensitivities to Run

1. **Congestion-rate assumption:** Run all calculations at 30%, 50%, 70% → shows how sensitive merchant viability is
2. **Discount rate:** Run at 4%, 5%, 6% → changes annualized CAPEX and therefore all ratios
3. **Price scenario:** If forward-looking price data available, compare current prices vs. projected 2030/2040 prices (VRE penetration will change spreads)
4. **Credit constraint threshold:** Test at 0.10, 0.15, 0.20 → shows how many projects shift between Track 2 and Track 3

---

## 5. Known Limitations & Caveats

1. **Congestion rent is a conservative lower bound** on merchant revenue — excludes capacity market payments and ancillary services
2. **ΔSEW from TYNDP 2022 uses 2022 scenarios** — TYNDP 2024 scenarios may differ significantly (higher VRE, different demand assumptions)
3. **Historical price data reflects past market conditions** — forward-looking analysis with PyPSA-Eur would be more appropriate for 2030s projects
4. **The cannibalization effect:** building more interconnectors reduces price differentials on that border, lowering congestion rents for subsequent projects. The analysis treats each project independently.
5. **TSO credit data requires manual verification** — automated sources may be incomplete
6. **CAPEX estimates from TYNDP are promoter-reported** — actual costs frequently exceed initial estimates (cost overruns are common in large infrastructure)
7. **The classification thresholds (1.0, 0.15) are judgmental** — the sensitivity analysis partially addresses this, but the thresholds should be validated against real project financing outcomes

---

## 6. Implementation Notes

### Language & Libraries
- Python 3.x
- `pandas` for data manipulation
- `openpyxl` for reading TYNDP Excel
- `plotly` for interactive charts (compatible with the HTML policy brief)
- `requests` for ENTSO-E Transparency Platform API (if fetching live data)

### ENTSO-E API
- The ENTSO-E Transparency Platform has a RESTful API
- Requires a free API key (register at https://transparency.entsoe.eu/)
- Day-ahead prices endpoint: `GET /api?documentType=A44&...`
- Alternative: the `entsoe-py` Python package wraps the API

### File Structure
```
/project
├── data/
│   ├── raw/
│   │   ├── TYNDP2022_CBA_EU27_all-scenarios.xlsx  (already available)
│   │   ├── tyndp2024_project_sheets.csv            (to extract from TYNDP platform)
│   │   ├── entsoe_dayahead_prices_2023.csv         (to fetch via API)
│   │   └── tso_credit_data.csv                     (manual compilation)
│   └── processed/
│       ├── project_master_table.csv                 (main output)
│       └── aggregate_summary.csv
├── src/
│   ├── 01_extract_tyndp_cba.py
│   ├── 02_extract_tyndp_capex.py
│   ├── 03_fetch_entsoe_prices.py
│   ├── 04_compute_congestion_rents.py
│   ├── 05_classify_projects.py
│   ├── 06_estimate_financing.py
│   └── 07_generate_charts.py
├── outputs/
│   ├── charts/
│   │   ├── triage_scatter.html
│   │   ├── financing_stack.html
│   │   └── interconnection_gap.html
│   └── tables/
│       ├── project_level_results.xlsx
│       └── aggregate_summary.xlsx
└── README.md
```

### Priority Order
1. Start with the TYNDP 2022 CBA Excel (already available) — extract all cross-border projects with ΔSEW
2. Add CAPEX data (from TYNDP project sheets or Ember estimates)
3. Add price differential data (ENTSO-E API or manual from ACER reports)
4. Add TSO credit data (manual table)
5. Compute ratios and classify
6. Generate charts

Steps 1-2 can be done immediately. Steps 3-4 may require API access or manual data entry. Steps 5-6 are pure computation once inputs are ready.

---

## 7. Deliverables for the Policy Brief

From this analysis, the brief needs:

1. **The scatter plot** (Chart A) — this is the centrepiece of the quantitative section
2. **The aggregate numbers:** "Of the €150bn pipeline, approximately €X bn could be financed by the market, €Y bn by creditworthy TSOs with proper CBCA, and €Z bn requires targeted EU support"
3. **3-4 named project examples** positioned on the scatter plot — ElecLink (Track 1 success), Celtic (Track 2 success), GSI (Track 3 failure), FR-ES Pyrenees (Track 2 blocked)
4. **The key policy-relevant number:** "By enabling merchant financing on high-congestion corridors, approximately €X bn of CEF resources could be redirected to the credit-constrained projects that need them most"
