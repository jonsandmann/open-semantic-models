# Building Permits (10 US jurisdictions)

A semantic model of building permits from ten jurisdictions, joined into one schema by our own data factory:
Seattle, New York City, Chicago, San Francisco, Los Angeles, Austin, Boston, Philadelphia, New Orleans and
Montgomery County MD. 1,519,874 permits, applied or issued 2023-01-01 to 2026-11-23. Headline counts follow
**issue date** (Census Building Permits Survey convention). Housing units de-duplicate Austin related permits
and include Los Angeles mixed-use apartments that the crosswalk filed as commercial.

## Source

- **Data:** `data-factory/permits/data/clean/permits.parquet` (63 MB, zstd), built 24 Nov 2026 by
  `scripts/fetch.py` and `scripts/normalize.py`. Schema in `schema.md`, findings and red team in `FINDINGS.md`.
  The lakehouse file is a slim 15 MB copy with `Housing Units Contribution` already applied (Austin master-permit
  de-dupe from raw `masterpermitnum`, Los Angeles mixed-use apartments included). Dates outside 2022–2026 are blanked.
- **Licences of the inputs:** public domain or PDDL (Seattle, Austin, Boston, New Orleans, Montgomery, SF);
  NYC Open Data terms; City of Chicago Terms of Use; City of Philadelphia open data; Los Angeles open data
  (attribute LADBS). Population: Census Vintage 2024, public domain.
- **Not at a public URL.** The model reads the two Parquet files from `PermitsFolder` (below). For the service
  test they were copied to the `PermitsData` lakehouse in Semantic Models Lab (`Files/permits/`) with `fab cp`.

### What the data can and can't say (from the factory's red team)

- **A permit is not the same unit everywhere.** Compare **categories**, not raw totals.
- **Austin copies the project's unit count onto every building permit under one master** (phases, fire areas,
  amenity buildings). `Housing Units` keeps one of those copies when 2–4 related permits share the same unit
  count and the same description (or phase / fire-area / leasing / amenity wording). Complexes of identical
  buildings (15 × 27 units) are kept. After that Austin is about 10.4 homes per 1,000 residents a year
  (2023–2025), near the red team's 10.7.
- **Los Angeles mixed-use apartments** (`Bldg-New | Commercial | Apartment` and similar) sit in
  `new_nonresidential` in the join; `Housing Units` still counts them. That closes LA's gap to BPS.
- **Boston, New Orleans and Montgomery County** publish no usable unit counts; `Housing Units` and the per-capita
  measures are blank for them. Montgomery's file carries a 1-per-house proxy (every new single-family or townhouse
  permit = 1, multifamily = nothing; 3,690 units 2023–2026, max 1 per permit); the model blanks it in Power Query
  so the data agrees with `Units Published` = false.
- **Valuation** is self-declared. Austin's field is unusable (copied onto trades); Philadelphia publishes none;
  NYC has $1,000 placeholders. `Valuation USD` drops Austin and values outside 1 .. $2 billion.
- **2026 is year-to-date** (to ~23 Nov). Chicago's unit field goes blank after 30 Sep 2026. Seattle's 2026
  Jan–Oct drop is one 734-unit permit in October 2025; Jan–Sep is about −9%.
- **Apply date** is missing for Boston, Philadelphia and many LA over-the-counter rows. **Final date** trails
  issue, so recent years are incomplete.

## Grain and size

| Fact | Grain | Rows |
|---|---|---|
| Fact Permit | one permit as the city defines it | 1,519,874 |

## Star schema

```
Issue Date (1 day)  1 --* Fact Permit *-- 1  Jurisdiction (pop, units published)
Apply Date (1 day)  1 --*      |       *-- 1  Category (14)
Final Date (1 day)  1 --*      |       *-- 1  Work Class
                               *-- 1  Use Class
                               *-- 1  Status
```

Every relationship is many-to-one, single direction. **Three marked date tables** (CMS/NOAA role-playing): a
slicer on Issue Date means "issued that day", Apply Date means "filed that day", Final Date means "finaled that
day". Do not put all three on one page unless the AND of the three roles is the question. Headline housing and
volume measures follow Issue Date.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Permit | 1,519,874 | Permit Key | measures only |
| Jurisdiction | 10 | Jurisdiction | Population, Units Published, Licence |
| Category | 14 | Category Key | Category, Work Class |
| Work Class | 6 | Work Class | |
| Use Class | 5 | Use Class | Use Class Label |
| Status | 7 | Status | Status Label |
| Issue Date, Apply Date, Final Date | 1,826 each (2022–2026) | Date | Year, Quarter, Month, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `PermitsFolder` | OneLake URL of `PermitsData/Files/permits` | Folder holding `permits.parquet` and `housing_units.parquet` |
| `PermitFiles` | shared, not loaded | `AzureStorage.DataLake ( PermitsFolder )` |
| `Calendar` | shared, not loaded | 2022-01-01 to 2026-12-31 |

No incremental refresh: the factory rebuilds the whole snapshot.

## Measures (17)

| Folder | Measures |
|---|---|
| Volume | Permits |
| Housing | Housing Units, Housing Units per 1,000 per Year, Units in 200+ Permits, Share of Units in 200+ Permits |
| Speed | Median Days Apply to Issue, Same-Day Issue Share |
| Value | Valuation USD, New Construction Valuation |
| Time | Last Issue Date (helper), Permits Prior Year, Permits YoY %, Housing Units Prior Year, Housing Units YoY % |
| Pipeline | Applications, Finaled Permits |
| About | Attribution |

`Housing Units per 1,000 per Year` is blank unless exactly one jurisdiction is in context. `Same-Day Issue Share`
compares with `==` (in DAX `BLANK = 0` is true), so permits without both dates are in neither side: Los Angeles
2025 is 12.8% (it read 79% before the 25 Nov fix).

## Ten business questions (acceptance checks)

Expected answers were computed first from the Parquet files with duckdb (`tests/expected.py`).

| # | Question | Expected (duckdb) |
|---|---|---|
| 1 | How much is loaded? | 1,519,874 permits; 244,650 housing units (contribution; 248,340 before Montgomery's proxy was dropped, 25 Nov) |
| 2 | Austin homes per 1,000 residents per year, issue 2023–2025 | 10.43 (31,080 units / 3 / 993,588 × 1000) |
| 3 | Median days apply→issue, new residential, issue year 2025 | Montgomery County 58; San Francisco 648 (647.5) |
| 4 | NYC housing units issued Jan–Oct 2026 vs 2025 | 24,662 vs 12,837 (**+92%**) |
| 5 | Seattle housing units issued Jan–Sep (not Oct) 2026 vs 2025 | 2,108 vs 2,329 (**−9.5%**); the −33% Jan–Oct headline is one 734-unit October 2025 permit |
| 6 | Los Angeles housing units 2023–2025 including mixed-use apartments | 35,160 |
| 7 | Chicago new-construction valuation 2023 vs 2025 | $1.99 bn vs $2.76 bn |
| 8 | NYC share of new-residential units in 200+ unit permits, 2023–2025 | 41% (27,128 of 66,863; 77 permits) |
| 9 | Los Angeles homes per 1,000 per year, 2023–2025 | 3.02 |
| 10 | Seattle new-residential **applications** Jan–Oct 2026 vs 2025 (Apply Date) | 1,164 vs 1,008 (**+15%**) |

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/building-permits/BuildingPermits.SemanticModel/definition`).

**In Fabric (25 Nov 2026, F2):** lakehouse **PermitsData**; slim
`permits.parquet` in `Files/permits/`; `fab import`; OAuth2; full refresh **Completed in 47 s**. First attempt with
the 63 MB factory file plus a NestedJoin hit the F2 3 GB cap. `tests/checks.dax` **10/10**; all 17 measures
evaluate. Capacity paused; `az rest` `properties.state` = `Paused`.

**Redeployed 25 Nov 2026 (16:00 UTC) with the bug fixes** (`Same-Day Issue Share` uses `==`; housing units blank
where `Units Published` is false): `fab import -f`, OAuth2 re-set on the OneLake source, full refresh 2 min 11 s.
`tests/checks.dax` **10/10** (Q1 now 244,650 units: the old 248,340 included Montgomery's proxy) plus the same-day
regression (Los Angeles 2025: 0.1283); all 17 measures evaluate. Capacity paused (`Paused`).
