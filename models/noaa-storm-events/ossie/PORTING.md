# NOAA Storm Events: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`noaa-storm-events.ossie.yaml`](noaa-storm-events.ossie.yaml). Source model (unchanged): [`NoaaStormEvents.SemanticModel`](../NoaaStormEvents.SemanticModel/).

Fact Event and Fact Fatality load from NOAA's bulk CSVs through Power Query. The twin uses logical source names
(`noaa_storm_events.<table>`). Role-playing dates are separate tables in the TMDL (Date, End Date, Fatality Date),
so every relationship is active and each survives as a plain join.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Area Type | `area_type` | Survives: 2 fields, primary key from the TMDL key column. |
| Date | `date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| End Date | `end_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Event Type | `event_type` | Survives: 3 fields, primary key from the TMDL key column. |
| Fact Event | `fact_event` | Survives: 19 fields, primary key from the TMDL key column. |
| Fact Fatality | `fact_fatality` | Survives: 5 fields. |
| Fatality Date | `fatality_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Fatality Profile | `fatality_profile` | Survives: 4 fields, primary key from the TMDL key column. |
| State | `state` | Survives: 4 fields, primary key from the TMDL key column. |
| Tornado Scale | `tornado_scale` | Survives: 3 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Event to Date (Begin Date) | Fact Event[Begin Date] to Date[Date] | `fact_event_to_date_begin_date` | As-is |
| Fact Event to End Date | Fact Event[End Date] to End Date[Date] | `fact_event_to_end_date` | As-is |
| Fact Event to State | Fact Event[State] to State[State] | `fact_event_to_state` | As-is |
| Fact Event to Event Type | Fact Event[Event Type] to Event Type[Event Type] | `fact_event_to_event_type` | As-is |
| Fact Event to Area Type | Fact Event[CZ Type] to Area Type[CZ Type] | `fact_event_to_area_type` | As-is |
| Fact Event to Tornado Scale | Fact Event[Tornado Scale] to Tornado Scale[Tornado Scale] | `fact_event_to_tornado_scale` | As-is |
| Fact Fatality to Fact Event | Fact Fatality[Event ID] to Fact Event[Event ID] | `fact_fatality_to_fact_event` | As-is |
| Fact Fatality to Fatality Date | Fact Fatality[Fatality Date] to Fatality Date[Date] | `fact_fatality_to_fatality_date` | As-is |
| Fact Fatality to Fatality Profile | Fact Fatality[Profile Key] to Fatality Profile[Profile Key] | `fact_fatality_to_fatality_profile` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Events | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Episodes | Ports as SQL | `NULLIF(COUNT(DISTINCT episode_id), 0)` |
| States in scope | Ports as SQL | `NULLIF(COUNT(DISTINCT state), 0)` |
| Property damage | Ports as SQL | `SUM(property_damage_usd)` |
| Crop damage | Ports as SQL | `SUM(crop_damage_usd)` |
| Total damage | Ports as SQL | `SUM(COALESCE(property_damage_usd, 0) + COALESCE(crop_damage_usd, 0))`. The SUMX row iterator becomes a SUM over a row expression; same result. |
| Events with property damage | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE property_damage_usd > 0), 0)` |
| Damage per event | Ports as SQL | `SUM(COALESCE(property_damage_usd, 0) + COALESCE(crop_damage_usd, 0)) / NULLIF(COUNT(*), 0)` |
| Deaths | Ports as SQL | `SUM(COALESCE(deaths_direct, 0) + COALESCE(deaths_indirect, 0))`. The SUMX row iterator becomes a SUM over a row expression; same result. |
| Direct deaths | Ports as SQL | `SUM(deaths_direct)` |
| Indirect deaths | Ports as SQL | `SUM(deaths_indirect)` |
| Injuries | Ports as SQL | `SUM(COALESCE(injuries_direct, 0) + COALESCE(injuries_indirect, 0))`. The SUMX row iterator becomes a SUM over a row expression; same result. |
| Events with a death | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE COALESCE(deaths_direct, 0) + COALESCE(deaths_indirect, 0) > 0), 0)` |
| Tornadoes | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE event_type = 'Tornado'), 0)` |
| EF2 or stronger | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE event_type = 'Tornado' AND tornado_scale IN ('EF2', 'EF3', 'EF4', 'EF5', 'F2', 'F3', 'F4', 'F5')), 0)`. `Tornado Scale[Scale Number]` is the digits of the fact's own `tornado_scale` (the dimension's M), and NOAA's ratings are EF0 to EF5, F0 to F5 and EFU, so `Scale Number >= 2` is this list. |
| Tornado path miles | Ports as SQL | `SUM(tornado_length_miles) FILTER (WHERE event_type = 'Tornado')` |
| Average magnitude | Doesn't port | *needs filter context*: blank unless exactly one event type is in the filters (magnitude is knots for wind and inches for hail). `AVG(magnitude)` alone would mix units; the guard reads the query's filters. |
| Events YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Property damage YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Events prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Events YoY % | Doesn't port | *time intelligence*: Depends on `events_prior_year`, which doesn't port. |
| Property damage prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Property damage YoY % | Doesn't port | *time intelligence*: Depends on `property_damage_prior_year`, which doesn't port. |
| Last Begin Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Blank property cells | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE property_damage_usd IS NULL), 0)` |
| File vintage | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Citation | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |
| Fatality records | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Direct fatality records | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE profile_key LIKE 'Direct\|%'), 0)`. The fact's `profile_key` is `Fatality Type \| Location \| Sex` and the type is only Direct, Indirect or Unknown, so its first segment is the dimension's Fatality Type. |
| Indirect fatality records | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE profile_key LIKE 'Indirect\|%'), 0)`. The fact's `profile_key` is `Fatality Type \| Location \| Sex` and the type is only Direct, Indirect or Unknown, so its first segment is the dimension's Fatality Type. |
| Median age at death | Ports as SQL | `MEDIAN(age)` |

**Count:** 31 measures. 21 port as SQL, 0 port with changes, 10 don't port (21 of 31 ported).

Why the rest don't port: time intelligence (6); needs filter context (3); text, not a number (1).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
