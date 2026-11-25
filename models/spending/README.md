# City Spending (9 US city checkbooks)

A semantic model of what nine US cities paid out, line by line, from their open checkbook datasets, joined into one
schema by our own data factory with a common function crosswalk and a normalized vendor key: Chicago, Los Angeles,
San Francisco, Austin, Dallas, Kansas City, Cincinnati, Atlanta and Boston. 4,049,310 payment lines, $105.2 billion,
the latest two complete fiscal years (Dallas one). The join answers what no single checkbook can: **938 payees were
paid by three or more of the nine cities ($6.5 billion, 10.7% of vendor spending), 18 by all nine**, and the same
supplier can be one city's main channel and another's afterthought.

## Source

- **Data:** `data-factory/spending/data/payments.parquet` (53 MB, zstd), built 24 Nov 2026 by
  `pipeline/fetch.py` and `pipeline/build.py`. Schema in `schema.md` (crosswalk and vendor normalization), sources in
  `SOURCES.md`, checks in `QUALITY.md`, findings and red team in `FINDINGS.md`.
- `data/prep.py` (duckdb, read only on the factory) writes a slim 17 MB `payments.parquet` (eight columns; integer
  vendor and department keys; the `vendor_spend` flag from `pipeline/analyze.py`'s pass-through rule) plus
  `vendors.parquet` (with `cities_paid`) and `departments.parquet`. Gitignored.
- **Licences of the inputs:** each city's open data terms as listed in the factory's `SOURCES.md` (Socrata portals
  for Chicago, Los Angeles, San Francisco, Austin, Dallas, Kansas City, Cincinnati; Atlanta's open checkbook; Boston's
  CKAN CSV files). Population: Census Vintage 2024, public domain.
- **Not at a public URL.** The model reads the Parquet files from `SpendingFolder`. For the service test they were
  copied to the `CivicData` lakehouse in Semantic Models Lab (`Files/spending/`) with `fab cp`.

### What the data can and can't say (from the factory's quality checks and red team)

- **A checkbook is not a cost.** It is cash to outside payees: no payroll, but capital outlay, debt principal and
  pass-throughs (pension funds, health plans, other governments) are in. Police and fire show only 9 to 12% of their
  audited cost here (a floor); capital-heavy utilities 67 to 137%. Use `Spending` for who gets paid; use the City
  Finances model for what a function costs. Comparing cities' checkbook totals without this split misleads.
- **Fiscal calendars differ.** Fiscal Year is the year it ends in; Chicago and Kansas City are calendar years;
  Dallas has FY2026 only. Compare a city with itself; `Spending Prior FY` is blank where the prior year isn't loaded.
- **Vendor Spending** leaves out the benefits/debt/non-departmental function and the pass-through payee list. It
  still includes other governments (LAHSA $763.5M, LAUSD, KCATA, housing authorities) and about $368M of title
  companies, a health plan and federal agencies the list misses; the red team puts the 3+-city count at about 925
  and $6.15B without them.
- **Functions are a crosswalk** (department, then fund, then vendor rules). San Francisco's PUC is one department, so
  `water_sewer` there includes power and debt service; LADWP employee benefit funds land in `electric_utility`.
  Chicago leaves department blank on ~58% of dollars (19 to 23% unmapped).
- **Lines are not payments.** Atlanta (27%) and Austin repeat identical accounting lines with no line number; LA's
  lines are invoice distributions; Chicago 2024 has year-only aggregates. All are real (totals match each portal to
  the cent), so nothing is de-duplicated: compare dollars, not line counts.
- **No dates** for San Francisco (voucher totals) and Chicago's 2024 aggregates: 954,034 lines sit on the blank Date
  row. Use Fiscal Year for whole years.
- **Vendor keys are deterministic**, not fuzzy: subsidiaries stay apart, truncated names can split one company, and
  `U S ARMY CORPS` / `US ARMY CORPS` are two keys.

## Grain and size

| Fact | Grain | Rows |
|---|---|---|
| Fact Payment | one payment line as the city publishes it | 4,049,310 |

## Star schema

```
Date (1 day)      1 --*                *-- 1  City (9, population)
Fiscal Year (3)   1 --*  Fact Payment  *-- 1  Vendor (95,722, Cities Paid, Pass-Through)
Function (17)     1 --*                *-- 1  Department (1,440 city x department)
```

Every relationship is many-to-one, single direction; one marked date table (payment date).

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Payment | 4,049,310 | (line) | measures only |
| City | 9 | City (slug) | City Name, State, Fiscal Year End, Fiscal Years Loaded, Population, Source Note |
| Fiscal Year | 3 | Fiscal Year | Fiscal Year Label |
| Vendor | 95,722 | Vendor Key | Vendor, Pass-Through, Cities Paid |
| Department | 1,440 | Department Key | Department, Department City |
| Function | 17 | Function | Function Label, ACFR Line |
| Date | 1,461 (2023-2026) | Date | Year, Quarter, Month, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `SpendingFolder` | OneLake URL of `CivicData/Files/spending` | Folder holding the three Parquet files |
| `SpendingFiles` | shared, not loaded | `AzureStorage.DataLake ( SpendingFolder )` |
| `Calendar` | shared, not loaded | 2023-01-01 to 2026-12-31 |

No incremental refresh: the factory rebuilds the whole snapshot (TmdlCheck's PRF3 warning, accepted; the full load
takes about a minute on an F2).

## Measures (16)

| Folder | Measures |
|---|---|
| Spending | Spending, Payment Lines, Reversals, Unmapped Share, Spending per Resident |
| Vendors | Vendor Spending, Payees, Top 10 Payee Share, Top 100 Payee Share, Cities Paying, Multi-City Vendors, Multi-City Vendor Spending, Multi-City Vendor Share |
| Time | Spending Prior FY, Spending YoY % |
| About | Attribution |

## Best-practice checklist

- Star schema, many-to-one single-direction relationships; one marked date table plus a fiscal-year dimension;
  auto date/time off; implicit measures discouraged.
- Every table, column, measure and expression described; format strings and display folders on every measure.
- Fact columns hidden and not available in MDX; integer surrogate keys for the two large dimensions (vendor,
  department) to keep the 4M-row fact narrow; fixed decimal (currency) for amounts, no floating point.
- DIVIDE everywhere; per-city measures (`Spending per Resident`) blank when more than one city is in context.
- One connector (`AzureStorage.DataLake`); one parameter to repoint it.

## Ten business questions (acceptance checks)

Expected answers computed first from the factory's full `payments.parquet` with duckdb (`tests/expected.py`), not
from the model's slim copy; they reproduce `FINDINGS.md` and `QUALITY.md`.

| # | Question | Expected (duckdb) |
|---|---|---|
| 1 | How much is loaded? | 4,049,310 lines; $105,153,697,731.73; vendor spending $60,744,004,239.11; 89,386 payees |
| 2 | Los Angeles FY2026 | 747,363 lines; $14,214,487,556.41 |
| 3 | Atlanta FY2026 concentration | 4,780 payees; $2,160.8M; top 10 **41.2%**; top 100 80.8% |
| 4 | Payees paid by 3+ cities; by all nine | **938**, $6,516.5M; 18 |
| 5 | Motorola Solutions | 9 cities; $278.9M; Chicago $118.8M |
| 6 | Austin culture and recreation FY2026 vs FY2025 | $370.0M vs $247.3M (**+49.6%**: the convention-centre rebuild) |
| 7 | Atlanta, Axon + Motorola per resident (two years) | $44.5M; **$85.65** |
| 8 | Chicago FY2025 unmapped share of absolute dollars | 18.9% |
| 9 | Kansas City CY2024 reversals | -$179.6M |
| 10 | Boston, dated July to September 2025; San Francisco dated lines | $387.8M; 0 (blank) |

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/spending/CitySpending.SemanticModel/definition`):
loads, validates, round-trips; every error rule passes (PRF3 warns: no incremental refresh, by design).

**In Fabric (25 Nov 2026, F2):** lakehouse **CivicData**; Parquet in
`Files/spending/`; `fab import` as "City Spending"; OAuth2 on the OneLake source; full refresh **Completed in
63 s** (4,049,310 lines). `tests/checks.dax` **10/10**, every figure to the cent; all 16 measures evaluate; zero
orphan keys on any relationship (undated lines sit on the blank Date row by design). Capacity paused; `az rest`
`properties.state` = `Paused`.
