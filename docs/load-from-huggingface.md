# Loading a model straight from Hugging Face

The public datasets behind these models are on Hugging Face as Parquet files. A model can read them directly, so anyone
can download the model, refresh it, and get the real data, with no lakehouse, gateway or copy step.

## Tested: City Finances, 25 Nov 2026

A copy of `models/city-finances` named "City Finances (HF)" was changed to read
[`jonsandmann/city-finances`](https://huggingface.co/datasets/jonsandmann/city-finances) (`data/city_finances.parquet`,
4,285 rows, 61 cities), deployed to a Fabric workspace on an F2 capacity, and refreshed in the service.

- **Data source:** one `Web` source, the literal file URL. Setting **Anonymous** credentials (privacy level Public)
  through the gateway datasource PATCH worked first time: the credential test follows Hugging Face's 302 redirect from
  `huggingface.co/.../resolve/main/...` to its CDN without trouble. The `RelativePath` form wasn't needed.
- **Refresh:** full refresh **Completed in about 3 s**. 4,285 figure rows, 61 cities, 122 reports.
- **Checks:** `tests/checks.dax` **11 of 11** matched answers computed independently from the same Parquet file with
  duckdb. Zero orphan keys (every figure row has a City, Report, Figure and Fiscal Year End).
- The test model was deleted from the workspace afterwards.

## The M

One shared expression is the model's only connector:

```m
expression FinanceRows =
    let
        Source = Parquet.Document(Web.Contents("https://huggingface.co/datasets/jonsandmann/city-finances/resolve/main/data/city_finances.parquet"))
    in
        Source
```

The lake version of the model reads three Parquet files that `data/prep.py` builds. The Hugging Face file is the
single long table, so the three tables do that prep in M instead.

**Fact Figure** (latest vs prior year, values in whole dollars, report key, hand-checked flag):

```m
let
    Raw = FinanceRows,
    Latest = Table.Group(Raw, {"fips_place"}, {{"latest_year", each List.Max([fiscal_year]), Int64.Type}}),
    Joined = Table.ExpandTableColumn(Table.NestedJoin(Raw, {"fips_place"}, Latest, {"fips_place"}, "L", JoinKind.Inner), "L", {"latest_year"}),
    AddPosition = Table.AddColumn(Joined, "year_position", each if [fiscal_year] = [latest_year] then "Latest" else "Prior", type text),
    AddValue = Table.AddColumn(AddPosition, "value_usd", each Number.Round([value] * 1000000, 0), type number),
    AddReport = Table.AddColumn(AddValue, "report_key", each [fips_place] & "|" & Text.From([fiscal_year]), type text),
    AddChecked = Table.AddColumn(AddReport, "hand_checked", each if [checked] = "pass" then 1 else 0, Int64.Type),
    Raw2 = Table.RenameColumns(AddChecked, {{"fips_place", "city_key"}}),
    Kept = Table.SelectColumns(Raw2, {"row_id", "city_key", "fiscal_year_end", "year_position", "figure_id", "report_key", "source_label", "value_usd", "page", "extraction_method", "hand_checked"}),
    Renamed = Table.RenameColumns(Kept, {{"row_id", "Row ID"}, {"city_key", "City Key"}, {"fiscal_year_end", "Fiscal Year End"}, {"year_position", "Year Position"}, {"figure_id", "Figure ID"}, {"report_key", "Report Key"}, {"source_label", "Source Label"}, {"value_usd", "Value USD"}, {"page", "Page"}, {"extraction_method", "Extraction Method"}, {"hand_checked", "Hand Checked"}}),
    Typed = Table.TransformColumnTypes(Renamed, {{"Row ID", type text}, {"City Key", type text}, {"Fiscal Year End", type date}, {"Year Position", type text}, {"Figure ID", type text}, {"Report Key", type text}, {"Source Label", type text}, {"Value USD", Currency.Type}, {"Page", Int64.Type}, {"Extraction Method", type text}, {"Hand Checked", Int64.Type}})
in
    Typed
```

**Report** (one PDF per city and fiscal year):

```m
let
    Grouped = Table.Group(FinanceRows, {"fips_place", "fiscal_year"}, {{"fiscal_year_end", each List.First([fiscal_year_end]), type text}, {"source_pdf_url", each List.First([source_pdf_url]), type text}}),
    AddKey = Table.AddColumn(Grouped, "report_key", each [fips_place] & "|" & Text.From([fiscal_year]), type text),
    Raw = Table.SelectColumns(AddKey, {"report_key", "fiscal_year_end", "source_pdf_url"}),
    Renamed = Table.RenameColumns(Raw, {{"report_key", "Report Key"}, {"fiscal_year_end", "Report Fiscal Year End"}, {"source_pdf_url", "Source PDF"}}),
    Typed = Table.TransformColumnTypes(Renamed, {{"Report Key", type text}, {"Report Fiscal Year End", type date}, {"Source PDF", type text}})
in
    Typed
```

**City** (one row per city in the file):

```m
let
    Grouped = Table.Group(FinanceRows, {"fips_place"}, {{"city", each List.First([city]) & ", " & List.First([state]), type text}, {"state", each List.First([state]), type text}, {"population", each List.First([population]), Int64.Type}, {"table_sums_ok", each List.AllTrue([table_sums_ok]), type logical}}),
    AddGroup = Table.AddColumn(Grouped, "city_group", each if [population] >= 402000 then "Top 50 US city" else if [state] = "WA" and [population] < 300000 then "Washington near Bellevue" else "Next 20 US city", type text),
    AddInData = Table.AddColumn(AddGroup, "in_data", each true, type logical),
    Raw = Table.RenameColumns(AddInData, {{"fips_place", "city_key"}}),
    Renamed = Table.RenameColumns(Raw, {{"city_key", "City Key"}, {"city", "City"}, {"state", "State"}, {"population", "Population"}, {"city_group", "City Group"}, {"in_data", "In Data"}, {"table_sums_ok", "Table Sums OK"}}),
    Typed = Table.TransformColumnTypes(Renamed, {{"City Key", type text}, {"City", type text}, {"State", type text}, {"Population", Int64.Type}, {"City Group", type text}, {"In Data", type logical}, {"Table Sums OK", type logical}})
in
    Typed
```

In the model, drop the `FinancesFolder` parameter and the `FinanceFiles` query, and add `FinanceRows` in their place
(also in `PBI_QueryOrder` and the `ref expression` lines in `model.tmdl`). Nothing else changes: the Figure, Year
Position and Fiscal Year End tables, the relationships and every measure are the same.

### What differs from the lake version

- **City has only the cities in the file** (61), so `In Data` is always true. The lake version also lists the cities
  that were attempted but couldn't be read; the dataset card names them.
- **City Group is derived from population**, because the file has no group column: 402,000 or more (Census Vintage
  2024) is a Top 50 US city, a Washington city under 300,000 is near Bellevue, the rest are the next 20. That gives 45,
  10 and 6 cities. The cut-offs fit the Vintage 2024 figures in this release; check them if a release changes
  population vintage.

### Checks on the Hugging Face release

The answers moved from the lake version's because the Hugging Face release has 61 cities, not 54. Seattle, San
Francisco, Los Angeles, Phoenix (checks 2, 4, 5, 7, 8) are unchanged. The totals across cities moved:

| check | Hugging Face release |
|---|---|
| 1 | 4,285 rows, 61 cities, 26 hand-checked, 50 cities with sums OK |
| 3 | $192.4B expenses on the latest reports, 61 cities, $4,411 per resident |
| 6 | 34 cities with negative unrestricted net position; lowest Dallas, -$4.89B |
| 9 | $39.05B net pension liability, 22 cities, $2,403 per resident |
| 10 | 6 Washington cities near Bellevue, property tax 6.65% of revenues |
| 11 | revenue growth +3.70%, expense growth +2.89% over the cities with both years |

## Doing the same for another model

- Point `Web.Contents` at the file's `resolve/main/...` URL on huggingface.co; don't use the CDN URL it redirects to,
  which is signed and expires.
- Set the Web source's credentials to Anonymous, privacy level Public. In Power BI Desktop this is the prompt on first
  refresh; in the service, the dataset's data source settings.
- If the file is the one long table, rebuild the dimension tables in M with `Table.Group`, as above.
