# CMS Hospital Quality: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`cms-hospital-quality.ossie.yaml`](cms-hospital-quality.ossie.yaml). Source model (unchanged): [`CmsHospitalQuality.SemanticModel`](../CmsHospitalQuality.SemanticModel/).

Both facts load from CMS Care Compare files through Power Query and keep every release that was loaded. The
results and the star ratings are snapshots: each measure keeps only the latest release inside the current
filters, so summing across releases would count a hospital once per release. That one rule keeps most of this
model in DAX. The twin uses logical source names (`cms_hospital_quality.<table>`).

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Fact Measure Result | `fact_measure_result` | Survives: 11 fields. |
| Fact Overall Rating | `fact_overall_rating` | Survives: 15 fields. |
| Hospital | `hospital` | Survives: 13 fields, primary key from the TMDL key column. |
| Performance Date | `performance_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Quality Measure | `quality_measure` | Survives: 5 fields, primary key from the TMDL key column. |
| Release Date | `release_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Measure Result to Hospital | Fact Measure Result[Facility ID] to Hospital[Facility ID] | `fact_measure_result_to_hospital` | As-is |
| Fact Measure Result to Quality Measure | Fact Measure Result[Measure ID] to Quality Measure[Measure ID] | `fact_measure_result_to_quality_measure` | As-is |
| Fact Measure Result to Performance Date (End Date) | Fact Measure Result[End Date] to Performance Date[Date] | `fact_measure_result_to_performance_date_end_date` | As-is |
| Fact Measure Result to Performance Date (Start Date) | Fact Measure Result[Start Date] to Performance Date[Date] | not carried | Not carried. Inactive in TMDL (used only through USERELATIONSHIP). Ossie has no inactive flag, so a second path between the same datasets would make joins ambiguous. |
| Fact Measure Result to Release Date | Fact Measure Result[Release Date] to Release Date[Date] | `fact_measure_result_to_release_date` | As-is |
| Fact Overall Rating to Hospital | Fact Overall Rating[Facility ID] to Hospital[Facility ID] | `fact_overall_rating_to_hospital` | As-is |
| Fact Overall Rating to Release Date | Fact Overall Rating[Release Date] to Release Date[Date] | `fact_overall_rating_to_release_date` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Latest result release | Ports as SQL | `MAX(release_date)` |
| Results | Doesn't port | *semi-additive*: counts results in the latest release inside the filters. Results are a snapshot per release. |
| Hospitals with a result | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Reported scores | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| Results by window start | Doesn't port | *needs filter context*: `USERELATIONSHIP` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Results by release | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Average score | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Denominator weighted score | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Total denominator | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Better than national | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| Worse than national | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| No different than national | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| Too small to compare | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| Not available to compare | Doesn't port | *semi-additive*: Depends on `results`, which doesn't port. |
| Share worse | Doesn't port | *semi-additive*: Depends on `worse_than_national`, which doesn't port. |
| Share better | Doesn't port | *semi-additive*: Depends on `better_than_national`, which doesn't port. |
| Latest release date | Ports as SQL | `MAX(release_date)` |
| Hospitals rated | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Average stars | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Five star hospitals | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| One star hospitals | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Five star share | Doesn't port | *semi-additive*: Depends on `five_star_hospitals`, which doesn't port. |
| One star share | Doesn't port | *semi-additive*: Depends on `one_star_hospitals`, which doesn't port. |
| Mortality measures worse | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Safety measures worse | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Readmission measures worse | Doesn't port | *semi-additive*: keeps only the latest date or release inside the current filters (`VAR ... = MAX(...)` then `CALCULATE`). One OSSIE_SQL_2026 aggregate can't pin itself to the max of the query's own rows without a subquery. |
| Hospitals | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Birthing friendly hospitals | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE birthing_friendly = 'Y'), 0)` |

**Count:** 28 measures. 4 port as SQL, 0 port with changes, 24 don't port (4 of 28 ported).

Why the rest don't port: semi-additive (22); needs filter context (2).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
