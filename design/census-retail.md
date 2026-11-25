# Census Monthly Retail Trade

Model #4. Retail, the next industry after taxi, electricity, and hospitals. U.S. government work: public domain in the United States under 17 USC 105. These are published aggregates, not Title 13 respondent records. Cite the Census Bureau (citation page revised 24 Feb 2026: https://www.census.gov/about/policies/citation.html). No API key. Downloaded 24 Nov 2026. Every answer was summed from this file.

## Source

| Item | Value |
|---|---|
| Release page | https://www.census.gov/retail/sales.html (advance release 17 Nov 2026 is a different, smaller MARTS table; this model uses the full MRTS history) |
| Workbook | https://www.census.gov/retail/mrts/www/mrtssales92-present.xlsx |
| Size | 444,013 bytes. Last-Modified Tue, 17 Nov 2026 13:30:11 GMT. Under 50 MB, not gitignored. |
| Saved as | `samples/census-mrts-sales.xlsx` (download from the source; not committed) |
| Sheets | One sheet per year, `2026` back to `1992` (35 sheets). |
| Layout | Row 1 title, row 2 unit note, row 4 headers, row 5 month names. `NOT ADJUSTED` then the lines, then `ADJUSTED(2)` and the same lines again. Estimates are millions of dollars. A month header with `(p)` is preliminary. September 2026 is the latest month in this file and is preliminary. October 2026 is only on the advance release, not here. |
| Suppressed | `(S)` means withheld. Store null, never zero. 1,142 of 42,534 published cells in this file are `(S)`. |
| What not to load | `CY CUM` and `PY CUM` columns. They match a January–latest sum of the monthly cells (checked on the 2026 total: 6,448,116 and 6,153,323) but they are not a grain. Inventories are a different workbook. |

Suggested citation: U.S. Census Bureau, “mrtssales92-present.xlsx,” Monthly Retail Trade Survey, vintage accessed 24 Nov 2026, https://www.census.gov/retail/mrts/www/mrtssales92-present.xlsx.

## Grain

One fact row per **kind of business × month × adjustment** (not seasonally adjusted, or seasonally adjusted). Geography is the U.S. total only, so there is no state dimension. About 41,392 numeric rows plus the suppressed cells you choose to keep as nulls.

The lines nest. `441` contains `4411`, which contains `44111`. Summing every row multiplies sales. Thirteen published codes partition “Retail and food services sales, total” with no remainder. Checked for January of 1992, 2000, 2010, 2020, 2025, and 2026, and for September 2026 not seasonally adjusted: the thirteen sum to the published total exactly (September 2026: 728,961 million dollars).

Those codes are `441`, `442`, `443`, `444`, `445`, `446`, `447`, `448`, `451`, `452`, `453`, `454`, `722`. `Include In Total` is true only on those thirteen. Every other line, including the total line and the “excl. …” lines, is kept for direct lookup and is excluded from the additive measures.

## Star schema

### Fact Retail Sales

| Column | Type | Notes |
|---|---|---|
| Date | date | First of the month. FK to Date |
| Kind Code | text | FK to Kind. Blank on the total and the “excl.” lines; use Kind Name as the key there |
| Kind Name | text | The published label. Part of the key together with Kind Code |
| Adjustment | text | `Not seasonally adjusted` or `Seasonally adjusted` |
| Include In Total | bool | True only for the thirteen codes |
| Sales USD | decimal | Millions × 1,000,000. Null when the cell is `(S)` |
| Preliminary | bool | True when the month header contains `(p)` |

### Date (marked date table)

Monthly, 1 Jan 1992 through 1 Dec of the latest year in the file. `Date`, `Year`, `Month Number`, `Month`, `Year Month`, `Year Month Sort`. Mark on `Date`. Auto date/time off.

### Kind

`Kind Code`, `Kind Name` (the pair is the key; a few lines have no code), `Include In Total`, `Parent Code` (the shorter NAICS prefix when one exists: `44111` → `4411` → `441`), `Level` (count of digits, 0 for the uncoded total lines). Names come from the workbook, not a hand list, because labels drift (`mail order` vs `mail-order`).

### Adjustment

Two rows. `Not seasonally adjusted` is the default for “what was sold.” `Seasonally adjusted` is Census’s holiday and trading-day adjustment, not a price adjustment. The workbook says adjusted figures are not adjusted for price changes.

### Relationships

| From | To | Cardinality | Filter |
|---|---|---|---|
| Fact[Date] | Date[Date] | many to one | single |
| Fact[Kind Code]+[Kind Name] | Kind | many to one | single |
| Fact[Adjustment] | Adjustment[Adjustment] | many to one | single |

## Measures

Folder in parentheses. Additive measures sum only `Include In Total`. A filtered kind that is not one of the thirteen is read with the lookup measures, which do not roll children up.

Additive

1. **Sales** `$#,0` (Sales). `CALCULATE ( SUM ( 'Fact Retail Sales'[Sales USD] ), 'Fact Retail Sales'[Include In Total] )`. The thirteen kinds. Equals the published total when no kind filter is on.
2. **Sales millions** `#,0` (Sales). `DIVIDE ( [Sales], 1000000 )`. The unit Census prints.
3. **Kinds in total** `0` (Audit). `CALCULATE ( DISTINCTCOUNT ( 'Fact Retail Sales'[Kind Code] ), 'Fact Retail Sales'[Include In Total] )`. Should be 13 for a full month.

Lookup (one published line, children not included)

4. **Line sales** `$#,0` (Line). `SUM ( 'Fact Retail Sales'[Sales USD] )`. Use with a single kind selected. This is how the total line and the “excl.” lines are read.
5. **Line sales millions** `#,0` (Line). `DIVIDE ( [Line sales], 1000000 )`.

Mix

6. **Share of retail and food services** `0.0%` (Mix). `DIVIDE ( [Line sales], CALCULATE ( [Line sales], Kind[Kind Name] = "Retail and food services sales, total", REMOVEFILTERS ( Kind ) ) )`. Adjustment and date stay.
7. **Share of parent** `0.0%` (Mix). Line sales divided by the parent code’s line sales in the same month and adjustment.

Time. Every time measure below has a twin in the Time folder built on `[Line sales]` instead of `[Sales]` (`Line sales YTD`, `Line sales prior year`, `Line sales YoY %`). The twins are how a single published line, including the total line, is compared. The three below are the additive thirteen.

8. **Sales YTD** `$#,0` (Time). `TOTALYTD ( [Sales], 'Date'[Date] )`.
9. **Sales prior year** `$#,0` (Time). `CALCULATE ( [Sales], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
10. **Sales YoY %** `+0.0%;-0.0%;0.0%` (Time). `DIVIDE ( [Sales] - [Sales prior year], [Sales prior year] )`.
11. **Sales prior month** `$#,0` (Time). `CALCULATE ( [Sales], DATEADD ( 'Date'[Date], -1, MONTH ) )`.
12. **Sales month to month %** `+0.0%;-0.0%;0.0%` (Time). `DIVIDE ( [Sales] - [Sales prior month], [Sales prior month] )`.

Seasonal comparison

13. **Not adjusted sales** `$#,0` (Adjustment). `CALCULATE ( [Sales], Adjustment[Adjustment] = "Not seasonally adjusted" )`.
14. **Seasonally adjusted sales** `$#,0` (Adjustment). The other adjustment.
15. **Seasonal factor** `0.000` (Adjustment). `DIVIDE ( [Not adjusted sales], [Seasonally adjusted sales] )`. Above 1 means the month is above the adjusted level. Census’s own factor files are the official factors. This is the ratio of the two published series.

Audit

16. **Suppressed cells** `#,0` (Audit). Count of fact rows with a null `Sales USD`.
17. **Preliminary sales** `$#,0` (Audit). `CALCULATE ( [Sales], 'Fact Retail Sales'[Preliminary] )`.

## Power Query M

```powerquery
let
  Source = Excel.Workbook(Web.Contents("https://www.census.gov/retail/mrts/www/mrtssales92-present.xlsx"), null, true),
  Sheets = Table.SelectRows(Source, each [Kind] = "Sheet" and Text.Length([Name]) = 4),
  PerYear = Table.AddColumn(Sheets, "Rows", each let
    T = Table.Skip([Data], 4),
    Header = Table.PromoteHeaders(Table.FirstN(T, 1), [PromoteAllScalars=true]),
    Body = Table.Skip(T, 1),
    Names = Table.ColumnNames(Header),
    Renamed = Table.RenameColumns(Body, List.Zip({Table.ColumnNames(Body), Names})),
    Tagged = Table.AddColumn(Renamed, "Adjustment", each
      if Text.Contains(Text.Upper(Text.From(Record.Field(_, Names{1}))), "ADJUSTED") then Text.From(Record.Field(_, Names{1})) else null),
    Filled = Table.FillDown(Tagged, {"Adjustment"}),
    DataRows = Table.SelectRows(Filled, each [Adjustment] <> null and Text.Upper(Text.From([Adjustment])) <> Text.Upper(Text.From(Record.Field(_, Names{1})))),
    Unpivot = Table.UnpivotOtherColumns(DataRows, {Names{0}, Names{1}, "Adjustment"}, "Month Label", "Sales Millions"),
    NoCum = Table.SelectRows(Unpivot, each not Text.StartsWith([Month Label], "CY") and not Text.StartsWith([Month Label], "PY")),
    Clean = Table.AddColumn(NoCum, "Suppressed", each Text.Trim(Text.From([Sales Millions])) = "(S)")
  in Clean),
  Expanded = Table.ExpandTableColumn(PerYear, "Rows", {"NAICS  Code", "Kind of Business", "Adjustment", "Month Label", "Sales Millions", "Suppressed"}),
  Adj = Table.TransformColumns(Expanded, {{"Adjustment", each if Text.StartsWith(Text.Upper(_), "NOT") then "Not seasonally adjusted" else "Seasonally adjusted", type text}}),
  Dated = Table.AddColumn(Adj, "Date", each let
    label = Text.Replace(Text.Replace([Month Label], "(p)", ""), "(r)", ""),
    parts = Text.Split(Text.Trim(label), " "),
    mon = Date.Month(Date.FromText("1 " & Text.Replace(parts{0}, ".", "") & " 2000"))
  in #date(Number.From(parts{1}), mon, 1), type date),
  Prel = Table.AddColumn(Dated, "Preliminary", each Text.Contains([Month Label], "(p)"), type logical),
  Dollars = Table.AddColumn(Prel, "Sales USD", each if [Suppressed] then null else Number.From([Sales Millions]) * 1000000, type number),
  Codes = {"441","442","443","444","445","446","447","448","451","452","453","454","722"},
  Flag = Table.AddColumn(Dollars, "Include In Total", each List.Contains(Codes, Text.From([#"NAICS  Code"])), type logical),
  Fact = Table.RenameColumns(Table.SelectColumns(Flag, {"Date","NAICS  Code","Kind of Business","Adjustment","Include In Total","Sales USD","Preliminary"}), {{"NAICS  Code","Kind Code"},{"Kind of Business","Kind Name"}})
in
  Fact
```

If `Excel.Workbook` names the NAICS column `Column1` because row 4 is not the promoted header, take columns by position: column 1 code, column 2 name, columns 3–14 the twelve months. Drop `CY CUM` and `PY CUM` by header text, not by position, because a partial year has fewer month columns (2026 has nine months, then the two cumulative columns).

Kind is `Table.Distinct` of Kind Code, Kind Name, and Include In Total. Parent Code is the code with the last digit removed when that prefix exists in the kind list. Date is `List.Dates(#date(1992,1,1), …, #duration(1,0,0,0))` filtered to month starts, or the distinct fact dates extended through December. Adjustment is the two labels.

## Ten questions

Millions of dollars, as Census prints them. September 2026 is preliminary. “Sales” in questions 1–4 and 8–10 is the published total line, which matches the sum of the thirteen codes.

| # | Question | Expected |
|---|---|---|
| 1 | U.S. retail and food services, not seasonally adjusted, September 2026 | 728,961 million dollars. |
| 2 | Same month, September 2025, and the year-over-year change | 680,630 million. Up 7.101% (7.100921). |
| 3 | Seasonally adjusted total, September 2026 vs September 2025 | 746,637 vs 700,614 million. Up 6.569%. |
| 4 | Not seasonally adjusted total, January through September 2026, vs the same months of 2025 | 6,448,116 vs 6,153,323 million. Up 4.791%. This matches the workbook’s `CY CUM` and `PY CUM` on that line. |
| 5 | Gasoline stations, not seasonally adjusted, September 2026, and their share of the total | 69,135 million. 9.484% of 728,961. |
| 6 | Nonstore retailers, not seasonally adjusted, September 2026 | 119,973 million, 16.458% of the total. Electronic shopping and mail-order houses are 113,238 million, 94.386% of nonstore. |
| 7 | Food services and drinking places, not seasonally adjusted, September 2026 | 91,767 million, 12.589% of the total. |
| 8 | Not seasonally adjusted total, December 2025 vs September 2025 | 780,707 vs 680,630 million. December is 14.704% higher. |
| 9 | Seasonally adjusted gasoline stations, September 2026, as a share of the seasonally adjusted total | 67,581 / 746,637 = 9.051%. |
| 10 | Not seasonally adjusted total, January 1992 | 142,051 million. The thirteen kinds sum to the same figure. |

Do not write a benchmark item that sums every kind, or that turns `(S)` into zero. Do not compare September 2026 in this file with the 17 Nov 2026 advance sentence for October ($748.2 billion). That sentence is the advance survey, and it is seasonally adjusted.
