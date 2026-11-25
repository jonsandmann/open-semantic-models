# Ossie twins

The first nine models in this repo also have an [Apache Ossie](https://github.com/apache/ossie) twin: the same tables,
relationships and measures written as one YAML document in the Ossie Core Metadata Specification, so a tool that
reads Ossie (rather than TMDL) can use the model's definitions. Each twin sits next to its model in
`models/<name>/ossie/`, with a `PORTING.md` that gives a verdict for every table, relationship and measure.

Spec: `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**,
fetched **25 Nov 2026**. The portable expression language is **OSSIE_SQL_2026**. The spec is pre-release and
moving; a later schema version may need the twins regenerated.

The verdicts were corrected after an independent red-team review against the TMDL and the spec: three ported
expressions didn't return the DAX number on blank rows, and eleven measures marked "doesn't port" had a fact
column that already says what the dimension filter says.

## How a measure is judged

- **Ports as SQL**: the Ossie metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under
  ordinary filters on the same columns, blanks included. Filters written with `KEEPFILTERS` port as
  `FILTER (WHERE ...)`; a filter on a dimension key becomes a filter on the fact's foreign key, and a filter on a
  dimension attribute ports when the dimension's own M makes it a function of a fact column (for example the
  jurisdictions that publish violations, or the category keys whose work class is `new`). Two DAX blank rules are
  written into the SQL rather than left as a difference: a count of no rows is blank in DAX and 0 in SQL, so every
  count measure is `NULLIF(COUNT(...), 0)`, which also covers a non-empty group whose filter matches nothing; and
  DAX compares a blank as 0, so a filter that 0 passes is written on `COALESCE(column, 0)`, and a sum of SUMs adds
  a blank SUM as 0.
- **Ports with changes**: a SQL expression exists but differs from the DAX in a stated case. No measure has this
  verdict now: every blank-versus-0 difference found was written into the SQL instead.
- **Doesn't port**: the DAX is kept as an opaque `DAX` dialect entry with the reason. No measure is faked as SQL.

Every measure, ported or not, keeps its DAX, format string and display folder in a `power_bi` extension, and every
field keeps its hidden flag, format string and sort-by column the same way.

## Models

| Model | Twin | Tables | Relationships | Measures ported | Main reasons the rest don't port |
| --- | --- | --- | --- | --- | --- |
| [Building Permits](../models/building-permits/ossie/PORTING.md) | [`building-permits.ossie.yaml`](../models/building-permits/ossie/building-permits.ossie.yaml) | 9 | 8 | 11 of 17 | time intelligence 4, needs filter context 1 |
| [Census Monthly Retail Trade](../models/census-retail/ossie/PORTING.md) | [`census-retail.ossie.yaml`](../models/census-retail/ossie/census-retail.ossie.yaml) | 4 | 3 | 4 of 24 | needs filter context 15, time intelligence 5 |
| [CMS Hospital Quality](../models/cms-hospital-quality/ossie/PORTING.md) | [`cms-hospital-quality.ossie.yaml`](../models/cms-hospital-quality/ossie/cms-hospital-quality.ossie.yaml) | 6 | 7 | 4 of 28 | semi-additive 22, needs filter context 2 |
| [EIA Electricity Retail Sales](../models/eia-electricity/ossie/PORTING.md) | [`eia-electricity.ossie.yaml`](../models/eia-electricity/ossie/eia-electricity.ossie.yaml) | 4 | 3 | 9 of 22 | time intelligence 8, needs filter context 3 |
| [NASA FIRMS Active Fires](../models/nasa-firms/ossie/PORTING.md) | [`nasa-firms.ossie.yaml`](../models/nasa-firms/ossie/nasa-firms.ossie.yaml) | 8 | 7 | 1 of 23 | needs filter context 15, time intelligence 3 |
| [NOAA Storm Events](../models/noaa-storm-events/ossie/PORTING.md) | [`noaa-storm-events.ossie.yaml`](../models/noaa-storm-events/ossie/noaa-storm-events.ossie.yaml) | 10 | 9 | 21 of 31 | time intelligence 6, needs filter context 3 |
| [NYC Taxi Trips](../models/nyc-taxi/ossie/PORTING.md) | [`nyc-taxi.ossie.yaml`](../models/nyc-taxi/ossie/nyc-taxi.ossie.yaml) | 8 | 7 | 27 of 42 | time intelligence 14, needs filter context 1 |
| [HM Land Registry Price Paid](../models/price-paid/ossie/PORTING.md) | [`price-paid.ossie.yaml`](../models/price-paid/ossie/price-paid.ossie.yaml) | 8 | 7 | 13 of 19 | time intelligence 3, needs filter context 2 |
| [Restaurant Inspections](../models/restaurant-inspections/ossie/PORTING.md) | [`restaurant-inspections.ossie.yaml`](../models/restaurant-inspections/ossie/restaurant-inspections.ossie.yaml) | 12 | 11 | 13 of 31 | filter on a dimension attribute 6, divides measures of two facts 5 |

**Total: 103 of 237 measures port** (43%). Every table and every active relationship ports; the one
inactive relationship (CMS Hospital Quality, window start date) is left out, because Ossie has no inactive flag and
a second path between the same two datasets would make joins ambiguous.

## Why measures don't port

The three most common reasons, across all nine models:

1. **Time intelligence** (47 measures). Year-to-date, prior-year, prior-month and year-over-year
   measures move the date filter through the Power BI date table (`TOTALYTD`, `SAMEPERIODLASTYEAR`, `DATEADD`).
   OSSIE_SQL_2026 has no time-intelligence functions and a metric can't shift the query's date range.
2. **Needs filter context** (44 measures). Shares of a total, defaults that apply only when nothing is
   picked, and guards that blank a number unless one value is selected read what the report has filtered (`ALL`,
   `REMOVEFILTERS`, `ISFILTERED`, `HASONEVALUE`). An Ossie metric has no filter context to read.
3. **Semi-additive** (24 measures). Snapshots (customer accounts per month, hospital results per
   CMS release) keep only the latest date inside the filters, so a plain `SUM` would count the same thing once per
   period. One aggregate can't pin itself to the max date of its own rows without a subquery.

Also seen: filter on a dimension attribute (6 measures) that no fact column determines (restaurant outcome tier and
closure flag; Ossie's `FILTER (WHERE ...)` may only reference the aggregate's own dataset),
text, not a number (6 measures) for citations and attribution, divides measures of two facts (5 measures) (restaurant violations
per inspection), and two-level aggregation (2 measures): NASA's peak day and peak-day detections, a rank over a
grain. An average of monthly sums is not on that list: it is one ratio (the sum over the months that have a
value) and ports.

## Validating

```sh
python3 -m venv /tmp/ossie-venv && /tmp/ossie-venv/bin/pip install pyyaml jsonschema
curl -sLo /tmp/ossie-schema.json https://raw.githubusercontent.com/apache/ossie/main/core-spec/ossie-schema.json
/tmp/ossie-venv/bin/python tools/ossie-check/check.py --schema /tmp/ossie-schema.json models/*/ossie/*.ossie.yaml
```

`tools/ossie-check/check.py` validates each twin against the JSON schema (2020-12) and checks the naming rules the
schema can't express: unique names, fields and metrics sharing one namespace per dataset, relationship columns and
primary keys that exist. It does not parse the SQL as OSSIE_SQL_2026, and no Ossie engine has run these metrics.
Sources are logical names (`<model>.<table>`), not warehouse tables: the Power BI models load through Power Query.
