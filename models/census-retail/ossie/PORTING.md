# Census Monthly Retail Trade: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`census-retail.ossie.yaml`](census-retail.ossie.yaml). Source model (unchanged): [`CensusRetail.SemanticModel`](../CensusRetail.SemanticModel/).

The fact loads from the Census Bureau workbook through Power Query. The twin uses logical source names
(`census_retail.<table>`). The headline measures read the report's filters twice: the adjustment (not seasonally
adjusted unless one is picked, so the two series are never added) and the kind of business (a line value only
when one kind is in the filters, since kind lines nest and would double count). Both rules are filter context,
so most of this model stays DAX.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Adjustment | `adjustment` | Survives: 2 fields, primary key from the TMDL key column. |
| Date | `date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Fact Retail Sales | `fact_retail_sales` | Survives: 7 fields. |
| Kind | `kind` | Survives: 10 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Retail Sales to Date | Fact Retail Sales[Date] to Date[Date] | `fact_retail_sales_to_date` | As-is |
| Fact Retail Sales to Kind | Fact Retail Sales[Kind Key] to Kind[Kind Key] | `fact_retail_sales_to_kind` | As-is |
| Fact Retail Sales to Adjustment | Fact Retail Sales[Adjustment] to Adjustment[Adjustment] | `fact_retail_sales_to_adjustment` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. One difference holds for every ported count: on an empty group DAX returns blank and SQL `COUNT` returns 0.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Sales in adjustment | Doesn't port | *needs filter context*: returns the one adjustment in the filters, or not seasonally adjusted when none is picked, and blank when both are. `HASONEVALUE` and `ISFILTERED` have no Ossie form. `SUM(sales_usd) FILTER (WHERE adjustment = 'Not seasonally adjusted')` would be right only for the default view. |
| Sales | Doesn't port | *needs filter context*: Depends on `sales_in_adjustment`, which doesn't port. |
| Sales millions | Doesn't port | *needs filter context*: Depends on `sales`, which doesn't port. |
| Line sales | Doesn't port | *needs filter context*: `HASONEVALUE` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Line sales millions | Doesn't port | *needs filter context*: Depends on `line_sales`, which doesn't port. |
| Share of retail and food services | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Share of parent | Doesn't port | *needs filter context*: `SELECTEDVALUE` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Sales YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Sales prior year | Doesn't port | *time intelligence*: `EOMONTH` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Sales YoY % | Doesn't port | *needs filter context*: Depends on `sales`, which doesn't port. |
| Sales prior month | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Sales month to month % | Doesn't port | *needs filter context*: Depends on `sales`, which doesn't port. |
| Line sales YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Line sales prior year | Doesn't port | *time intelligence*: `EOMONTH` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Line sales YoY % | Doesn't port | *needs filter context*: Depends on `line_sales`, which doesn't port. |
| Not adjusted sales | Doesn't port | *needs filter context*: `HASONEVALUE` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Seasonally adjusted sales | Doesn't port | *needs filter context*: `HASONEVALUE` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Seasonal factor | Doesn't port | *needs filter context*: Depends on `not_adjusted_sales`, which doesn't port. |
| Kinds in total | Ports as SQL | `COUNT(DISTINCT kind_key) FILTER (WHERE include_in_total = TRUE AND cell_status = 'Published')` |
| Suppressed cells | Ports as SQL | `COUNT(*) FILTER (WHERE cell_status = 'Suppressed')` |
| Not available cells | Ports as SQL | `COUNT(*) FILTER (WHERE cell_status = 'Not available')` |
| Preliminary sales | Doesn't port | *needs filter context*: Depends on `sales`, which doesn't port. |
| Months in scope | Ports as SQL | `COUNT(DISTINCT date)` |
| Last Data Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |

**Count:** 24 measures. 4 port as SQL, 0 port with changes, 20 don't port (4 of 24 ported).

Why the rest don't port: needs filter context (15); time intelligence (5).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
