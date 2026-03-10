# Methodology

This note lists the key assumptions used in the notebook-based financing triage.

## Sources

- **TYNDP 2024 project sheets:** project list, status, transfer capacity, CAPEX, and welfare results.
- **TYNDP 2022 CBA:** fallback welfare results where needed.
- **Amber hourly wholesale electricity prices:** used for the commercial screen.
- **TSO annual reports, regulatory filings, and CEER material:** used for TSO financial capacity, especially RAB.
- **Sovereign fiscal data and ratings:** used as an additional financing-capacity check.

## Key metrics

### 1. Social benefit-cost ratio

This is the first economic screen. It asks whether a project creates enough value for Europe as a whole to justify support, even if it is not commercially financeable.

The ratio is:

```text
annual socio-economic welfare gain / annualised CAPEX
```

The welfare input comes from TYNDP. In the current implementation, the preferred source is the **TYNDP 2024 2030NT-EU27** scenario, with fallback to other available 2024 and then 2022 welfare fields.

This ratio does **not** decide the financing track on its own. It is used to judge whether an uncommercial project may still have a strong public case.

### 2. Commercial ratio

This asks whether the project could plausibly recover its cost from cross-border trading value.

The ratio is:

```text
estimated annual congestion-rent proxy / annualised CAPEX
```

The congestion-rent proxy is based on:

- hourly price differences;
- transfer capacity;
- a **30 percent congestion-rate assumption**.

This should not be read as physical utilisation of the line. It is a simplifying assumption for the share of the year during which the project is assumed able to monetise price spreads at full transfer capacity. The notebook currently treats **30 percent** as the base case, with higher values tested in sensitivity analysis.

The implementation uses the **absolute hourly price spread** and sums it across the year. This is meant to capture the gross trading opportunity whenever there is a price difference, regardless of direction.

### 3. Credit-constraint score

This asks whether the relevant transmission operators are large enough to carry their share of the project.

The ratio is:

```text
project CAPEX share / TSO RAB
```

**RAB** means **regulated asset base**. It is the asset value on which a regulated TSO is allowed to earn a return. In practice, it is a simple proxy for the size of the TSO balance sheet and therefore for its financing capacity.

In the current implementation, a project is treated as credit-constrained if, on either side of the interconnector:

- the project CAPEX share is above **15 percent of TSO RAB**;
- the TSO is below investment grade;
- the sovereign is fiscally constrained.

## Participant allocation assumptions

These assumptions matter because the credit-constraint result depends on who is assumed to pay.

- where no verified allocation is available, the current model uses **equal shares across participants**;
- for a standard two-country project, that means a default **50/50 split**;
- for multi-country projects, equal shares are only a placeholder, not a measured allocation;
- the present implementation still reduces the credit screen to side `A` and side `B`, so additional participants in more complex corridors are not yet fully captured.

A better next step would be to replace these placeholder shares with verified CBCA or sponsor allocations, or with a more explicit value-based allocation approach such as **Shapley values** for marginal contribution.

## Other core assumptions

- CAPEX is annualised using a **5 percent discount rate** over **25 years**.
- The commercial threshold for **Track 1** is **commercial ratio > 1.0**.
- The credit threshold for **Track 3** is **credit-constraint score > 0.15**, unless the TSO rating or sovereign constraint already triggers the flag.

## Classification logic

- **Track 1:** the commercial ratio is above `1.0`.
- **Track 2:** the commercial ratio is not above `1.0`, and the project is not credit-constrained.
- **Track 3:** the commercial ratio is not above `1.0`, and at least one side is credit-constrained.

In other words, the model first asks whether the project looks commercially financeable. If not, it asks whether the regulated parties can still carry it. If they cannot, the project falls into the targeted-support track.

## Main caveats

- The hourly price input is a **proxy** for commercial value, not a forward-looking merchant revenue model.
- Some TSO RAB values, especially for smaller or unrated TSOs, are estimated.
- Participant shares are often assumed rather than taken from verified CBCA decisions.
- The current method is strongest for bilateral projects and less precise for multi-country corridors.
