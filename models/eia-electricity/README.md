# EIA Electricity Retail Sales

A star-schema semantic model of US electricity retail sales by state, month and sector: revenue, kilowatthours sold,
customer accounts and average price, with year-to-date, prior-year and share-of-US comparisons, January 2010 to the
latest month EIA has published.

## Source

- **Publisher:** US Energy Information Administration (EIA), [Form EIA-861M, monthly sales and revenue](https://www.eia.gov/electricity/data/eia861m/).
- **File:** `https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx` (about 2.3 MB; the copy checked
  here, Last-Modified 23 Oct 2026, is in `samples/` (download from the source; not committed)). Only the sheet `Monthly-States` is loaded; the
  territory, year-to-date and US sheets are aggregates and would double-count.
- **Licence:** public domain. EIA data is a work of the US government and carries no copyright
  ([EIA copyright and reuse](https://www.eia.gov/about/copyrights_reuse.php)); citing "Source: US Energy Information
  Administration" is requested.
- **Refreshed by:** Power Query M in the model (`Web.Contents` + `Excel.Workbook`), straight from eia.gov, anonymous.
  No API key (the `api.eia.gov` route needs one; the xlsx does not).
- **Units:** EIA publishes revenue in thousand dollars and sales in megawatthours; the model stores dollars and
  kilowatthours. EIA's per-row price column (cents/kWh) is not loaded; price is recomputed from the sums.

## Grain and size

`Fact Retail Sales` holds one row per **state (50 states and DC) x month x sector** for four sectors (Residential,
Commercial, Industrial, Transportation). EIA's Total column is the sum of the four and is not loaded.
In the October 2026 file: 51 areas x 200 months (January 2010 to August 2026) x 4 sectors = **40,800 rows**.
January to August 2026 carry `Data Status = Preliminary` until EIA's annual survey closes.

## Star schema

```
              Date (marked date table, daily)
               | Date 1
               |
               * Date
     Fact Retail Sales * ---- 1 State   (State Code)
               * Sector
               |
               | 1
             Sector
```

All three relationships are many-to-one from the fact, single direction (dimension filters fact), active.
The fact keys each month to its first day; the daily date table lets standard time intelligence run unchanged.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Retail Sales | 40,800 | none (all columns hidden) | measures only |
| Date | one per day, 1 Jan 2010 to 31 Dec of the refresh year | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month (`YYYY-MM`), Month Start |
| State | 51 | State Code | State Code, State Name, Census Region, Census Division |
| Sector | 4 | Sector | Sector (sorted in EIA's order) |

## Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `EiaBaseUrl` | `https://www.eia.gov/electricity/data/eia861m/` | Data source root; the file is `RelativePath = "xls/sales_revenue.xlsx"` |
| `CalendarStart` | 2010-01-01 | First day of the Date table (the file's first month) |
| `CalendarEnd` | 31 December of the current year (computed) | Whole years, grows with the file |

No incremental refresh: the source is one 2.3 MB workbook and a full refresh takes about 11 seconds on an F2.

## Measures (22)

| Folder | Measures |
|---|---|
| Sales | Revenue, Sales kWh, Sales MWh, Customers, Average customers |
| Price | Price cents per kWh, Revenue per customer, Sales per customer kWh |
| Mix | Share of US sales, Share of state sales |
| Time | Sales YTD kWh, Revenue YTD, Sales prior year kWh, Revenue prior year, Price prior year cents per kWh, Sales YoY %, Revenue YoY %, Price YoY cents, Sales latest month kWh |
| Audit | Months in scope, Preliminary months, Last Data Date (hidden) |

Notes on the logic:

- **Price is a ratio of sums**, revenue / kWh x 100, never an average of EIA's per-row price.
- **Customers are semi-additive.** They add across states and sectors but take the last month in the filter context,
  so a year shows December's accounts, not twelve months summed. Revenue and kWh per customer divide by `Average
  customers` (each month's accounts averaged over the months in context): one month gives the monthly bill, a whole year
  the annual bill, a year in progress the bill so far (`Months in scope` says how many months).
- **YTD stops at the data.** YTD measures are blank after `[Last Data Date]`, so a 2026 line doesn't run flat to December.
- **Prior year matches the months that have data.** The prior-year measures shift only dates up to the last data month,
  so 2026 (January to August) compares with January to August 2025, not all of 2025.
- **Share of US sales** removes only the State filter; sector and date filters stay. "US" is the 50 states plus DC.

## Ten business questions (acceptance checks)

Pinned to August 2026 (the file grows monthly). Expected answers were computed from the raw sheet with Python
(`Decimal` sums, Total excluded); `tests/checks.dax` asks each one of the deployed model.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | California residential, Aug 2026 | 11,160,409 MWh; $3,320,537,900; 14,138,808 customers; 29.75 c/kWh | 11,160,409; $3,320,537,900; 14,138,808; 29.7528 | Pass |
| 2 | US residential revenue, Aug 2026 | $30,455,229,710 | $30,455,229,710 | Pass |
| 3 | Washington commercial price, Aug 2026 | 11.81 c/kWh; 2,955,812.7 MWh; $349,212,000; 408,477 | 11.8144; 2,955,812.7; $349,212,000; 408,477 | Pass |
| 4 | California all sectors, Aug 2026 vs Aug 2025 | 26,720,654.69 vs 24,383,435.14 MWh, +9.585% | 26,720,654.69 vs 24,383,435.14, +9.59% | Pass |
| 5 | Texas share of US industrial sales, Aug 2026 | 15.868% | 15.87% | Pass |
| 6 | California residential YTD through Aug 2026 | 58,930,561.1 MWh | 58,930,561.1 | Pass |
| 7 | Highest state residential price, Aug 2026 | Hawaii, 47.18 c/kWh on 257,565.21 MWh | Hawaii, 47.1833, 257,565.21 | Pass |
| 8 | US commercial customers, Aug 2026 | 19,658,797 | 19,658,797 | Pass |
| 9 | US transportation sales, Aug 2026 | 603,959.78 MWh | 603,959.78 | Pass |
| 10 | Alaska all-sector price, Aug 2026 | 25.32 c/kWh; $124,600,400; 492,109.63 MWh; 365,040 | 25.3196; $124,600,400; 492,109.63; 365,040 | Pass |

Also checked: 40,800 rows, 200 months, zero fact rows without a Date, State or Sector; YTD accumulates January to
August 2026 and is blank after; customers by month stay a monthly count (about 16 million in California).

## Changes from the design (`design/eia-electricity.md`)

- **Fact column names.** The design named fact columns `Revenue USD`, `Sales kWh` and `Customers`, colliding with
  the measures `Sales kWh` and `Customers` (a column and measure can't share a name usefully, and BPA flags it). They
  are `Revenue Amount USD`, `Sales Amount kWh` and `Customer Count`.
- **`kWh per customer` -> `Sales per customer kWh`**: names start with a capital (BPA naming rule).
- **Customers** was a plain SUM, which double-counts across months; it is now semi-additive (last month in context).
  Single-month answers are unchanged.
- **Date table is daily**, not one row per month: Power BI's mark-as-date-table check expects contiguous days with no
  gaps, and TOTALYTD / SAMEPERIODLASTYEAR are written for a continuous calendar. Month columns carry the monthly view. It is built from calendar
  parameters, not from the fact, so the workbook isn't downloaded twice.
- **Sales latest month kWh** used `MAX ( 'Date'[Date] )`, which is the calendar's last day (December, blank). It uses
  the fact's last month instead. YTD measures are also blanked after the last data month.
- **Data source root.** `Web.Contents` points at `…/eia861m/` (answers 200) with `RelativePath = "xls/sales_revenue.xlsx"`;
  the `xls/` folder answers 403, which fails the service's credential test (the same gotcha as model #1).
- **Robust M.** Columns are picked by position from `Table.ColumnNames` and the notes row is dropped with
  `[Year] is number`; the design's `Value.FromText(Text.From(null))` filter would error on blank cells.
- **Preliminary is eight months, not one.** All of January to August 2026 is `Preliminary` in this file (408 rows).
- Added `Preliminary months` (Audit) so preliminary figures can be flagged; `Data Status` itself stays hidden.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/eia-electricity/EiaElectricity.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except one deliberate warning:

| Rule | Status |
|---|---|
| Descriptions on every table, column, measure and expression | Pass |
| Format strings; `%` formats on percentages; visible measures in display folders | Pass |
| `summarizeBy: none` on numeric columns; implicit measures discouraged | Pass |
| Foreign keys hidden; dimension keys `isKey`; month and year-month labels sorted | Pass |
| Marked date table; auto date/time off | Pass |
| Many-to-one, single-direction relationships on matching types; no islands | Pass |
| Fixed decimal (no floating point); fact columns hidden, `isAvailableInMdx: false` | Pass |
| DIVIDE, no IFERROR, column/measure reference style, every reference resolves | Pass |
| PRF3 incremental refresh on the fact | **Warn, deliberate**: 40,800 rows from one workbook; partitions would each re-download the whole file |

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in 11 s**, and the 10 questions above matched 10/10. Details in the
[run log](../../docs/toolchain.md#run-log).

**After Grok's review (24 Nov 2026):** redeployed with `Average customers` and the data-matched prior year; refresh 7 s
(EIA had since published September 2026: 41,004 rows, 201 months); the 10 August 2026 questions still **10/10**, check
13 confirms the per-customer and prior-year fixes, and all 22 measures evaluate.
