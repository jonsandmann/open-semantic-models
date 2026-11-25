# City Finances from audited ACFRs (54 US cities)

A semantic model of US city finances read by our own data factory from each city's audited Annual Comprehensive
Financial Report (ACFR): the 50 largest US cities plus ten Washington cities near Bellevue, 54 of them read. 3,751
figures, each city's latest posted fiscal year (FY2025 for 52, FY2024 for Bakersfield and Redmond) and the prior
year from the same report's comparative column. **Every figure cites its PDF and page**, so any number in a report
built on this model can be checked against the audited statement. On their latest reports the 54 cities spent
$184.5 billion, $4,424 per resident, and 33 of them carry a negative unrestricted net position.

## Source

- **Data:** `data-factory/cities/data/city_finances.csv` (one row per city x fiscal year x figure, USD
  millions), run 3 of 24 Nov 2026. Schema in `schema.md`, coverage gaps in `MISSING.md`, extractor checks and spot
  checks in `QUALITY.md`, the 59 cities in `sources/cities.csv`.
- `data/prep.py` (duckdb, read only on the factory) writes `figures.parquet` (values converted to whole dollars;
  Year Position Latest / Prior), `reports.parquet` (one PDF URL per city and year) and `cities.parquet` (all 59
  attempted, with In Data and Table Sums OK). Gitignored.
- **Licence:** ACFRs are public records each city publishes; the figures are facts read from them, with citations.
  Population: Census Bureau Vintage 2024 (`sub-est2024`), public domain.
- **Not at a public URL.** The model reads the Parquet files from `FinancesFolder`. For the service test they were
  copied to the `CivicData` lakehouse in Semantic Models Lab (`Files/cities/`) with `fab cp`.

### What the data can and can't say (from the factory's schema caveats and quality checks)

- **Five of the 59 aren't read** (`City[In Data]` false): New York (three-year, two-page table), Philadelphia, Kent
  and Miami (image or scanned tables), Bothell (excluded: columns grouped by year). Per-resident and total measures
  count only the cities that report the figure.
- **Totals are comparable; lines need care.** Function lines are mapped by label synonyms (SF's "Public
  protection", Virginia Beach's department-named functions and airports, transit and ports land in `exp_other` with
  their label in `Source Label`). 7 of 54 cities fail a sum check (`City[Table Sums OK]`): use their totals, not
  their lines.
- **The reporting entity differs.** Some cities hold an airport or utilities as business-type activities (Seattle
  City Light: 43% of Seattle's expenses); others don't. `Business-Type Share of Expenses` shows how much. San
  Francisco is a city-county and Washington DC runs state functions, so they top every per-resident ranking.
- **Accrual, not cash.** Expenses include payroll, pension expense and depreciation and exclude capital outlay and
  debt principal: the opposite of the City Spending checkbook model. Don't add the two.
- **Hand-checked is a small sample:** 30 figures read against the PDF page across three runs (29 of 30 right first
  time on rows still in the data). Every other row is unchecked. `Total Assets`, `Total Liabilities`,
  `Net Pension Liability` (19 city-years) and `General Fund Balance` were never in a random sample: treat as unchecked.
- **Fiscal years end on different days** (30 June, 30 September, 31 December). `Fiscal Year End[Year]` is the year
  the fiscal year ends in; `Year Position = Latest` compares each city on its own newest audited year.
- `table_sums_ok` is an arithmetic check of the extracted table, not an audit; the MD&A tables are required
  supplementary information that agree with the audited statements.

## Grain and size

| Fact | Grain | Rows |
|---|---|---|
| Fact Figure | one city x fiscal year x figure (several `*_other` lines per city-year, by label) | 3,751 |

## Star schema

```
Fiscal Year End (1 day) 1 --*               *-- 1  City (59; 54 in data)
Year Position (2)       1 --*  Fact Figure  *-- 1  Figure (43, statement and section)
                                            *-- 1  Report (108, Source PDF)
```

Every relationship is many-to-one, single direction; one marked date table (fiscal year end).

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Figure | 3,751 | Row ID | measures only (page and extraction method kept, hidden) |
| City | 59 | City Key (FIPS place) | City, State, Population, City Group, In Data, Table Sums OK |
| Figure | 43 | Figure ID | Figure Label (statement order), Statement, Section |
| Report | 108 | Report Key | Report Fiscal Year End, Source PDF (web URL) |
| Year Position | 2 | Year Position | Latest, Prior |
| Fiscal Year End | 1,095 (2023-2025) | Date | Year (= fiscal year), Quarter, Month, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `FinancesFolder` | OneLake URL of `CivicData/Files/cities` | Folder holding the three Parquet files |
| `FinanceFiles` | shared, not loaded | `AzureStorage.DataLake ( FinancesFolder )` |
| `Calendar` | shared, not loaded | 2023-01-01 to 2025-12-31 |

No incremental refresh (3,751 rows; TmdlCheck's PRF3 warning, accepted).

## Measures (31)

| Folder | Measures |
|---|---|
| Figures | Figure Value, Total Revenues, Total Expenses, Revenues less Expenses, Net Position, Unrestricted Net Position, Total Assets, Total Liabilities, Net Pension Liability, General Fund Balance, Property Tax Revenue |
| Shares | Share of Total Expenses, Share of Total Revenues, Property Tax Share of Revenues, Business-Type Share of Expenses |
| Per Resident | Revenues per Resident, Expenses per Resident, Net Position per Resident, Unrestricted Net Position per Resident, Net Pension Liability per Resident, Years per City |
| Time | Total Revenues Prior Year, Revenue Growth %, Total Expenses Prior Year, Expense Growth % |
| Coverage | Figures Read, Cities Reporting, Hand-Checked Figures, Cities with Sums OK, Cities with Negative Unrestricted Net Position |
| About | Attribution |

Each headline measure picks one figure (`KEEPFILTERS` on Figure ID), so a visual never adds a total to its parts.
Per-resident measures divide by the population of the cities that report the figure and are blank when any city has
more than one fiscal year in context. `Share of Total Expenses` / `Revenues` are for figure lines on rows; at the
grand total they are meaningless.

## Best-practice checklist

- Star schema, many-to-one single-direction relationships; one marked date table; auto date/time off; implicit
  measures discouraged.
- Every table, column, measure and expression described; format strings and display folders on every measure;
  percentages in percent format; figure labels sorted in statement order.
- Fact columns hidden and not available in MDX; dimension keys marked `isKey`; fixed decimal (currency) for values;
  DIVIDE everywhere; Source PDF as a web URL for drill-through to the audited page.
- One connector (`AzureStorage.DataLake`); one parameter to repoint it.

## Ten business questions (acceptance checks)

Expected answers computed first from the factory's `city_finances.csv` with duckdb (`tests/expected.py`). Recomputed
25 Nov 2026 after the factory's run-4 fix: Charlotte's government-wide figures had been read 1,000× too small (its
MD&A states "Dollar Amounts in Millions" once, above the tables), Oklahoma City's total assets and liabilities were a
change column, and Chicago's net position rows (from the enterprise funds' statement) are left out. Q1, Q3 and Q6
moved; the Fabric run below was on the earlier read.

| # | Question | Expected (duckdb) |
|---|---|---|
| 1 | How much is loaded? | 3,751 figures; 54 cities; 30 hand-checked; 47 pass every sum check |
| 2 | Seattle FY2025 revenues, expenses, net position | $6,275.0M; $5,573.59M; $10,362.0M |
| 3 | Every city on its latest report: expenses, cities, per resident | $184,539.64M; 54; **$4,423.75** |
| 4 | San Francisco FY2025 expenses per resident | $18,465.67 |
| 5 | Los Angeles total revenues FY2025 vs FY2024 | $24,276.13M vs $21,851.11M (**+11.1%**) |
| 6 | Latest report: cities with negative unrestricted net position; lowest | **33**; Dallas -$4,893.45M |
| 7 | Phoenix FY2025 public safety share of total expenses | 30.7% |
| 8 | Seattle FY2025 business-type share of expenses | 43.4% |
| 9 | Latest report: net pension liability, cities, per resident | $37,836.47M; 19; $2,510.58 |
| 10 | Washington cities near Bellevue, latest: cities, property tax share of revenues | 8; 11.9% |

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/city-finances/CityFinances.SemanticModel/definition`):
loads, validates, round-trips; every error rule passes (PRF3 warns, by design). TmdlCheck's reference rule doesn't
know `ADDCOLUMNS` columns, so the per-resident measures iterate the City table instead.

**In Fabric (25 Nov 2026, F2):** lakehouse **CivicData**; Parquet in
`Files/cities/`; `fab import` as "City Finances (ACFR)"; OAuth2 on the OneLake source; full refresh **Completed in
5 s**. `tests/checks.dax` **10/10**; all 31 measures evaluate; zero orphan keys. Capacity paused; `az rest`
`properties.state` = `Paused`.
