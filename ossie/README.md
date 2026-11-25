# Ossie twins

Every model in this repo also has an [Apache Ossie](https://github.com/apache/ossie) twin: the same tables,
relationships and measures written as one YAML document in the Ossie Core Metadata Specification, so a tool that
reads Ossie (rather than TMDL) can use the model's definitions. Each twin sits next to its model in
`models/<name>/ossie/`, with a `PORTING.md` that gives a verdict for every table, relationship and measure.

Spec: `core-spec/ossie-schema.json` on `apache/ossie` `main` (commit `7b8ed65`), version const **0.3.0.dev0**,
fetched **25 Nov 2026**. The portable expression language is **OSSIE_SQL_2026**. The spec is pre-release and
moving; a later schema version may need the twins regenerated.

## How a measure is judged

- **Ports as SQL**: the Ossie metric has an OSSIE_SQL_2026 expression that returns the DAX measure's number under
  ordinary filters on the same columns. Filters written with `KEEPFILTERS` port as `FILTER (WHERE ...)`, and a
  filter on a dimension key becomes a filter on the fact's foreign key.
- **Ports with changes**: a SQL expression exists but differs from the DAX in a stated case. None of the 237
  measures needed this verdict: each one either matched or didn't port.
- **Doesn't port**: the DAX is kept as an opaque `DAX` dialect entry with the reason. No measure is faked as SQL.

Every measure, ported or not, keeps its DAX, format string and display folder in a `power_bi` extension, and every
field keeps its hidden flag, format string and sort-by column the same way.

## Models

| Model | Twin | Tables | Relationships | Measures ported | Main reasons the rest don't port |
| --- | --- | --- | --- | --- | --- |
| [Building Permits](../models/building-permits/ossie/PORTING.md) | [`building-permits.ossie.yaml`](../models/building-permits/ossie/building-permits.ossie.yaml) | 9 | 8 | 10 of 17 | time intelligence 4, needs filter context 1 |
| [Census Monthly Retail Trade](../models/census-retail/ossie/PORTING.md) | [`census-retail.ossie.yaml`](../models/census-retail/ossie/census-retail.ossie.yaml) | 4 | 3 | 4 of 24 | needs filter context 15, time intelligence 5 |
| [CMS Hospital Quality](../models/cms-hospital-quality/ossie/PORTING.md) | [`cms-hospital-quality.ossie.yaml`](../models/cms-hospital-quality/ossie/cms-hospital-quality.ossie.yaml) | 6 | 7 | 4 of 28 | semi-additive 22, needs filter context 2 |
| [EIA Electricity Retail Sales](../models/eia-electricity/ossie/PORTING.md) | [`eia-electricity.ossie.yaml`](../models/eia-electricity/ossie/eia-electricity.ossie.yaml) | 4 | 3 | 6 of 22 | time intelligence 8, two-level aggregation 3 |
| [NASA FIRMS Active Fires](../models/nasa-firms/ossie/PORTING.md) | [`nasa-firms.ossie.yaml`](../models/nasa-firms/ossie/nasa-firms.ossie.yaml) | 8 | 7 | 1 of 23 | needs filter context 15, time intelligence 3 |
| [NOAA Storm Events](../models/noaa-storm-events/ossie/PORTING.md) | [`noaa-storm-events.ossie.yaml`](../models/noaa-storm-events/ossie/noaa-storm-events.ossie.yaml) | 10 | 9 | 18 of 31 | time intelligence 6, filter on a dimension attribute 3 |
| [NYC Taxi Trips](../models/nyc-taxi/ossie/PORTING.md) | [`nyc-taxi.ossie.yaml`](../models/nyc-taxi/ossie/nyc-taxi.ossie.yaml) | 8 | 7 | 27 of 42 | time intelligence 14, needs filter context 1 |
| [HM Land Registry Price Paid](../models/price-paid/ossie/PORTING.md) | [`price-paid.ossie.yaml`](../models/price-paid/ossie/price-paid.ossie.yaml) | 8 | 7 | 13 of 19 | time intelligence 3, needs filter context 2 |
| [Restaurant Inspections](../models/restaurant-inspections/ossie/PORTING.md) | [`restaurant-inspections.ossie.yaml`](../models/restaurant-inspections/ossie/restaurant-inspections.ossie.yaml) | 12 | 11 | 9 of 31 | filter on a dimension attribute 15, time intelligence 4 |

**Total: 92 of 237 measures port** (39%). Every table and every active relationship ports; the one
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

Also seen: filters on a dimension attribute that the fact doesn't carry (19; Ossie's
`FILTER (WHERE ...)` may only reference the aggregate's own dataset), citation and attribution text measures
(6), and two-level aggregations such as an average of monthly sums or a peak day
(5).

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
