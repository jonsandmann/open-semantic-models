# EIA Electricity Retail Sales: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`eia-electricity.ossie.yaml`](eia-electricity.ossie.yaml). Source model (unchanged): [`EiaElectricity.SemanticModel`](../EiaElectricity.SemanticModel/).

The fact rows come from EIA `sales_revenue.xlsx` through Power Query; Date, State and Sector are generated or
typed in M. The twin uses logical source names (`eia_electricity.<table>`), not warehouse tables.
Filters written with `KEEPFILTERS` port exactly: `FILTER (WHERE ...)` intersects with an outer filter on the
same column, as `KEEPFILTERS` does.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Date | `date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Fact Retail Sales | `fact_retail_sales` | Survives: 7 fields. |
| Sector | `sector` | Survives: 2 fields, primary key from the TMDL key column. |
| State | `state` | Survives: 4 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Retail Sales to Date | Fact Retail Sales[Date] to Date[Date] | `fact_retail_sales_to_date` | As-is |
| Fact Retail Sales to State | Fact Retail Sales[State Code] to State[State Code] | `fact_retail_sales_to_state` | As-is |
| Fact Retail Sales to Sector | Fact Retail Sales[Sector] to Sector[Sector] | `fact_retail_sales_to_sector` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Revenue | Ports as SQL | `SUM(revenue_amount_usd)` |
| Sales kWh | Ports as SQL | `SUM(sales_amount_kwh)` |
| Sales MWh | Ports as SQL | `SUM(sales_amount_kwh) / 1000` |
| Customers | Doesn't port | *semi-additive*: a monthly snapshot of accounts. It adds across states and sectors and keeps only the last month in the filters; `SUM(customer_count)` would count the same account every month. |
| Price cents per kWh | Ports as SQL | `(SUM(revenue_amount_usd) / NULLIF(SUM(sales_amount_kwh), 0)) * 100` |
| Average customers | Ports as SQL | `SUM(customer_count) / NULLIF(COUNT(DISTINCT date) FILTER (WHERE customer_count IS NOT NULL), 0)`. `AVERAGEX` over months of each month's sum skips months whose sum is blank, so it is the sum of all months over the months that have a customer count. |
| Revenue per customer | Ports as SQL | `SUM(revenue_amount_usd) * COUNT(DISTINCT date) FILTER (WHERE customer_count IS NOT NULL) / NULLIF(SUM(customer_count), 0)`. Revenue over Average customers, with Average customers written out as above. |
| Sales per customer kWh | Ports as SQL | `SUM(sales_amount_kwh) * COUNT(DISTINCT date) FILTER (WHERE customer_count IS NOT NULL) / NULLIF(SUM(customer_count), 0)`. Sales over Average customers, with Average customers written out as above. |
| Share of US sales | Doesn't port | *needs filter context*: `ALL` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Share of state sales | Doesn't port | *needs filter context*: `ALL` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Sales YTD kWh | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Revenue YTD | Doesn't port | *time intelligence*: `TOTALYTD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Sales prior year kWh | Doesn't port | *time intelligence*: `EOMONTH` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Revenue prior year | Doesn't port | *time intelligence*: `EOMONTH` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Price prior year cents per kWh | Doesn't port | *time intelligence*: `EOMONTH` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Sales YoY % | Doesn't port | *time intelligence*: Depends on `sales_prior_year_kwh`, which doesn't port. |
| Revenue YoY % | Doesn't port | *time intelligence*: Depends on `revenue_prior_year`, which doesn't port. |
| Price YoY cents | Doesn't port | *time intelligence*: Depends on `price_prior_year_cents_per_kwh`, which doesn't port. |
| Sales latest month kWh | Doesn't port | *semi-additive*: sales in the latest month inside the current filters. Needs the max date of the query's own rows. |
| Months in scope | Ports as SQL | `NULLIF(COUNT(DISTINCT date), 0)` |
| Preliminary months | Ports as SQL | `NULLIF(COUNT(DISTINCT date) FILTER (WHERE data_status = 'Preliminary'), 0)` |
| Last Data Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |

**Count:** 22 measures. 9 port as SQL, 0 port with changes, 13 don't port (9 of 22 ported).

Why the rest don't port: time intelligence (8); needs filter context (3); semi-additive (2).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
