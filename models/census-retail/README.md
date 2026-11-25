# Census Monthly Retail Trade

A star-schema semantic model of U.S. retail and food services sales by kind of business and month, not seasonally
adjusted and seasonally adjusted, January 1992 to the latest month the Census Bureau has published, with year-to-date,
prior-year, month-to-month, share and seasonal comparisons. The kind lines nest and include totals, and the model is
built so they are never added twice.

## Source

- **Publisher:** U.S. Census Bureau, [Monthly Retail Trade Survey](https://www.census.gov/retail/sales.html) (MRTS).
- **File:** `https://www.census.gov/retail/mrts/www/mrtssales92-present.xlsx` (444 KB, one sheet per year 1992 to
  2026; the copy checked here, Last-Modified 17 Nov 2026, latest month September 2026 preliminary, is in
  `samples/census-mrts-sales.xlsx` (download from the source; not committed)). Estimates are millions of dollars.
- **Licence:** public domain in the United States. The workbook is a work of the U.S. government (17 USC 105); these
  are published aggregates, not Title 13 respondent records. Census asks to be cited
  ([citation guidance](https://www.census.gov/about/policies/citation.html)): U.S. Census Bureau,
  "mrtssales92-present.xlsx," Monthly Retail Trade Survey, accessed 24 Nov 2026.
- **Refreshed by:** Power Query M in the model (`Web.Contents` + `Excel.Workbook`), straight from census.gov,
  anonymous, no API key. Full refresh on an F2: about 5.5 minutes.
- **Not loaded:** the `CY CUM`, `PY CUM` and annual `TOTAL` columns (sums of the months, not a grain), the footnotes,
  the advance release (MARTS, a smaller and different table) and inventories (another workbook).

### Field caveats

- **`(S)` and `(NA)` are not zero.** 710 cells are `(S)` (suppressed: below publication standards) and 432 are `(NA)`
  (mostly lines Census doesn't seasonally adjust). They load with a blank Sales USD and their `Cell Status`.
- **Seasonally adjusted is not price adjusted.** It removes seasonal, holiday and trading-day effects only.
- **Preliminary.** The newest month carries `(p)` and is revised in the next release (102 rows in this file).

## Grain and size

`Fact Retail Sales` holds one row per **kind of business x month x adjustment**, U.S. total only (no geography).
In the November 2026 file: **42,534 rows** (41,392 published numbers, 710 `(S)`, 432 `(NA)`), 64 kind lines,
417 months (January 1992 to September 2026).

**Double counting.** The 64 lines nest (`441` holds `4411`, which holds `44111`) and include totals and "excl." lines,
so summing every row multiplies sales. Thirteen lines, `441`-`448`, `451`-`454` and `722`, partition "Retail and food
services sales, total" with no remainder (checked for all 834 month x adjustment pairs). The model guards it three ways:

- `Include In Total` marks the thirteen; **Sales** adds only those, so with no kind filter it equals the published total.
- **Line sales** reads one published line and is blank unless exactly one kind is in context, so nested lines can't
  be added together.
- The two adjustments are the same sales measured twice: with no adjustment filter the measures read **not seasonally
  adjusted**; with both selected they are blank.

## Star schema

```
          Date (marked date table, daily)
           | Date  1
           |
           * Date
   Fact Retail Sales * ---- 1 Kind        (Kind Key)
           * Adjustment
           |
           | 1
       Adjustment
```

All three relationships are many-to-one from the fact, single direction (dimension filters fact), active.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Retail Sales | 42,534 | none (all columns hidden) | measures only |
| Date | one per day, 1 Jan 1992 to 31 Dec of the refresh year | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month (`YYYY-MM`), Month Start |
| Kind | 64 | Kind Key (hidden) | Kind (`447 Gasoline stations`, sorted in the workbook's order), Kind Code, Kind Name, Kind Type, Include In Total, Parent Code, Parent Kind, Level |
| Adjustment | 2 | Adjustment | Adjustment (not adjusted first) |

## Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `CensusBaseUrl` | `https://www.census.gov/` | Data source root (answers 200); the file is `RelativePath = "retail/mrts/www/mrtssales92-present.xlsx"` |
| `CalendarStart` | 1992-01-01 | First day of the Date table (the file's first month) |
| `CalendarEnd` | 31 December of the current year (computed) | Whole years, grows with the file |

`MrtsCells` is a shared, unloaded query that parses every sheet once and feeds both the fact and Kind.
No incremental refresh: the source is one 444 KB workbook that every partition would download again.

## Measures (24)

| Folder | Measures |
|---|---|
| Sales | Sales, Sales millions |
| Line | Line sales, Line sales millions |
| Mix | Share of retail and food services, Share of parent |
| Time | Sales YTD, Sales prior year, Sales YoY %, Sales prior month, Sales month to month %, Line sales YTD, Line sales prior year, Line sales YoY % |
| Adjustment | Not adjusted sales, Seasonally adjusted sales, Seasonal factor |
| Audit | Kinds in total, Suppressed cells, Not available cells, Preliminary sales, Months in scope, Sales in adjustment (hidden), Last Data Date (hidden) |

Notes on the logic:

- **Sales vs Line sales.** Use Sales for the total and the thirteen lines (it adds across them); use Line sales for
  any single line, including the total line, "excl." lines and subsectors such as `4541` (where Sales is blank).
- **Shares** divide Line sales by the total line (kind filters removed) or by the parent line (`Kind[Parent Code]`,
  the longest shorter published code: `44111` > `4411`, `443141` > `443`, `722513, 722514, 722515` > `7225`).
- **YTD stops at the data**: blank after the last month in the workbook.
- **Prior year matches the months that have data**: the prior-year measures shift only dates up to the last month in
  the workbook, so 2026 (January to September) compares with January to September 2025, not all of 2025.
- **Seasonal factor** works for the total and for any one kind line (with one kind in context the two adjusted measures
  read Line sales, so 4541 has a factor as 441 does); it is not adjusted / seasonally adjusted, the ratio of the two published series (0.976 for
  September 2026), not Census's official factor files.

## Ten business questions (acceptance checks)

Millions of dollars, pinned to the November 2026 workbook. Expected answers were recomputed from the raw workbook
with Python (openpyxl), independently of the M; `tests/checks.dax` asks each one of the deployed model.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | Retail and food services, not adjusted, Sep 2026 | 728,961 | 728,961 (Sales and total line; 13 kinds) | Pass |
| 2 | Same, Sep 2025, and YoY | 680,630; +7.101% | 680,630; +7.10% | Pass |
| 3 | Seasonally adjusted total, Sep 2026 vs Sep 2025 | 746,637 vs 700,614; +6.569% | 746,637 vs 700,614; +6.57% | Pass |
| 4 | Not adjusted, Jan-Sep 2026 vs Jan-Sep 2025 | 6,448,116 vs 6,153,323; +4.791% | 6,448,116 vs 6,153,323; +4.79%; Sales YTD and total line YTD 6,448,116 | Pass |
| 5 | Gasoline stations, not adjusted, Sep 2026, share | 69,135; 9.484% | 69,135; 9.48% | Pass |
| 6 | Nonstore retailers; electronic shopping and mail-order | 119,973, 16.458%; 113,238, 94.386% of nonstore | 119,973, 16.46%; 113,238, 94.39% of parent; Sales blank for 4541 | Pass |
| 7 | Food services and drinking places, not adjusted, Sep 2026 | 91,767; 12.589% | 91,767; 12.59% | Pass |
| 8 | Not adjusted total, Dec 2025 vs Sep 2025 | 780,707 vs 680,630; +14.704% | 780,707 vs 680,630; +14.70% | Pass |
| 9 | Seasonally adjusted gasoline stations share, Sep 2026 | 67,581 / 746,637 = 9.051% | 67,581; 9.05% | Pass |
| 10 | Not adjusted total, Jan 1992 | 142,051 (thirteen lines agree) | 142,051 and 142,051; 13 kinds | Pass |

Also checked: 42,534 rows (41,392 published, 710 suppressed, 432 not available, none unrecognised); 64 kinds; 417
months; 102 preliminary rows; zero orphan keys; the thirteen lines equal the total line in all 834 month x adjustment
pairs; Line sales is blank with no kind filter; Sales is blank with both adjustments selected and reads not adjusted
with none; YTD is blank after September 2026; the parent codes above.

## Changes from the design (`design/census-retail.md`)

- **Kind key is the code, not code + name.** Census labels drift between the two sections of the same sheet
  (`4453` "Beer, wine and liquor" / "Beer, wine, and liquor"; `453` "store" / "stores"; `4541` "mail order" /
  "mail-order"), so a code + name key would split each into two kinds, one per adjustment. The key is the code, or the
  name for the seven uncoded lines; Kind Name is the newest not adjusted label. A relationship also needs one column.
- **A unique `Kind` label** (`447 Gasoline stations`) for visuals: Kind Name isn't unique (`4522` and `45221` are both
  "Department stores") and so can't carry a sort-by column.
- **Adjustment double counting.** The design's measures summed both series when no adjustment was filtered (every
  number doubled). Sales and Line sales read not adjusted by default and are blank with both selected.
- **Line sales is guarded** (blank unless one kind is in context); the design's plain SUM over every row multiplied sales.
- **`(S)` count.** The design said 1,142 `(S)` cells; 1,142 is all non-numeric cells: 710 `(S)` and 432 `(NA)`. Both
  load blank, told apart by `Cell Status`; `Not available cells` added.
- **Parent Code** is the longest shorter prefix that exists (the design's "last digit removed" misses `443141` > `443`,
  `45330` > `453` and the combined lines), taken from the first code of a combined line. `Parent Kind` added.
- **Date table is daily**, built from parameters (the design's monthly table can't be marked as a date table reliably,
  and TOTALYTD / SAMEPERIODLASTYEAR expect a continuous calendar).
- **Robust M.** Columns picked by position and month columns by header text (the design's promoted-header M with
  `"NAICS  Code"` breaks on blank headers and on the annual `TOTAL` column, which only complete years have); one shared
  query parses the workbook for both the fact and Kind; data source root `https://www.census.gov/` (the
  `/retail/mrts/www/` folder answers 404, which would fail the service's credential test).
- **YTD stops at the data** (blank after the last month), as in model #2.
- **Added:** Kind Type, Level, Months in scope, Sales in adjustment (hidden helper), Last Data Date (hidden).
- **Q2** in the design reads "7.101% (7.100921)"; the ratio is 7.10092%.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/census-retail/CensusRetail.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except one deliberate warning:

| Rule | Status |
|---|---|
| Descriptions on every table, column, measure and expression | Pass |
| Format strings; `%` formats on percentages; visible measures in display folders | Pass |
| `summarizeBy: none` on numeric columns; implicit measures discouraged | Pass |
| Foreign keys hidden; dimension keys `isKey`; month, year-month, kind and adjustment labels sorted | Pass |
| Marked date table; auto date/time off | Pass |
| Many-to-one, single-direction relationships on matching types; no islands | Pass |
| Fixed decimal (no floating point); fact columns hidden, `isAvailableInMdx: false` | Pass |
| DIVIDE, no IFERROR, column/measure reference style, every reference resolves | Pass |
| PRF3 incremental refresh on the fact | **Warn, deliberate**: 42,534 rows from one 444 KB workbook |

Model #3's lesson (TmdlCheck passed a measure the engine rejected) is why `tests/checks.dax` queries every measure,
not only the ones the ten questions need: all 24 evaluated in the service on the first deploy (check 13 covers
prior month, month to month, the line prior-year twins and preliminary sales).

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in 5 min 26 s**, and the 10 questions matched **10/10**. Details in
the [run log](../../docs/toolchain.md#run-log).

**After Grok's review (24 Nov 2026):** redeployed with the kind-aware adjustment measures and the data-matched prior
year; refresh 13 min 32 s (sharing the F2 with the NYC load); the 10 questions still **10/10**, check 14 confirms the
fixes (seasonal factor for 441, 4541 and the total; 2026 prior year 6,153,323 = January to September 2025), and all
24 measures evaluate.
