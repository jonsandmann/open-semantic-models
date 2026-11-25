# EIA state electricity retail sales

Model #2. Public domain (U.S. government work). Source file downloaded 24 Nov 2026 and every answer below was summed from that file. No API key.

## Source

| Item | Value |
|---|---|
| Page | https://www.eia.gov/electricity/data/eia861m/ |
| File | https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx |
| Bulk API | Not used. `api.eia.gov` needs a free key. This xlsx does not. |
| Size | 2,280,162 bytes (`Content-Length` and the file on disk). Under 50 MB, so it is not gitignored. |
| Saved as | `samples/eia-sales-revenue.xlsx` (download from the source; not committed) |
| Last-Modified | Fri, 23 Oct 2026 17:10:42 GMT |
| Sheet used | `Monthly-States` only. `Monthly-Ter`, `State-YTD-*`, and `US-YTD` are aggregates. Do not load them or totals double-count. |
| Layout | Rows 1–2 are sector and metric banners. Row 3 is the header. Data starts at row 4. A notes row sits at the bottom (year is not a number). Drop it. |
| Span in this file | January 2010 through August 2026. 200 year-months. 51 areas: 50 states plus DC. No Puerto Rico in this sheet. August 2026 is `Data Status = Preliminary`. |
| Source units | Revenue in thousand dollars, sales in megawatthours, customers as a count, price in cents/kWh. Price is revenue ÷ sales and is not stored. |

Columns on `Monthly-States`, repeating Revenue, Sales, Customers, Price:

| Cols | Sector |
|---|---|
| A–D | Year, Month, State, Data Status |
| E–H | Residential |
| I–L | Commercial |
| M–P | Industrial |
| Q–T | Transportation |
| U–X | Total. **Do not load.** It is the sum of the four sectors. |

## Grain

One fact row per **state (or DC) × month × sector**, four sectors, Total excluded. 40,800 rows in this file (51 × 200 × 4).

## Star schema

### Fact Retail Sales

| Column | Type | Key | Notes |
|---|---|---|---|
| Date | date | FK to Date[Date] | First of the month |
| State Code | text | FK to State[State Code] | |
| Sector | text | FK to Sector[Sector] | |
| Data Status | text | | Preliminary or Final, as published |
| Revenue USD | decimal | | thousand dollars × 1,000 |
| Sales kWh | decimal | | megawatthours × 1,000 |
| Customers | int64 | | count. Do not sum across months (the same account repeats). |

### Date (marked date table)

`Date`, `Year`, `Month Number`, `Month`, `Year Month` (`YYYY-MM`), `Year Month Sort` (year × 100 + month). One row per month, 2010-01-01 through the latest month in the file, extended to December of that year so time intelligence has a frame. Mark as the date table on `Date`. Auto date/time off.

### State

`State Code` (key), `State Name`, `Census Region` (Northeast, Midwest, South, West), `Census Division`. DC is South / South Atlantic. Static list in M, not from EIA.

### Sector

`Sector` (key), `Sector Sort` (1 Residential, 2 Commercial, 3 Industrial, 4 Transportation).

### Relationships

| From | To | Cardinality | Filter |
|---|---|---|---|
| Fact[Date] | Date[Date] | many to one | single, Date filters Fact |
| Fact[State Code] | State[State Code] | many to one | single |
| Fact[Sector] | Sector[Sector] | many to one | single |

## Measures

Display folder in parentheses. Format after the name. Descriptions are the business meaning.

Base

1. **Revenue** `$#,0` (Sales). `SUM ( 'Fact Retail Sales'[Revenue USD] )`. Dollars utilities billed retail customers.
2. **Sales kWh** `#,0` (Sales). `SUM ( 'Fact Retail Sales'[Sales kWh] )`. Retail kilowatthours sold.
3. **Sales MWh** `#,0.0` (Sales). `DIVIDE ( [Sales kWh], 1000 )`. Same sales in the unit EIA publishes.
4. **Customers** `#,0` (Sales). `SUM ( 'Fact Retail Sales'[Customers] )`. Meaningful for one month. Summing months double-counts accounts.
5. **Price cents per kWh** `0.00` (Price). `DIVIDE ( [Revenue], [Sales kWh] ) * 100`. Recomputed. EIA's published cents column is this ratio.

Ratios and mix

6. **Revenue per customer** `$#,0.00` (Price). `DIVIDE ( [Revenue], [Customers] )`. One month only.
7. **kWh per customer** `#,0.0` (Price). `DIVIDE ( [Sales kWh], [Customers] )`.
8. **Share of US sales** `0.0%` (Mix). `DIVIDE ( [Sales kWh], CALCULATE ( [Sales kWh], ALL ( State ) ) )`. Sector and date filters stay.
9. **Share of state sales** `0.0%` (Mix). `DIVIDE ( [Sales kWh], CALCULATE ( [Sales kWh], ALL ( Sector ) ) )`.

Time

10. **Sales YTD kWh** `#,0` (Time). `TOTALYTD ( [Sales kWh], 'Date'[Date] )`. Calendar year, January through the selected month.
11. **Revenue YTD** `$#,0` (Time). `TOTALYTD ( [Revenue], 'Date'[Date] )`.
12. **Sales prior year kWh** `#,0` (Time). `CALCULATE ( [Sales kWh], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
13. **Revenue prior year** `$#,0` (Time). `CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
14. **Price prior year cents per kWh** `0.00` (Time). `CALCULATE ( [Price cents per kWh], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
15. **Sales YoY %** `+0.0%;-0.0%;0.0%` (Time). `DIVIDE ( [Sales kWh] - [Sales prior year kWh], [Sales prior year kWh] )`.
16. **Revenue YoY %** `+0.0%;-0.0%;0.0%` (Time). `DIVIDE ( [Revenue] - [Revenue prior year], [Revenue prior year] )`.
17. **Price YoY cents** `+0.00;-0.00;0.00` (Time). `[Price cents per kWh] - [Price prior year cents per kWh]`.

Latest month (the file is not "today")

18. **Sales latest month kWh** `#,0` (Time). `CALCULATE ( [Sales kWh], 'Date'[Date] = MAX ( 'Date'[Date] ) )`.
19. **Months in scope** `0` (Audit). `DISTINCTCOUNT ( 'Fact Retail Sales'[Date] )`.

## Power Query M

Anonymous GET. Unpivot the four sectors. Drop Total and the notes row.

```powerquery
let
  Source = Excel.Workbook(Web.Contents("https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"), null, true),
  Sheet = Source{[Item="Monthly-States", Kind="Sheet"]}[Data],
  // Row 1 sector banner, row 2 metric banner, row 3 units. Data is row 4 onward.
  Body = Table.Skip(Sheet, 3),
  Named = Table.RenameColumns(Body, {
    {"Column1","Year"}, {"Column2","Month"}, {"Column3","State Code"}, {"Column4","Data Status"},
    {"Column5","Res Revenue"}, {"Column6","Res Sales"}, {"Column7","Res Customers"},
    {"Column9","Com Revenue"}, {"Column10","Com Sales"}, {"Column11","Com Customers"},
    {"Column13","Ind Revenue"}, {"Column14","Ind Sales"}, {"Column15","Ind Customers"},
    {"Column17","Tra Revenue"}, {"Column18","Tra Sales"}, {"Column19","Tra Customers"}
  }),
  Keep = Table.SelectColumns(Named, {
    "Year","Month","State Code","Data Status",
    "Res Revenue","Res Sales","Res Customers",
    "Com Revenue","Com Sales","Com Customers",
    "Ind Revenue","Ind Sales","Ind Customers",
    "Tra Revenue","Tra Sales","Tra Customers"}),
  Years = Table.SelectRows(Keep, each Value.Is(Value.FromText(Text.From([Year])), type number) or Value.Is([Year], type number)),
  Res = Table.RenameColumns(Table.SelectColumns(Years, {"Year","Month","State Code","Data Status","Res Revenue","Res Sales","Res Customers"}), {{"Res Revenue","Revenue Thousand"},{"Res Sales","Sales MWh"},{"Res Customers","Customers"}}),
  ResS = Table.AddColumn(Res, "Sector", each "Residential"),
  Com = Table.AddColumn(Table.RenameColumns(Table.SelectColumns(Years, {"Year","Month","State Code","Data Status","Com Revenue","Com Sales","Com Customers"}), {{"Com Revenue","Revenue Thousand"},{"Com Sales","Sales MWh"},{"Com Customers","Customers"}}), "Sector", each "Commercial"),
  Ind = Table.AddColumn(Table.RenameColumns(Table.SelectColumns(Years, {"Year","Month","State Code","Data Status","Ind Revenue","Ind Sales","Ind Customers"}), {{"Ind Revenue","Revenue Thousand"},{"Ind Sales","Sales MWh"},{"Ind Customers","Customers"}}), "Sector", each "Industrial"),
  Tra = Table.AddColumn(Table.RenameColumns(Table.SelectColumns(Years, {"Year","Month","State Code","Data Status","Tra Revenue","Tra Sales","Tra Customers"}), {{"Tra Revenue","Revenue Thousand"},{"Tra Sales","Sales MWh"},{"Tra Customers","Customers"}}), "Sector", each "Transportation"),
  Stacked = Table.Combine({ResS, Com, Ind, Tra}),
  Typed = Table.TransformColumnTypes(Stacked, {{"Year", Int64.Type},{"Month", Int64.Type},{"Revenue Thousand", type number},{"Sales MWh", type number},{"Customers", Int64.Type}}),
  Dated = Table.AddColumn(Typed, "Date", each #date([Year], [Month], 1), type date),
  Units = Table.AddColumn(Table.AddColumn(Dated, "Revenue USD", each [Revenue Thousand] * 1000, type number), "Sales kWh", each [Sales MWh] * 1000, type number),
  Fact = Table.SelectColumns(Units, {"Date","State Code","Sector","Data Status","Revenue USD","Sales kWh","Customers"})
in
  Fact
```

`Column8`, `Column12`, `Column16`, `Column20` are the published cents prices and are skipped. Columns 21–24 are Total and are skipped. If `Excel.Workbook` names columns from row 1 instead of `ColumnN`, promote nothing and pick fields by position (`Table.Column` index), not by the banner text. Residential revenue is column 5.

Date, from the fact:

```powerquery
let
  Dates = List.Distinct(Fact[Date]),
  T = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),
  Add = Table.AddColumn(Table.AddColumn(Table.AddColumn(T, "Year", each Date.Year([Date]), Int64.Type), "Month Number", each Date.Month([Date]), Int64.Type), "Month", each Date.MonthName([Date]), type text),
  Sort = Table.AddColumn(Add, "Year Month Sort", each [Year] * 100 + [Month Number], Int64.Type),
  Label = Table.AddColumn(Sort, "Year Month", each Text.From([Year]) & "-" & Text.PadStart(Text.From([Month Number]), 2, "0"), type text)
in
  Label
```

State is a 51-row entered table (`State Code`, `State Name`, `Census Region`, `Census Division`). Sector is four entered rows with `Sector Sort`.

## Ten questions

Computed from `Monthly-States` with Total excluded. August 2026 is preliminary. Price is `sum(revenue thousand dollars) / sum(sales MWh) × 100`, not the average of the published price column. "US" is the 50 states plus DC.

| # | Question | Expected |
|---|---|---|
| 1 | California residential sales, August 2026 | 11,160,409 MWh (11,160,409,000 kWh). Revenue $3,320,537,900. Customers 14,138,808. Price 29.75 cents/kWh (29.7528 unrounded). |
| 2 | US residential revenue, August 2026 | $30,455,229,710 (30,455,229.71 thousand dollars). |
| 3 | Washington commercial price, August 2026 | 11.81 cents/kWh (11.8144). Sales 2,955,812.7 MWh. Revenue $349,212,000. Customers 408,477. |
| 4 | California all-sector sales, August 2026 vs August 2025 | 26,720,654.69 MWh vs 24,383,435.14 MWh. YoY +9.585%. |
| 5 | Texas share of US industrial sales, August 2026 | 14,869,625 / 93,707,250.26 MWh = 15.868%. |
| 6 | California residential sales, year to date through August 2026 | 58,930,561.1 MWh. |
| 7 | Highest state residential price, August 2026 | Hawaii, 47.18 cents/kWh (47.1833), on 257,565.21 MWh. |
| 8 | US commercial customers, August 2026 | 19,658,797. |
| 9 | US transportation sales, August 2026 | 603,959.78 MWh. |
| 10 | Alaska all-sector price, August 2026 | 25.32 cents/kWh (25.3196). Revenue $124,600,400. Sales 492,109.63 MWh. Customers 365,040. |

Query-benchmark items should pin the month (the file grows) and accept price rounded to 0.01 cents. Customer counts are a snapshot, so a question that sums customers across months is a bad item.
