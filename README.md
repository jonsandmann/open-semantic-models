# Semantic models

Production-quality Power BI / Fabric semantic models built on public, openly licensed data, authored as
PBIP semantic models in TMDL so every change is a readable diff.

No data is committed: each model's README names its source and how to download it. Restaurant Inspections and
Building Permits sit on joins of ten city datasets each, built by a separate data pipeline (not yet published); their
READMEs describe the joined schema and each input's licence.

Each model lives in `models/<name>/` with:

- `<Name>.SemanticModel/`: the PBIP semantic model (`definition.pbism`, `.platform`, `definition/*.tmdl`).
  Open it in Power BI Desktop through a PBIP project, or deploy it to a Fabric workspace with the Fabric CLI.
- `README.md`: source, licence, grain, star schema, measures and the best-practice checklist.
- `tests/`: DAX queries that check the deployed model.

| Model | Source | Licence | Grain | Size |
|---|---|---|---|---|
| [NYC Taxi Trips](models/nyc-taxi/README.md) | NYC TLC yellow taxi trip records | NYC Open Data Terms of Use | One row per trip | ~3.5M trips a month |
| [EIA Electricity Retail Sales](models/eia-electricity/README.md) | EIA Form EIA-861M monthly sales and revenue | Public domain (US government) | State x month x sector | ~41K rows (2010 onward) |
| [CMS Hospital Quality](models/cms-hospital-quality/README.md) | CMS Care Compare: Hospital General Information, Complications and Deaths | Public domain (US government) | Hospital x measure x window; hospital x release | ~96K results, ~5.4K hospitals |
| [Census Monthly Retail Trade](models/census-retail/README.md) | Census Bureau Monthly Retail Trade Survey (mrtssales92-present.xlsx) | Public domain (US government) | Kind of business x month x adjustment | ~43K rows (1992 onward), 64 kind lines |
| [HM Land Registry Price Paid](models/price-paid/README.md) | HM Land Registry Price Paid Data, monthly update file (no address fields loaded) | Open Government Licence v3.0, attribution required | One row per transaction | ~98K rows a monthly file |
| [NOAA Storm Events](models/noaa-storm-events/README.md) | NOAA NCEI Storm Events Database, bulk CSV (details and fatalities, latest vintage per year) | Public domain (US government) | One row per event; one row per fatality | ~70K events a year (2024-2025 loaded) |
| [NASA FIRMS Active Fires](models/nasa-firms/README.md) | NASA LANCE FIRMS country yearly active-fire CSVs (VIIRS NOAA-20, VIIRS S-NPP, MODIS) | NASA open data (CC0), citation and disclaimer requested | One row per detection (pixel x overpass x product) | ~60K rows (Portugal 2024-2025) |
| [Restaurant Inspections](models/restaurant-inspections/README.md) | Our data factory's join of ten open restaurant-inspection datasets (NYC, Chicago, King County, Austin, Montgomery MD, Delaware, Marin, NY State, Boston, Toronto), 15-category violation crosswalk | Inputs public domain or open; Toronto OGL and Marin ODbL attribution required | One row per inspection; one row per violation | 582K inspections, 1.18M violations (2023-2026) |
| [Building Permits](models/building-permits/README.md) | Our data factory's join of ten open building-permit datasets (Seattle, NYC, Chicago, SF, LA, Austin, Boston, Philadelphia, New Orleans, Montgomery County MD), 14-category work crosswalk | Inputs public domain or open; NYC, Chicago, Philadelphia and LA terms as published | One row per permit | 1.52M permits (2023-2026) |
| [City Council Votes](models/councils/README.md) | Our data factory's pull of eight councils' Legistar public Web API (Seattle, Bellevue, Oakland, Boston, Madison, Denver, Phoenix, San José), full council only | Public meeting records (no separate API licence) | One row per meeting; per agenda item; per member vote | 295 meetings, 16K items, 24.5K vote rows (Nov 2025-Nov 2026) |
| [City Spending](models/spending/README.md) | Our data factory's join of nine city checkbooks (Chicago, Los Angeles, San Francisco, Austin, Dallas, Kansas City, Cincinnati, Atlanta, Boston), function crosswalk and normalized vendor key | Each city's open data terms; Census population public domain | One row per payment line | 4.05M lines, $105.2B (latest two fiscal years) |
| [City Finances (ACFR)](models/city-finances/README.md) | Our data factory's read of 54 cities' audited ACFRs (50 largest US cities plus ten Washington cities), every figure citing its PDF page | Public records; Census population public domain | City x fiscal year x figure | 3,717 figures (FY2024-FY2025, prior years from 2023) |

The first nine models also have an [Apache Ossie](https://github.com/apache/ossie) twin in `models/<name>/ossie/`, with a verdict for each measure: 103 of their 237 measures port to Ossie SQL. See [ossie/README.md](ossie/README.md).

## Validating a model

Every model must load in the Tabular Object Model (TOM) and pass the rule checks before it is committed:

```sh
export DOTNET_ROOT=/opt/homebrew/opt/dotnet/libexec   # macOS with Homebrew .NET
dotnet run --project tools/TmdlCheck -- models/nyc-taxi/NycTaxi.SemanticModel/definition
```

`tools/TmdlCheck` deserializes the TMDL folder with `TmdlSerializer`, runs `Model.Validate()`, round-trips the model,
and checks it against Best Practice Analyzer style rules. It runs anywhere .NET runs; no Windows, no Power BI Desktop.
What it can and can't prove, and how to deploy and test in a Fabric workspace, is in [docs/toolchain.md](docs/toolchain.md).

## Licence

The code and model definitions in this repo are MIT licensed (see `LICENSE`). The data belongs to its publishers and
stays under their terms, listed per model; attribution is required for HM Land Registry (OGL v3.0), Toronto (OGL
Toronto) and Marin County (ODbL), among others.
