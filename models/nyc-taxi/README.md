# NYC Taxi Trips

A star-schema semantic model of New York City yellow taxi trips: volume, distance, speed, fares, tips, surcharges
(including the 2025 congestion relief zone fee) and airport traffic, with year-to-date and prior-year comparisons.

## Source

- **Publisher:** NYC Taxi & Limousine Commission (TLC), [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
- **Files:** one Parquet file per month, `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet`
  (about 60 MB and 3.5 million trips a month), plus the zone lookup
  `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` (265 zones).
- **Data dictionary:** [Yellow Taxi Trip Records, March 2025](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).
  Vendor, rate code and payment type labels in the model come from it.
- **Licence:** published as NYC Open Data under the
  [NYC Open Data Terms of Use](https://opendata.cityofnewyork.us/overview/#termsofuse): free to use, share and build on,
  no registration; the City makes no warranty about accuracy. Attribute "NYC Taxi & Limousine Commission".
- **Refreshed by:** Power Query M in the model (`Web.Contents` + `Parquet.Document`), straight from the public URLs.
  Nothing is copied into this repo.

## Grain and size

`Trips` holds one row per trip reported by a TPEP provider, keyed to the day and hour the meter was engaged.
Pickup and dropoff timestamps are reduced to date, hour and duration so the fact table compresses well.

| Window | Trips (approx.) |
|---|---|
| Development default (`RangeStart` 2025-01-01 to `RangeEnd` 2025-03-01) | 7 million |
| One year | 40 million |
| Incremental refresh policy (3 years rolling) | 120 million |

## Star schema

```
                         Date (marked date table)
                          | Date 1
                          |
   Time of Day 1 ---- * Trips * ---- 1 Pickup Zone
   (Hour)        Pickup Hour |  Pickup Location ID
                             |
      Vendor 1 ---------- *  |  * ---------- 1 Dropoff Zone
                             |    Dropoff Location ID
   Rate Code 1 ---------- *  |  * ---------- 1 Payment Type
```

All seven relationships are many-to-one from `Trips`, single direction (dimension filters fact), active, on integer
keys except the date (a `dateTime` key, as the date table requires). `Pickup Zone` and `Dropoff Zone` are role-playing
copies of one shared query (`TaxiZoneLookup`), with prefixed column names so a visual never shows two "Borough"s.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Trips (fact) | per trip | none (all columns hidden) | measures only |
| Date | 1,461 (2023 to 2026) | Date | Year, Quarter, Year Quarter, Month, Month Short, Year Month, Day of Month, Day of Week, Week Start, Is Weekend |
| Time of Day | 24 | Hour (hidden) | Hour Label, Day Part |
| Pickup Zone / Dropoff Zone | 265 each | Location ID (hidden) | Borough, Zone Name, Service Zone |
| Vendor | 4 | Vendor ID (hidden) | Vendor |
| Rate Code | 7 | Rate Code ID (hidden) | Rate Code, Fare Basis |
| Payment Type | 7 | Payment Type ID (hidden) | Payment Type, Payment Group |

## Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `TlcBaseUrl` | `https://d37ci6vzurychx.cloudfront.net/` | Host for both sources |
| `RangeStart`, `RangeEnd` | 2025-01-01, 2025-03-01 | Incremental refresh bounds; in Desktop they set the development window |
| `CalendarStart`, `CalendarEnd` | 2023-01-01, 2026-12-31 | Date table span, independent of the refresh range |

**Incremental refresh:** 3 years rolling, the last 3 months refreshed. The source query picks only the monthly files
inside each partition's range, and a month TLC hasn't published yet (CloudFront answers 403) comes back empty instead of
failing the refresh.

## Measures (42)

| Folder | Measures |
|---|---|
| Volume | Trips, Passengers, Avg Passengers per Trip, Trips per Day |
| Distance and Time | Total Miles, Avg Miles per Trip, Trip Hours, Avg Trip Minutes, Avg Speed (mph) |
| Revenue | Fare Revenue, Tips, Tolls, Taxes and Surcharges, CBD Congestion Fees, Total Revenue, Avg Fare per Trip, Avg Revenue per Trip, Fare per Mile |
| Tipping | Card Trips, Card Payment %, Card Tips, Card Tip Rate %, Avg Tip per Card Trip |
| Mix | Airport Pickups, Airport Pickup %, CBD Zone Trips, CBD Zone Trip % |
| Time Intelligence\Trips | Trips YTD, Trips PY, Trips PY YTD, Trips YoY, Trips YoY %, Trips YTD YoY % |
| Time Intelligence\Revenue | Total Revenue YTD, Total Revenue PY, Total Revenue PY YTD, Total Revenue YoY, Total Revenue YoY %, Total Revenue YTD YoY % |
| Time Intelligence\Fares | Avg Fare per Trip PY, Avg Fare per Trip YoY % |
| Helpers (hidden) | Last Trip Date |

Notes on the logic:

- **Prior year compares like for like.** PY measures shift only dates on or before the last loaded pickup (`'Date'[Through Last Trip Date]`, a contiguous cutoff, not a per-day has-trips flag), so a
  partial current month is compared with the same days a year earlier, not a whole month.
- **YTD stops at the data.** YTD measures are blank after `[Last Trip Date]`, so a line chart doesn't run flat to December.
- **Tips are card tips.** Cash tips are not recorded, so the tipping folder reads tips against card fares only.
- **Speed excludes meter noise:** only trips of 0.1 to 200 miles and 1 to 300 minutes count.
- **Refunds stay in.** Voids and disputes appear as negative amounts, as TLC reports them; filter on Payment Group to exclude them.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/nyc-taxi/NycTaxi.SemanticModel/definition`):
the TMDL deserializes, `Model.Validate()` reports no errors, and the model round-trips TMDL -> TOM -> TMDL -> TOM.

**Best practice checklist** (rules from Microsoft's Best Practice Analyzer set, checked by `tools/TmdlCheck`; all pass):

| Rule | Status |
|---|---|
| Every table, column, measure and expression has a description | Pass |
| Measures have format strings; percentages use `%` formats | Pass |
| Visible measures are in display folders | Pass |
| Numeric columns don't summarize (`summarizeBy: none`); implicit measures discouraged at model level | Pass |
| Foreign keys hidden; dimension keys marked `isKey` | Pass |
| Month, weekday, year-month, year-quarter and day-part labels have sort-by columns | Pass |
| A date table is marked (`dataCategory: Time`, `isKey` date column); auto date/time off | Pass |
| No bi-directional or many-to-many relationships; all relationships many-to-one | Pass |
| Relationship columns share data types; no orphan tables | Pass |
| No floating point columns (fixed decimal for money, miles and minutes) | Pass |
| Fact columns hidden and `isAvailableInMdx: false` where not keys | Pass |
| Large fact table has an incremental refresh policy | Pass |
| DIVIDE instead of `/`; no IFERROR/ISERROR | Pass |
| Columns fully qualified, measures never qualified; every reference resolves | Pass |
| Object names trimmed and capitalised; no measure/column name collisions | Pass |

Known, deliberate exception to the BPA set: "relationship columns should be integers" doesn't hold for
`Trips[Pickup Date]` -> `'Date'[Date]`; the marked date table relates on its date column.

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import`, refreshed 13 months (January 2024 to
January 2025, 44.6 million trips, 39 minutes) from the public URLs, and queried with `tests/checks.dax`. January 2025
trips, revenue and card tip rate match figures computed independently from the raw Parquet file; prior-year, YoY and
YTD measures return the expected values; no orphan keys. Details in the
[run log](../../docs/toolchain.md#run-log).

| January 2025 | Value |
|---|---|
| Trips | 3,475,206 (YoY +17.2%) |
| Total Revenue | $89.0M (YoY +12.0%) |
| Avg Fare per Trip | $17.08 (YoY -6.0%) |
| Card Tip Rate % | 22.8% |
| CBD Zone Trip % | 64.6% |
| Avg Speed (mph) | 13.0 |
