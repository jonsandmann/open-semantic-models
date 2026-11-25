# NASA FIRMS Active Fires: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`nasa-firms.ossie.yaml`](nasa-firms.ossie.yaml). Source model (unchanged): [`NasaFirms.SemanticModel`](../NasaFirms.SemanticModel/).

Detections load from NASA LANCE FIRMS country yearly CSVs through Power Query. The twin uses logical source names
(`nasa_firms.<table>`). The three products (VIIRS NOAA-20, VIIRS S-NPP, MODIS) see the same fires, so the
model's headline measures count one product at a time: VIIRS NOAA-20 when the report picks none. That rule reads
what the report has filtered, which is why almost nothing in this model ports.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Confidence Band | `confidence_band` | Survives: 2 fields, primary key from the TMDL key column. |
| Country | `country` | Survives: 1 fields, primary key from the TMDL key column. |
| Date | `date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Day Night | `day_night` | Survives: 1 fields, primary key from the TMDL key column. |
| Fact Detection | `fact_detection` | Survives: 14 fields. |
| Hotspot Type | `hotspot_type` | Survives: 2 fields, primary key from the TMDL key column. |
| Satellite | `satellite` | Survives: 4 fields, primary key from the TMDL key column. |
| Source | `source` | Survives: 4 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Detection to Date | Fact Detection[Acq Date] to Date[Date] | `fact_detection_to_date` | As-is |
| Fact Detection to Source | Fact Detection[Source] to Source[Source] | `fact_detection_to_source` | As-is |
| Fact Detection to Satellite | Fact Detection[Satellite] to Satellite[Satellite] | `fact_detection_to_satellite` | As-is |
| Fact Detection to Country | Fact Detection[Country] to Country[Country] | `fact_detection_to_country` | As-is |
| Fact Detection to Confidence Band | Fact Detection[Confidence Band] to Confidence Band[Confidence Band] | `fact_detection_to_confidence_band` | As-is |
| Fact Detection to Day Night | Fact Detection[Day Night] to Day Night[Day Night] | `fact_detection_to_day_night` | As-is |
| Fact Detection to Hotspot Type | Fact Detection[Type Code] to Hotspot Type[Type Code] | `fact_detection_to_hotspot_type` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Detections | Doesn't port | *needs filter context*: counts VIIRS NOAA-20 only when no source or satellite is picked, and the picked source otherwise, so the three overlapping products are never added. `ISFILTERED` has no Ossie form; `COUNT(*) FILTER (WHERE source = 'VIIRS NOAA-20')` would be right only for the default view. |
| Detections in source | Doesn't port | *needs filter context*: blank unless exactly one source is in the filters (`INTERSECT(VALUES(...))`). Reads the query's filters. |
| Vegetation detections | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| High confidence detections | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| High confidence share | Doesn't port | *needs filter context*: Depends on `high_confidence_detections`, which doesn't port. |
| Day share | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| Satellites in scope | Doesn't port | *needs filter context*: same source rule as `detections`. |
| Total FRP | Doesn't port | *needs filter context*: same source rule as `detections`. |
| Average FRP | Doesn't port | *needs filter context*: Depends on `total_frp`, which doesn't port. |
| Vegetation FRP | Doesn't port | *needs filter context*: Depends on `total_frp`, which doesn't port. |
| Last Acq Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Detections YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Detections prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Detections YoY % | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| FRP prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| FRP YoY % | Doesn't port | *needs filter context*: Depends on `total_frp`, which doesn't port. |
| Peak day | Doesn't port | *two-level aggregation*: `TOPN` over the days in the filters, ranked by a measure. A ranking over a grain, not one aggregate. |
| Peak day detections | Doesn't port | *two-level aggregation*: Depends on `peak_day`, which doesn't port. |
| Static land detections | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| Low confidence detections | Doesn't port | *needs filter context*: Depends on `detections`, which doesn't port. |
| All product rows | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Citation | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |
| Disclaimer | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |

**Count:** 23 measures. 1 port as SQL, 0 port with changes, 22 don't port (1 of 23 ported).

Why the rest don't port: needs filter context (15); time intelligence (3); two-level aggregation (2); text, not a number (2).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
