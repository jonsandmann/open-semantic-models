# Restaurant Inspections (10 jurisdictions)

A semantic model of restaurant health inspections from ten jurisdictions, joined into one schema by our own data
factory: New York City, Chicago, King County WA (Seattle), Austin, Montgomery County MD, Delaware, Marin County CA,
New York State (outside NYC), Boston and Toronto. 582,036 inspections, 1,181,038 violations, 147,443 establishments,
January 2023 to November 2026. It is the first model in the library on data we built ourselves rather than a
publisher's file, and the one where the semantic layer matters most: each city's "fail" is a different event, so the
model is built to compare **findings**, not **verdicts**.

## Source

- **Data:** the data factory's joined tables, `data-factory/inspections/data/{establishments,inspections,violations}.parquet`
  (24 MB, zstd Parquet), built on 24 Nov 2026 by `scripts/fetch.py` and `scripts/transform.py` from the ten open
  datasets listed in the factory's `SOURCES.md`. Schema in `schema.md`, the 15-category violation crosswalk in
  `CROSSWALK.md`, the cross-city findings and their red team in `FINDINGS.md`.
- **Licences of the inputs** (verified 24 Nov 2026): public domain (King County, Austin, Montgomery, Delaware;
  Boston PDDL), NYC Open Data terms, City of Chicago Data Terms of Use, OPEN-NY Terms of Use, **Open Government
  Licence - Toronto** (attribution required) and **ODbL** for Marin County (attribution; a published derived database
  must be shared under ODbL). The model's `Attribution` measure and model annotation carry the required lines; put
  them on any report built from it.
- **Not at a public URL.** The model reads the three Parquet files from a folder named by the `InspectionsFolder`
  parameter (below). For the service test they were copied to the `InspectionsData` lakehouse in the Semantic Models
  Lab workspace (`Files/inspections/`) with `fab cp`.

### What the data can and can't say (from the factory's red team)

- **Published fail rates are not comparable.** With 3+ critical findings, Boston, King County and Chicago call it a
  fail; Toronto calls 81% a Conditional Pass and closes 2.7%; NYC gives no grade and closes 5.2%. Boston's 40% and
  Toronto's 0.1% compare rulebooks, not kitchens. The model's comparable measures hold the findings constant:
  **Critical violations per inspection**, **Re-inspection rate at 3+ criticals** and **Closure rate at 3+
  criticals**. `Published outcome` exists for use within one jurisdiction, and its description says so.
- **Critical means different things.** Toronto's critical adds Significant to Crucial; Boston's adds priority
  foundation; Chicago's is FDA items 1-29; NYC's flag is the narrowest. Delaware and Montgomery publish none, so it is
  derived from the category. `Jurisdiction[Critical Means]` says which.
- **Boston and Toronto publish no inspection type**, so their follow-ups sit inside Routine. `Visit Kind` (first visit
  or within 60 days of an earlier visit) separates them: Boston's published outcome is 40.0% on all routine visits and
  61.1% on first visits.
- **In Boston's published file every listed violation comes with a fail** (passing visits' violations are not
  published), so "Boston fails anything it finds" can't be told apart from "Boston lists violations only when it
  fails".
- **Austin publishes a score only.** It counts in `Inspections` and `Average burden score` (its native 100-point score)
  and is left out of every per-inspection violation measure (`Inspections with violation data` is the denominator).
- **A zero in a category can mean the form has no item for it** (Montgomery's 16-item form; no garbage item in NYC or
  New York State).
- **Windows differ:** Austin and Toronto from November 2023, Montgomery from June 2024, Delaware from November 2024
  (`Jurisdiction[Data From]`). Delaware publishes two inspections dated 4 December 2026, kept as published.
- 93 inspections (91 Montgomery, 2 Chicago) have no establishment id; they point to a `<jurisdiction>:(unknown)` row.

## Grain and size

| Fact | Grain | Rows |
|---|---|---|
| Fact Inspection | one inspection | 582,036 (routine 461,028) |
| Fact Violation | one violation cited at one inspection | 1,181,038 (363,455 critical) |

Two grains, related by Inspection Key: `Fact Violation` many-to-one `Fact Inspection`. Inspection counts come from
`Fact Inspection` rows and violation counts from `Fact Violation` rows, and every per-inspection rate divides a
violation count by an inspection count, so nothing is counted once per violation that should be counted once per
inspection. "Inspections citing" a category is a distinct count of the violation fact's Inspection Key.

## Star schema

```
Date (1 day)           1 --* Fact Inspection *-- 1  Establishment (chain flag)
Jurisdiction (rulebook) 1 --*        |         *-- 1  Outcome (tier, closed)
Inspection Type        1 --*         |         *-- 1  Critical Band (0, 1, 2, 3+)
Visit Kind             1 --*         |
                                     1
                                     *
Violation Category (15) 1 --* Fact Violation *-- 1  Critical Flag
                                             *-- 1  Violation Code
```

Every relationship is many-to-one, single direction. Date, establishment, jurisdiction and type filters reach
violations through their inspection; category and critical filters stay on violations. **One date:** the inspection
date. Violations have no date of their own and establishments none, so there is no role-playing date table (the CMS
lesson does not arise); if a later version adds, say, a correction date, it gets its own marked date table.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Inspection | 582,036 | Inspection Key | measures only |
| Fact Violation | 1,181,038 | none | measures only |
| Establishment | 147,445 | Establishment Key | Publisher Id, Name, Name Normalized, Address, City, State, Zip, Latitude, Longitude, Facility Type, Cuisine (NYC), Chain, Is Chain, Chain or Independent |
| Jurisdiction | 10 | Jurisdiction Key | Jurisdiction, Country, Publisher, Scoring System, **Fail Means**, **Critical Means**, Publishes Violations, Publishes Verdict, Data From, Licence |
| Outcome | 64 | jurisdiction, result, tier | Published Result, Tier, Tier Name, Closed |
| Inspection Type | 5 | type code | Inspection Type (Routine, Re-inspection, Complaint, Pre-opening, Other) |
| Critical Band | 4 | 0-3 | Critical Band (No critical, 1, 2, 3+) |
| Visit Kind | 2 | 1-2 | First visit, Follow-up within 60 days |
| Violation Category | 15 | category code | Category, Covers, FDA Risk Factor |
| Critical Flag | 2 | Critical / Not critical | Critical Flag |
| Violation Code | 1,051 | jurisdiction and code | Code Jurisdiction, Code, Code Description (first published, 300 characters) |
| Date | 1,461 (2023-2026) | Date | Year, Quarter, Month, Year Month, Month Start, Season |

The chain flag matches the 18 chains of FINDINGS.md Q3 on the start of the normalized name (9,650 establishments).
The outcome tier and closure rule, and each jurisdiction's rulebook text, come from the factory's schema.md and the
red team (closures: NYC closed or re-closed by DOHMH; Boston HE_Closure, HE_VolClos, HE_TSOP; Toronto and Montgomery
Closed; Marin red placard).

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `InspectionsFolder` | `https://onelake.dfs.fabric.microsoft.com/<Semantic Models Lab id>/<InspectionsData lakehouse id>/Files/inspections` | The folder holding the three Parquet files |
| `InspectionFiles` | shared, not loaded | `AzureStorage.DataLake ( InspectionsFolder )`: Name and Content of each file. The only connector in the model |
| `Calendar` | shared, not loaded | 2023-01-01 to 2026-12-31 for the Date table |

**Pointing it at your own copy.** Copy the three files from the data factory's `data/` folder to any ADLS Gen2 or
OneLake folder and set `InspectionsFolder` to its URL; the service asks for an organizational (OAuth) sign-in on that
source. For a folder on disk in Power BI Desktop, change the one line in `InspectionFiles` to
`Files = Folder.Files ( InspectionsFolder )` and set the parameter to the local path (both connectors return Name and
Content). One connector per model on purpose: the service can't refresh a query that switches between a cloud folder
and a local one.

No incremental refresh: the factory rebuilds the whole snapshot; a full refresh reads 24 MB of Parquet.

## Measures (31)

| Folder | Measures |
|---|---|
| Inspections | Inspections, Inspections with violation data, Establishments inspected, Inspections per establishment, Follow-up share |
| Findings | Violations, Critical violations, Critical share of violations, **Critical violations per inspection**, Violations per inspection, Inspections citing, Share of inspections citing, Share with no violation, Average burden score, Inspections with 3+ criticals, Share with 3+ criticals |
| Outcomes | Inspections with a verdict, **Re-inspection rate at 3+ criticals**, **Closure rate at 3+ criticals**, Closures, Closure rate, Published outcome (not comparable across jurisdictions) |
| Chains | Chain critical per inspection, Independent critical per inspection, Chain ratio (one jurisdiction at a time) |
| Time | Inspections prior year, Inspections YoY %, Critical per inspection prior year, Critical per inspection change, Last inspection date (hidden) |
| About | Attribution |

## Ten business questions (acceptance checks)

"Window" is the factory's findings base: routine inspections, 2024-01-01 to 2026-10-31. Expected answers were
computed first from the Parquet files with duckdb (`tests/expected.py`, independent of the factory's
`findings.py`); `tests/checks.dax` asks each one of the deployed model.

| # | Question | Expected (duckdb) | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | How much is loaded? | 582,036 inspections; 1,181,038 violations, 363,455 critical; 143,368 establishment ids inspected | identical; 143,370 establishments inspected (the 2 `(unknown)` placeholders); `SUM ( Critical Count )` = 363,455, so the two facts agree | Pass |
| 2 | Critical violations per inspection, window | NYC 1.87, Delaware 2.35, Boston 0.72, Chicago 0.64, King County 0.48, Marin 0.54, Montgomery 0.41, NYS 0.34, Toronto 0.33; Austin none | identical to 4 places; Austin blank | Pass |
| 3 | With 3+ criticals, how often is a re-inspection ordered or worse? | Toronto 81.4%, NYC 99.6%, Marin 85.0%, Boston, Chicago, King County, Montgomery 100%; Delaware, NYS no verdict | identical; Delaware and NYS blank | Pass |
| 4 | With 3+ criticals, how often is the place closed? | Marin 6.3%, NYC 5.2%, Boston 4.1%, Toronto 2.7%, Montgomery 1.7%, Chicago and King County 0% | identical (0%, not blank, after the fix below) | Pass |
| 5 | Published outcome (not comparable), window | Boston 40.0%, King County 30.7%, Chicago 22.7%, NYC 19.2%, Montgomery 3.8%, Marin 1.6%, Austin 0.4%, Toronto 0.1% | identical | Pass |
| 6 | Boston on first visits only | 61.1% (40.0% with follow-ups); 12,911 of 31,787 routine visits are follow-ups (40.6%) | identical | Pass |
| 7 | Share of inspections citing pests / temperature, window | pests NYC 31.8%, King County 3.6%, Marin 2.7%; temperature NYC 43.0%, Toronto 4.3% | identical for all nine | Pass |
| 8 | Chains vs everyone else, critical per inspection | NYC 1.09 vs 1.96 (0.56), Toronto 0.12 vs 0.35 (0.34), King County 0.41 vs 0.48 (0.86), Montgomery 0.33 vs 0.42 | identical; Chain ratio blank across jurisdictions | Pass |
| 9 | Average burden score, window | Delaware 80.6, NYC 83.9, Chicago 90.2, Austin 91.2 (native), Boston 92.9, NYS 93.3, King County 95.6, Marin 95.9, Toronto 96.5, Montgomery 96.7 | identical | Pass |
| 10 | Temperature citations, summer vs winter | Boston 14.0% vs 10.1% (1.39), Chicago 17.4 vs 13.8, Toronto 5.0 vs 3.9, NYS 23.4 vs 25.1 (no summer rise) | identical for all nine | Pass |

Also checked: NYC routine critical per inspection 2025 1.8489 against 1.8388 in 2024 (prior year), 13,139 vs 12,878
inspections; the 15 categories' violation and critical counts match the Parquet exactly; zero orphan keys on all
eleven relationships; 64 outcomes, 1,051 codes, 9,650 chain establishments; all 31 measures evaluate with no filter.
Every answer in questions 2-10 also reproduces the factory's FINDINGS.md and its red team (Boston 61.1% on first
visits, Toronto 81.4% / 2.7%, NYC 99.6% / 5.2%).

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/restaurant-inspections/RestaurantInspections.SemanticModel/definition`):
deserializes (12 tables, 85 columns, 31 measures, 11 relationships, 3 expressions), `Model.Validate()` has no errors,
round-trips, and all 30 rules pass except two deliberate warnings:

| Rule | Status |
|---|---|
| Descriptions on every table, column, measure and expression | Pass |
| Format strings; `%` formats on percentages; visible measures in display folders | Pass |
| `summarizeBy: none` on numeric columns; implicit measures discouraged | Pass |
| Foreign keys hidden; keys `isKey`; month, season, tier and band labels sorted | Pass |
| One marked date table; auto date/time off | Pass |
| Many-to-one, single-direction relationships on matching types; no islands | Pass |
| Fixed decimal (no floating point); fact columns hidden | Pass |
| DIVIDE, no IFERROR, column/measure reference style, every reference resolves | Pass |
| PRF3 incremental refresh on the facts | **Warn, deliberate**: the factory rebuilds one 24 MB snapshot |
| PRF4 `isAvailableInMdx` off on `Fact Inspection[Inspection Key]` | **Warn, deliberate**: it is the key Fact Violation relates to |

**In a Fabric workspace (24 Nov 2026, F2):** the three Parquet files copied to the new `InspectionsData` lakehouse in
Semantic Models Lab; deployed with `fab import`; OAuth2 credentials (an Entra token for `https://storage.azure.com/`)
set on the one AzureDataLakeStorage source through the gateway API; full refresh **Completed in 2 min 52 s**. The
first check run found one thing TmdlCheck could not: the rates returned blank, not 0%, where nothing qualified
(Chicago's closure rate at 3+ criticals). Every rate's numerator is now `COALESCE`d to 0 inside `DIVIDE`; redeployed,
refreshed (2 min 43 s), **10/10**. Details in the [run log](../../docs/toolchain.md#run-log).

**Credentials note:** an OAuth2 access token set through the API lasts about an hour. A scheduled refresh needs the
source's credentials set once in the service UI (organizational account) or a service principal with access to the
lakehouse.
