# Building Permits: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`building-permits.ossie.yaml`](building-permits.ossie.yaml). Source model (unchanged): [`BuildingPermits.SemanticModel`](../BuildingPermits.SemanticModel/).

The fact is a join of ten city permit datasets built by a separate data pipeline (not yet published); the
TMDL loads it through Power Query. The twin uses logical source names (`building_permits.<table>`). Issue,
Apply and Final dates are separate role-playing tables, so every relationship is active.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Apply Date | `apply_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Category | `category` | Survives: 4 fields, primary key from the TMDL key column. |
| Fact Permit | `fact_permit` | Survives: 13 fields. |
| Final Date | `final_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Issue Date | `issue_date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Jurisdiction | `jurisdiction` | Survives: 4 fields, primary key from the TMDL key column. |
| Status | `status` | Survives: 2 fields, primary key from the TMDL key column. |
| Use Class | `use_class` | Survives: 2 fields, primary key from the TMDL key column. |
| Work Class | `work_class` | Survives: 2 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Permit to Issue Date | Fact Permit[Issued Date] to Issue Date[Date] | `fact_permit_to_issue_date` | As-is |
| Fact Permit to Apply Date | Fact Permit[Applied Date] to Apply Date[Date] | `fact_permit_to_apply_date` | As-is |
| Fact Permit to Final Date | Fact Permit[Final Date] to Final Date[Date] | `fact_permit_to_final_date` | As-is |
| Fact Permit to Jurisdiction | Fact Permit[Jurisdiction] to Jurisdiction[Jurisdiction] | `fact_permit_to_jurisdiction` | As-is |
| Fact Permit to Category | Fact Permit[Category Key] to Category[Category Key] | `fact_permit_to_category` | As-is |
| Fact Permit to Work Class | Fact Permit[Work Class] to Work Class[Work Class] | `fact_permit_to_work_class` | As-is |
| Fact Permit to Use Class | Fact Permit[Use Class] to Use Class[Use Class] | `fact_permit_to_use_class` | As-is |
| Fact Permit to Status | Fact Permit[Status] to Status[Status] | `fact_permit_to_status` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Permits | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Housing Units | Ports as SQL | `SUM(housing_units_contribution)` |
| Housing Units per 1,000 per Year | Doesn't port | *needs filter context*: blank unless one jurisdiction is in the filters; divides by that jurisdiction's population (from the Jurisdiction table) and by the number of issue years with housing units. Needs the filter guard and fields of two other datasets. |
| Units in 200+ Permits | Ports as SQL | `SUM(housing_units_contribution) FILTER (WHERE units_added >= 200)` |
| Share of Units in 200+ Permits | Ports as SQL | `SUM(housing_units_contribution) FILTER (WHERE units_added >= 200) / NULLIF(SUM(housing_units_contribution), 0)` |
| Median Days Apply to Issue | Ports as SQL | `MEDIAN(days_apply_to_issue)` |
| Same-Day Issue Share | Ports as SQL | `COUNT(*) FILTER (WHERE days_apply_to_issue = 0) / NULLIF(COUNT(*) FILTER (WHERE days_apply_to_issue IS NOT NULL), 0)`. The DAX compares with `==` (fixed 25 Nov 2026; `= 0` was true for blank), so a null day-count is in neither side, as SQL `= 0` drops it. The DAX numerator is `COALESCE(..., 0)`, the 0 that `COUNT(*)` returns. |
| Valuation USD | Ports as SQL | `SUM(valuation_usable)` |
| New Construction Valuation | Ports as SQL | `SUM(valuation_usable) FILTER (WHERE category_key IN ('new_residential', 'new_nonresidential'))`. `Category[Work Class] = "new"` holds for exactly these two category keys (the Category table's own M), and the fact carries `category_key`. |
| Last Issue Date | Ports as SQL | `MAX(issued_date)` |
| Permits Prior Year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Permits YoY % | Doesn't port | *time intelligence*: Depends on `permits_prior_year`, which doesn't port. |
| Housing Units Prior Year | Doesn't port | *time intelligence*: `SAMEPERIODLASTYEAR` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Housing Units YoY % | Doesn't port | *time intelligence*: Depends on `housing_units_prior_year`, which doesn't port. |
| Applications | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE applied_date IS NOT NULL), 0)` |
| Finaled Permits | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE final_date IS NOT NULL), 0)` |
| Attribution | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |

**Count:** 17 measures. 11 port as SQL, 0 port with changes, 6 don't port (11 of 17 ported).

Why the rest don't port: time intelligence (4); needs filter context (1); text, not a number (1).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
