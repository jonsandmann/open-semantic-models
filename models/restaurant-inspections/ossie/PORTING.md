# Restaurant Inspections: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`restaurant-inspections.ossie.yaml`](restaurant-inspections.ossie.yaml). Source model (unchanged): [`RestaurantInspections.SemanticModel`](../RestaurantInspections.SemanticModel/).

The two facts are a join of ten city inspection datasets built by a separate data pipeline (not yet published);
the TMDL loads them through Power Query. The twin uses logical source names (`restaurant_inspections.<table>`).
Most rates divide by inspections in jurisdictions that publish violations, a flag on the Jurisdiction table.
That table is typed in M and the flag is false only for Austin, so the flag ports as a filter on the fact's
`jurisdiction_key`. Rates that divide Fact Violation by Fact Inspection, and filters on the outcome tier or
closure flag (not a function of a fact column), stay DAX.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Critical Band | `critical_band` | Survives: 2 fields, primary key from the TMDL key column. |
| Critical Flag | `critical_flag` | Survives: 2 fields, primary key from the TMDL key column. |
| Date | `date` | Survives: 14 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Establishment | `establishment` | Survives: 16 fields, primary key from the TMDL key column. |
| Fact Inspection | `fact_inspection` | Survives: 14 fields, primary key from the TMDL key column. |
| Fact Violation | `fact_violation` | Survives: 6 fields. |
| Inspection Type | `inspection_type` | Survives: 3 fields, primary key from the TMDL key column. |
| Jurisdiction | `jurisdiction` | Survives: 11 fields, primary key from the TMDL key column. |
| Outcome | `outcome` | Survives: 6 fields, primary key from the TMDL key column. |
| Violation Category | `violation_category` | Survives: 5 fields, primary key from the TMDL key column. |
| Violation Code | `violation_code` | Survives: 4 fields, primary key from the TMDL key column. |
| Visit Kind | `visit_kind` | Survives: 2 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Inspection to Date | Fact Inspection[Inspection Date] to Date[Date] | `fact_inspection_to_date` | As-is |
| Fact Inspection to Establishment | Fact Inspection[Establishment Key] to Establishment[Establishment Key] | `fact_inspection_to_establishment` | As-is |
| Fact Inspection to Jurisdiction | Fact Inspection[Jurisdiction Key] to Jurisdiction[Jurisdiction Key] | `fact_inspection_to_jurisdiction` | As-is |
| Fact Inspection to Outcome | Fact Inspection[Outcome Key] to Outcome[Outcome Key] | `fact_inspection_to_outcome` | As-is |
| Fact Inspection to Inspection Type | Fact Inspection[Inspection Type Key] to Inspection Type[Inspection Type Key] | `fact_inspection_to_inspection_type` | As-is |
| Fact Inspection to Critical Band | Fact Inspection[Critical Band Key] to Critical Band[Critical Band Key] | `fact_inspection_to_critical_band` | As-is |
| Fact Inspection to Visit Kind | Fact Inspection[Visit Kind Key] to Visit Kind[Visit Kind Key] | `fact_inspection_to_visit_kind` | As-is |
| Fact Violation to Fact Inspection | Fact Violation[Inspection Key] to Fact Inspection[Inspection Key] | `fact_violation_to_fact_inspection` | As-is |
| Fact Violation to Violation Category | Fact Violation[Category Key] to Violation Category[Category Key] | `fact_violation_to_violation_category` | As-is |
| Fact Violation to Critical Flag | Fact Violation[Critical Flag] to Critical Flag[Critical Flag] | `fact_violation_to_critical_flag` | As-is |
| Fact Violation to Violation Code | Fact Violation[Violation Code Key] to Violation Code[Violation Code Key] | `fact_violation_to_violation_code` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Inspections | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Inspections with violation data | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto')), 0)`. `Jurisdiction[Publishes Violations]` is true for these nine keys (the Jurisdiction table is typed in M; only Austin is false), and the fact carries `jurisdiction_key`. |
| Establishments inspected | Ports as SQL | `NULLIF(COUNT(DISTINCT establishment_key), 0)` |
| Inspections per establishment | Ports as SQL | `NULLIF(COUNT(*), 0) / NULLIF(COUNT(DISTINCT establishment_key), 0)` |
| Follow-up share | Ports as SQL | `COUNT(*) FILTER (WHERE visit_kind_key = 2) / NULLIF(COUNT(*), 0)` |
| Share with no violation | Ports as SQL | `COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto') AND COALESCE(violation_count, 0) = 0) / NULLIF(COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto')), 0)`. `Jurisdiction[Publishes Violations]` is true for these nine keys (the Jurisdiction table is typed in M; only Austin is false), and the fact carries `jurisdiction_key`. DAX compares a blank violation count as 0, hence the `COALESCE`. |
| Average burden score | Ports as SQL | `AVG(burden_score)` |
| Inspections with 3+ criticals | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto') AND critical_band_key = 3), 0)`. `Jurisdiction[Publishes Violations]` is true for these nine keys (the Jurisdiction table is typed in M; only Austin is false), and the fact carries `jurisdiction_key`. |
| Share with 3+ criticals | Ports as SQL | `COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto') AND critical_band_key = 3) / NULLIF(COUNT(*) FILTER (WHERE jurisdiction_key IN ('nyc', 'chicago', 'king_county', 'montgomery', 'delaware', 'marin', 'ny_state', 'boston', 'toronto')), 0)`. `Jurisdiction[Publishes Violations]` is true for these nine keys (the Jurisdiction table is typed in M; only Austin is false), and the fact carries `jurisdiction_key`. |
| Inspections with a verdict | Doesn't port | *filter on a dimension attribute*: `FILTER (WHERE ...)` may only reference the aggregate's own dataset, and the fact has no copy of that column. |
| Re-inspection rate at 3+ criticals | Doesn't port | *filter on a dimension attribute*: Depends on `inspections_with_a_verdict`, which doesn't port. |
| Closures | Doesn't port | *filter on a dimension attribute*: `FILTER (WHERE ...)` may only reference the aggregate's own dataset, and the fact has no copy of that column. |
| Closure rate | Doesn't port | *filter on a dimension attribute*: Depends on `closures`, which doesn't port. |
| Closure rate at 3+ criticals | Doesn't port | *filter on a dimension attribute*: Depends on `closures`, which doesn't port. |
| Published outcome | Doesn't port | *filter on a dimension attribute*: Depends on `inspections_with_a_verdict`, which doesn't port. |
| Last inspection date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Inspections prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Inspections YoY % | Doesn't port | *time intelligence*: Depends on `inspections_prior_year`, which doesn't port. |
| Violations | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Critical violations | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE critical_flag = 'Critical'), 0)` |
| Critical share of violations | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE critical_flag = 'Critical'), 0) / NULLIF(COUNT(*), 0)` |
| Violations per inspection | Doesn't port | *divides measures of two facts*: Divides a Fact Violation count by a Fact Inspection count. A dataset metric aggregates one dataset, and this twin does not compose model metrics across the two facts. |
| Critical violations per inspection | Doesn't port | *divides measures of two facts*: Divides a Fact Violation count by a Fact Inspection count. A dataset metric aggregates one dataset, and this twin does not compose model metrics across the two facts. |
| Inspections citing | Ports as SQL | `NULLIF(COUNT(DISTINCT inspection_key), 0)` |
| Share of inspections citing | Doesn't port | *divides measures of two facts*: Divides a Fact Violation count by a Fact Inspection count. A dataset metric aggregates one dataset, and this twin does not compose model metrics across the two facts. |
| Chain critical per inspection | Doesn't port | *divides measures of two facts*: Depends on `critical_violations_per_inspection`, which doesn't port. |
| Independent critical per inspection | Doesn't port | *divides measures of two facts*: Depends on `critical_violations_per_inspection`, which doesn't port. |
| Chain ratio | Doesn't port | *needs filter context*: `HASONEVALUE` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Critical per inspection prior year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Critical per inspection change | Doesn't port | *time intelligence*: Depends on `critical_per_inspection_prior_year`, which doesn't port. |
| Attribution | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |

**Count:** 31 measures. 13 port as SQL, 0 port with changes, 18 don't port (13 of 31 ported).

Why the rest don't port: filter on a dimension attribute (6); divides measures of two facts (5); time intelligence (4); needs filter context (2); text, not a number (1).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
