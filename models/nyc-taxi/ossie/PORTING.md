# NYC Taxi Trips: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`nyc-taxi.ossie.yaml`](nyc-taxi.ossie.yaml). Source model (unchanged): [`NycTaxi.SemanticModel`](../NycTaxi.SemanticModel/).

Trips load from the TLC's monthly Parquet files through Power Query with incremental refresh; Pickup Zone and
Dropoff Zone are role-playing copies of the TLC zone lookup. The twin uses logical source names
(`nyc_taxi.<table>`). Payment type and airport filters are on dimension keys, which the fact carries as foreign
keys, so they port as `FILTER (WHERE ...)` on the fact.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Date | `date` | Survives: 17 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. 1 calculated column carried as opaque DAX. |
| Dropoff Zone | `dropoff_zone` | Survives: 4 fields, primary key from the TMDL key column. |
| Payment Type | `payment_type` | Survives: 3 fields, primary key from the TMDL key column. |
| Pickup Zone | `pickup_zone` | Survives: 4 fields, primary key from the TMDL key column. |
| Rate Code | `rate_code` | Survives: 3 fields, primary key from the TMDL key column. |
| Time of Day | `time_of_day` | Survives: 4 fields, primary key from the TMDL key column. |
| Trips | `trips` | Survives: 20 fields. |
| Vendor | `vendor` | Survives: 2 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Trips to Date | Trips[Pickup Date] to Date[Date] | `trips_to_date` | As-is |
| Trips to Time of Day | Trips[Pickup Hour] to Time of Day[Hour] | `trips_to_time_of_day` | As-is |
| Trips to Pickup Zone | Trips[Pickup Location ID] to Pickup Zone[Pickup Location ID] | `trips_to_pickup_zone` | As-is |
| Trips to Dropoff Zone | Trips[Dropoff Location ID] to Dropoff Zone[Dropoff Location ID] | `trips_to_dropoff_zone` | As-is |
| Trips to Vendor | Trips[Vendor ID] to Vendor[Vendor ID] | `trips_to_vendor` | As-is |
| Trips to Rate Code | Trips[Rate Code ID] to Rate Code[Rate Code ID] | `trips_to_rate_code` | As-is |
| Trips to Payment Type | Trips[Payment Type ID] to Payment Type[Payment Type ID] | `trips_to_payment_type` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. One difference holds for every ported count: on an empty group DAX returns blank and SQL `COUNT` returns 0.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Trips | Ports as SQL | `COUNT(*)` |
| Passengers | Ports as SQL | `SUM(passenger_count)` |
| Avg Passengers per Trip | Ports as SQL | `SUM(passenger_count) / NULLIF(COUNT(*) FILTER (WHERE passenger_count IS NOT NULL), 0)` |
| Trips per Day | Ports as SQL | `COUNT(*) / NULLIF(COUNT(DISTINCT pickup_date), 0)` |
| Total Miles | Ports as SQL | `SUM(trip_miles)` |
| Avg Miles per Trip | Ports as SQL | `SUM(trip_miles) / NULLIF(COUNT(*), 0)` |
| Trip Hours | Ports as SQL | `SUM(trip_minutes) / 60` |
| Avg Trip Minutes | Ports as SQL | `SUM(trip_minutes) / NULLIF(COUNT(*), 0)` |
| Avg Speed (mph) | Ports as SQL | `(SUM(trip_miles) FILTER (WHERE trip_miles >= 0.1 AND trip_miles <= 200 AND trip_minutes >= 1 AND trip_minutes <= 300) * 60) / NULLIF(SUM(trip_minutes) FILTER (WHERE trip_miles >= 0.1 AND trip_miles <= 200 AND trip_minutes >= 1 AND trip_minutes <= 300), 0)` |
| Fare Revenue | Ports as SQL | `SUM(fare_amount)` |
| Tips | Ports as SQL | `SUM(tip_amount)` |
| Tolls | Ports as SQL | `SUM(tolls_amount)` |
| Taxes and Surcharges | Ports as SQL | `SUM(extra_amount) + SUM(mta_tax) + SUM(improvement_surcharge) + SUM(congestion_surcharge) + SUM(airport_fee) + SUM(cbd_congestion_fee)` |
| CBD Congestion Fees | Ports as SQL | `SUM(cbd_congestion_fee)` |
| Total Revenue | Ports as SQL | `SUM(total_amount)` |
| Avg Fare per Trip | Ports as SQL | `SUM(fare_amount) / NULLIF(COUNT(*), 0)` |
| Avg Revenue per Trip | Ports as SQL | `SUM(total_amount) / NULLIF(COUNT(*), 0)` |
| Fare per Mile | Ports as SQL | `SUM(fare_amount) / NULLIF(SUM(trip_miles), 0)` |
| Card Trips | Ports as SQL | `COUNT(*) FILTER (WHERE payment_type_id = 1)` |
| Card Payment % | Ports as SQL | `COUNT(*) FILTER (WHERE payment_type_id = 1) / NULLIF(COUNT(*), 0)` |
| Card Tips | Ports as SQL | `SUM(tip_amount) FILTER (WHERE payment_type_id = 1)` |
| Card Tip Rate % | Ports as SQL | `SUM(tip_amount) FILTER (WHERE payment_type_id = 1) / NULLIF(SUM(fare_amount) FILTER (WHERE payment_type_id = 1), 0)` |
| Avg Tip per Card Trip | Ports as SQL | `SUM(tip_amount) FILTER (WHERE payment_type_id = 1) / NULLIF(COUNT(*) FILTER (WHERE payment_type_id = 1), 0)` |
| Airport Pickups | Ports as SQL | `COUNT(*) FILTER (WHERE pickup_location_id IN (1, 132, 138))` |
| Airport Pickup % | Ports as SQL | `COUNT(*) FILTER (WHERE pickup_location_id IN (1, 132, 138)) / NULLIF(COUNT(*), 0)` |
| CBD Zone Trips | Ports as SQL | `COUNT(*) FILTER (WHERE cbd_congestion_fee > 0)` |
| CBD Zone Trip % | Ports as SQL | `COUNT(*) FILTER (WHERE cbd_congestion_fee > 0) / NULLIF(COUNT(*), 0)` |
| Last Trip Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Trips YTD | Doesn't port | *time intelligence*: `DATESYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Trips PY | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Trips PY YTD | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Trips YoY | Doesn't port | *time intelligence*: Depends on `trips_py`, which doesn't port. |
| Trips YoY % | Doesn't port | *time intelligence*: Depends on `trips_yoy`, which doesn't port. |
| Trips YTD YoY % | Doesn't port | *time intelligence*: Depends on `trips_ytd`, which doesn't port. |
| Total Revenue YTD | Doesn't port | *time intelligence*: `DATESYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Total Revenue PY | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Total Revenue PY YTD | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Total Revenue YoY | Doesn't port | *time intelligence*: Depends on `total_revenue_py`, which doesn't port. |
| Total Revenue YoY % | Doesn't port | *time intelligence*: Depends on `total_revenue_yoy`, which doesn't port. |
| Total Revenue YTD YoY % | Doesn't port | *time intelligence*: Depends on `total_revenue_ytd`, which doesn't port. |
| Avg Fare per Trip PY | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Avg Fare per Trip YoY % | Doesn't port | *time intelligence*: Depends on `avg_fare_per_trip_py`, which doesn't port. |

**Count:** 42 measures. 27 port as SQL, 0 port with changes, 15 don't port (27 of 42 ported).

Why the rest don't port: time intelligence (14); needs filter context (1).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
