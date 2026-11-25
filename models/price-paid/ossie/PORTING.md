# HM Land Registry Price Paid: porting the TMDL model to Apache Ossie

Spec: Apache Ossie Core Metadata Specification, schema `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**, fetched **25 Nov 2026**. The only dialect the spec defines is **OSSIE_SQL_2026**, written in the `sql` key; any other dialect is carried and not interpreted.

Twin: [`price-paid.ossie.yaml`](price-paid.ossie.yaml). Source model (unchanged): [`PricePaid.SemanticModel`](../PricePaid.SemanticModel/).

The fact loads from HM Land Registry's monthly update file through Power Query; no address fields are loaded. The
twin uses logical source names (`price_paid.<table>`). Market measures count standard-price sales only
(category A, not deleted), a flag on the fact, so they port with `FILTER (WHERE is_standard_sale = TRUE)`.

## Tables

Every table becomes a dataset with its columns as fields. Hidden flags, format strings, sort-by columns and data categories have no portable Ossie property; they are kept in `power_bi` extensions on each field.

| TMDL table | Ossie dataset | Verdict |
| --- | --- | --- |
| Build | `build` | Survives: 2 fields, primary key from the TMDL key column. |
| Category | `category` | Survives: 3 fields, primary key from the TMDL key column. |
| Date | `date` | Survives: 12 fields, primary key from the TMDL key column. The Power BI date-table role does not survive; `is_time` is only a hint to consumers. |
| Duration | `duration` | Survives: 3 fields, primary key from the TMDL key column. |
| Fact Sale | `fact_sale` | Survives: 10 fields. |
| Location | `location` | Survives: 4 fields, primary key from the TMDL key column. |
| Property Type | `property_type` | Survives: 3 fields, primary key from the TMDL key column. |
| Record Status | `record_status` | Survives: 2 fields, primary key from the TMDL key column. |

## Relationships

Ossie relationships are many-to-one joins with no active flag and no cross-filter direction.

| TMDL relationship | Columns | Ossie | Verdict |
| --- | --- | --- | --- |
| Fact Sale to Date | Fact Sale[Transfer Date] to Date[Date] | `fact_sale_to_date` | As-is |
| Fact Sale to Location | Fact Sale[Location Key] to Location[Location Key] | `fact_sale_to_location` | As-is |
| Fact Sale to Property Type | Fact Sale[Property Type Code] to Property Type[Property Type Code] | `fact_sale_to_property_type` | As-is |
| Fact Sale to Duration | Fact Sale[Duration Code] to Duration[Duration Code] | `fact_sale_to_duration` | As-is |
| Fact Sale to Build | Fact Sale[Build] to Build[Build] | `fact_sale_to_build` | As-is |
| Fact Sale to Category | Fact Sale[Category] to Category[Category] | `fact_sale_to_category` | As-is |
| Fact Sale to Record Status | Fact Sale[Record Status] to Record Status[Record Status] | `fact_sale_to_record_status` | As-is |

## Measures

**Ports as SQL**: the metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under ordinary filters on the same columns. **Ports with changes**: it has a SQL expression, but the result differs from the DAX in a stated case. **Doesn't port**: the DAX is carried as an opaque `DAX` dialect entry only, with the reason; nothing is faked as SQL. Every measure keeps its DAX, format string and folder in a `power_bi` extension. Two DAX blank rules are written into the SQL: a count of no rows is blank in DAX and 0 in SQL, so every count measure is `NULLIF(COUNT(...), 0)` (including a count whose filter matches nothing in a non-empty group); and DAX compares a blank as 0, so a filter that 0 passes (`= 0`, `< 250000`) is written on `COALESCE(column, 0)`.

| Measure | Verdict | Ossie SQL, or why not |
| --- | --- | --- |
| Sales | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE is_standard_sale = TRUE), 0)` |
| All records | Ports as SQL | `NULLIF(COUNT(*), 0)` |
| Deleted records | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE record_status = 'Deleted'), 0)` |
| Additional transfers | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE category = 'Additional' AND record_status <> 'Deleted'), 0)` |
| Median price | Ports as SQL | `MEDIAN(price_gbp) FILTER (WHERE is_standard_sale = TRUE)` |
| Mean price | Ports as SQL | `AVG(price_gbp) FILTER (WHERE is_standard_sale = TRUE)` |
| Total consideration | Ports as SQL | `SUM(price_gbp) FILTER (WHERE is_standard_sale = TRUE)` |
| Lowest price | Ports as SQL | `MIN(price_gbp) FILTER (WHERE is_standard_sale = TRUE)` |
| Highest price | Ports as SQL | `MAX(price_gbp) FILTER (WHERE is_standard_sale = TRUE)` |
| Share of sales | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Freehold share | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE duration_code = 'F' AND is_standard_sale = TRUE), 0) / NULLIF(COUNT(*) FILTER (WHERE is_standard_sale = TRUE), 0)` |
| New build sales | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE build = 'New build' AND is_standard_sale = TRUE), 0)` |
| Sales under £250,000 | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE COALESCE(price_gbp, 0) < 250000 AND is_standard_sale = TRUE), 0)` |
| Sales of £1 million or more | Ports as SQL | `NULLIF(COUNT(*) FILTER (WHERE price_gbp >= 1000000 AND is_standard_sale = TRUE), 0)` |
| Share of consideration | Doesn't port | *needs filter context*: `REMOVEFILTERS` reads or removes what the report has filtered. OSSIE_SQL_2026 metrics have no filter context: no ALL, REMOVEFILTERS, ISFILTERED or HASONEVALUE. |
| Sales prior month | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Median price prior month | Doesn't port | *time intelligence*: `DATEADD` shifts or accumulates dates through the Power BI date table. OSSIE_SQL_2026 has no time-intelligence functions, and a metric can't move the query's date filter. |
| Median price change | Doesn't port | *time intelligence*: Depends on `median_price_prior_month`, which doesn't port. |
| Attribution | Doesn't port | *text, not a number*: a citation or attribution string. Kept in the DAX dialect for reports; there is nothing to aggregate. |

**Count:** 19 measures. 13 port as SQL, 0 port with changes, 6 don't port (13 of 19 ported).

Why the rest don't port: time intelligence (3); needs filter context (2); text, not a number (1).

## What was validated

`python3 tools/ossie-check/check.py` validates the YAML against `ossie-schema.json` 0.3.0.dev0 (JSON Schema 2020-12; `additionalProperties: false` is in force, so a stray key fails) and checks names: unique datasets, fields and dataset metrics sharing one namespace per dataset, unique model metrics, relationship datasets and columns that exist, primary keys that name fields. It does not parse the SQL as OSSIE_SQL_2026 (the grammar is published, no parser is), and no Ossie engine ran these metrics. The TMDL model was not modified.
