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

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. One difference holds for every ported count: on an empty group DAX returns blank and SQL `COUNT` returns 0.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Revenue | Ports as SQL | `SUM(revenue_amount_usd)` |
| Sales kWh | Ports as SQL | `SUM(sales_amount_kwh)` |
| Sales MWh | Ports as SQL | `SUM(sales_amount_kwh) / 1000` |
| Customers | Doesn't port | *semi-additive*: a monthly snapshot of accounts. It adds across states and sectors and keeps only the last month in the filters; `SUM(customer_count)` would count the same account every month. |
| Price cents per kWh | Ports as SQL | `(SUM(revenue_amount_usd) / NULLIF(SUM(sales_amount_kwh), 0)) * 100` |
| Average customers | Doesn't port | *two-level aggregation*: sum within each month, then average across months. Two-level aggregation, not one aggregate over the row grain. |
| Revenue per customer | Doesn't port | *two-level aggregation*: Depends on `average_customers`, which doesn't port. |
| Sales per customer kWh | Doesn't port | *two-level aggregation*: Depends on `average_customers`, which doesn't port. |
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
| Months in scope | Ports as SQL | `COUNT(DISTINCT date)` |
| Preliminary months | Ports as SQL | `COUNT(DISTINCT date) FILTER (WHERE data_status = 'Preliminary')` |
| Last Data Date | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |

**Count:** 22 measures. 6 port as SQL, 0 port with changes, 16 don't port (6 of 22 ported).

Why the rest don't port: time intelligence (8); two-level aggregation (3); needs filter context (3); semi-additive (2).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
