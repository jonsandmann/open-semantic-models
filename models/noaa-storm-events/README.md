# NOAA Storm Events

A star-schema semantic model of NOAA's Storm Events Database: every county or zone segment of a US storm that NOAA
logged, with its damage, deaths and injuries, its tornado rating, and, apart from those, the fatalities file (who
died, when, where). Built for loss questions: what weather cost, where, and when.

## Source

- **Publisher:** NOAA National Centers for Environmental Information (NCEI),
  [Storm Events Database](https://www.ncdc.noaa.gov/stormevents/), bulk CSV directory
  [`/pub/data/swdi/stormevents/csvfiles/`](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
  (field definitions in `Storm-Data-Bulk-csv-Format.pdf` in that directory).
- **Files:** `StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz` (one row per event) and
  `StormEvents_fatalities-…` (one row per person), where `d` is the data year (the year the event began) and `c` the
  day NOAA built the file. Loaded by default: data years 2024 and 2025, vintage `c20261119`. The 2025 copies checked
  here are in `samples/` (download from the source; not committed) (details 15.6 MB, gitignored as over 10 MB; fatalities 11 KB, committed).
- **Licence:** public domain in the United States (a work of the US government, 17 USC 105). No key, no login.
- **Citation:** NOAA National Centers for Environmental Information, Storm Events Database, bulk CSV vintage
  c20261119, accessed 24 Nov 2026, https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/. The model carries
  it as the `Citation` measure (with the vintage loaded) and a model annotation.
- **Refreshed by:** Power Query M in the model, straight from ncei.noaa.gov, anonymous. It lists the directory and
  keeps **one file per table and data year, the greatest `c`**: NOAA leaves superseded vintages in the index (2025
  has `c20260819` and `c20261119` today; 2024 has three), and reading them all would count a year two or three times.
- **Not loaded:** the locations file (several points per event; joining it and summing damage multiplies the loss),
  narratives, azimuths and coordinates.

### Field caveats

- **Blank damage is unknown, not zero.** 16,389 of 73,505 property cells in 2025 are blank. Sums leave them out;
  `Blank property cells` counts them; `Damage per event` divides by every event, blank or not (say so on a visual).
- **Damage is text with a suffix** (`1.00K`, `2.50M`, `1.60B`); M multiplies it out. One 2025 Missouri tornado (event
  1262207, 16 May 2025) is 1.6 billion dollars of property damage, a third of the year: one event swings any YoY.
- **Two death counts that disagree.** The event rows say 926 deaths in 2025 (645 direct, 281 indirect); the
  fatalities file has 932 people (649 direct, 283 indirect). The model keeps them in separate measures and never adds
  them.
- **County and zone are both events.** NOAA files some events against counties (`C`) and some against forecast zones
  (`Z`); a zone is not the sum of its counties, so there is no rollup between them.
- **Magnitude's unit depends on the type** (hail in inches, wind in knots); `Average magnitude` is blank across types.
- **Dates are the event's local standard time,** built from `BEGIN_YEARMONTH` + `BEGIN_DAY` (not the two-digit year
  in `BEGIN_DATE_TIME`).

## Grain and size

- `Fact Event`: one row per **event id** (a county or zone segment of a storm). 2025: 73,505 events in 9,932 episodes
  (storm systems); 2024: 69,802. 143,307 rows loaded.
- `Fact Fatality`: one row per **fatality id** (a person). 2025: 932; 2024: 1,142. 2,074 rows loaded.

## Star schema

```
State (68)            1 --* Fact Event *-- 1  Event Type (48 in 2025, 7 groups)
Area Type (3)         1 --* Fact Event *-- 1  Tornado Scale (EF0-EF5, EFU, None)
Date (begin)          1 --* Fact Event *-- 1  End Date
                            Fact Event 1 --* Fact Fatality *-- 1  Fatality Date
                                             Fact Fatality *-- 1  Fatality Profile (type x location x sex)
```

Every relationship is many-to-one, single direction. Fact Fatality -> Fact Event lets an event's state, type and
begin date filter fatalities; fatalities never filter events back.

### Three dates, three date tables (role-playing)

Each fact date has one meaning and its own marked date table, all loaded from one shared `Calendar` query:

| Date table | Related to | Means | Use it for |
|---|---|---|---|
| **Date** | `Fact Event[Begin Date]` | The day the event began | "Storms in May", every event, damage and death measure, YTD and prior year |
| **End Date** | `Fact Event[End Date]` | The day the event ended | Events by when they ended; does not move the YTD or prior-year measures |
| **Fatality Date** | `Fact Fatality[Fatality Date]` | The day the person died | Fatality records by date of death |

No inactive relationships and no second link onto Date. A Date slicer also reaches fatalities through their event
(by the event's begin date), so it and Fatality Date can differ: one 2025 death belongs to an event that began in
December 2024, so 2025 by Date gives 931 fatality records and 2025 by Fatality Date gives 932. A page that should
share one slicer syncs the date tables in the report.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Event | 143,307 | Event ID (hidden) | measures only |
| Fact Fatality | 2,074 | none (all columns hidden) | measures only |
| State | 68 | State | State, State FIPS, Geography Kind (State, Territory, Marine) |
| Event Type | one per type loaded | Event Type | Event Type, Event Group (Convective, Flood, Winter, Tropical, Heat and drought, Wind, Other) |
| Area Type | 3 | CZ Type (hidden) | Area Type (County, Zone, Marine zone) |
| Tornado Scale | one per rating loaded | Tornado Scale | Tornado Scale, Scale Number |
| Fatality Profile | one per combination | Profile Key (hidden) | Fatality Type, Fatality Location, Sex |
| Date, End Date, Fatality Date | one per day, 1 Jan FirstYear to 31 Dec LastYear | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `StormEventsBaseUrl` | `https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` | The one Web data source (answers 200); files are `RelativePath`s |
| `FirstYear`, `LastYear` | 2024, 2025 | Data years to load; the date tables span the same whole years. Widen for history (about 70K events a year since 2010; 1950 onward exists) |
| `LatestFiles` | shared, not loaded | The index parsed to one file per table and data year, greatest `c` |
| `StormDetails`, `StormFatalities` | shared, not loaded | The parsed files; feed the facts and the dimensions built from them |
| `Calendar` | shared, not loaded | The one calendar the three date tables load |

No incremental refresh: two years are about 31 MB compressed; a full refresh took 20 s on an F2.

## Measures (31)

| Folder | Measures |
|---|---|
| Volume | Events, Episodes, States in scope |
| Loss | Property damage, Crop damage, Total damage, Events with property damage, Damage per event |
| Deaths | Deaths, Direct deaths, Indirect deaths, Injuries, Events with a death |
| Fatality file | Fatality records, Direct fatality records, Indirect fatality records, Median age at death |
| Tornado | Tornadoes, EF2 or stronger, Tornado path miles |
| Magnitude | Average magnitude |
| Time | Events YTD, Property damage YTD, Events prior year, Events YoY %, Property damage prior year, Property damage YoY % |
| Audit | Blank property cells, File vintage, Last Begin Date (hidden) |
| About | Citation |

Notes on the logic:

- **No double counting.** Event measures sum event rows only; episodes are a distinct count, never a sum; the
  fatality file is counted with `COUNTROWS` and never added to `Deaths`; the locations file is not loaded.
- **`Total damage` and `Deaths`/`Injuries` add two columns row by row with `COALESCE`,** so an event with one blank
  cell still contributes the other.
- **Tornado measures keep the event-type filter** (`KEEPFILTERS`): a Hail row shows blank for `Tornadoes`, a card shows
  the tornado count. `EF2 or stronger` reads `Scale Number >= 2`; EFU is unrated and not counted.
- **Time follows the event's begin date** (Date) only. `Events YTD` is blank for a period that starts after the last
  begin date; prior year shifts only the days up to the last begin date, so a year in progress compares like with
  like.

## Ten business questions (acceptance checks)

Data year 2025, vintage c20261119. Expected answers are from Grok's design (`design/noaa-storm-events.md`), recomputed
independently from the raw gzip CSVs with Python (`csv` + `Decimal`) before deploying; `tests/checks.dax` asks each
one of the deployed model, filtered on Date (begin) year 2025 unless the question says otherwise.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | Storm events logged in 2025 | 73,505 | 73,505 | Pass |
| 2 | Episodes (storm systems) | 9,932 | 9,932 | Pass |
| 3 | Property damage | $4,631,120,360 | $4,631,120,360 | Pass |
| 4 | Crop damage; total damage | $273,029,900; $4,904,150,260 | identical | Pass |
| 5 | Deaths on event rows vs the fatality file | 926 (645 + 281); file 932 (649 + 283) by fatality date | identical | Pass |
| 6 | Tornadoes; EF5 | 1,644; 1 | 1,644; 1 (EF2 or stronger 234) | Pass |
| 7 | Deaths on tornado event rows | 65 | 65 | Pass |
| 8 | State with the largest total damage | Missouri $1,791,939,000 (property $1,791,384,000, crop $555,000) on 2,840 events | identical; Washington next ($544,577,900) | Pass |
| 9 | Property damage, events that began in May 2025 | $1,773,718,960 | $1,773,718,960 (9,361 events) | Pass |
| 10 | Texas tornadoes and their property damage; hail events | 143, $16,062,500; hail 9,238; average magnitude blank for hail + tornado | identical; hail alone 1.30 in | Pass |

Also checked: 2025 vs 2024 (69,802 events, prior year +5.3%; property $15,741,503,630 in 2024, YoY -70.6%); YTD May
2025 37,353; May 2025 prior year 11,183 (May 2024); 2025 injuries 1,370, events with a death 507, events with
property damage 14,857, blank property cells 16,389; median age at death 54.5; zero orphan keys on every
relationship (every 2025 fatality finds its event once 2024 is loaded); all 31 measures evaluate.

## Changes from the design (`design/noaa-storm-events.md`)

- **The file-name parser.** The design read the data year after the first `_d`, which is the `_d` of `_details`
  (the first refresh failed: `etai` is not a number). It now reads after `_v1.0_d`, and the creation date after the
  last `_c`.
- **Years are parameters** (`FirstYear`/`LastYear`, 2024 to 2025) instead of every year in the index (1950 onward,
  about 1.5 GB of CSV), and the calendar covers those whole years instead of 1950 on.
- **2024 is loaded** so prior year and YoY have something to compare; the ten answers filter to 2025.
- **Dates from `BEGIN_YEARMONTH` + `BEGIN_DAY`**, not `BEGIN_DATE_TIME` (two-digit year).
- **Fact columns are hidden, so the sliceable fields are dimensions:** `Area Type` (County/Zone), `Tornado Scale`
  (with `Scale Number`), and `Fatality Profile` (type, location, sex in one junk dimension) instead of visible fact
  columns.
- **`Tornadoes` and `Tornado path miles` keep the event-type filter** (`KEEPFILTERS`) instead of overriding it: in a
  matrix by event type the design's version showed 1,644 on every row.
- **`Average magnitude` checks the distinct event types in the fact rows in context**, not `HASONEVALUE` on the
  dimension, so an Event Group or state filter that leaves only hail still answers.
- **Event Group has a seventh group, Wind** (High Wind, Strong Wind and their marine forms), rather than putting
  non-convective wind in Other. Other holds 7 types (fog, surf, rip current, sneaker wave, low tide, tsunami).
- **YTD guard and prior year follow the repo's convention** (blank for a period starting after the data; prior year
  over the same days that have data), not the design's "blank when the filter runs past the last date", which would
  blank a year still in progress.
- **Added:** `Indirect deaths`, `Indirect fatality records`, `Median age at death`, `Events YoY %`, `File vintage`,
  `Citation`. Damage and magnitudes are fixed decimal; deaths, injuries and width are whole numbers.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/noaa-storm-events/NoaaStormEvents.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except two deliberate warnings:

| Rule | Status |
|---|---|
| Descriptions on every table, column, measure and expression | Pass |
| Format strings; `%` formats on percentages; visible measures in display folders | Pass |
| `summarizeBy: none` on numeric columns; implicit measures discouraged | Pass |
| Foreign keys hidden; keys `isKey`; month, year-month and group labels sorted | Pass |
| Three marked date tables; auto date/time off | Pass |
| Many-to-one, single-direction relationships on matching types; no islands | Pass |
| Fixed decimal (no floating point); fact columns hidden | Pass |
| DIVIDE, no IFERROR, column/measure reference style, every reference resolves | Pass |
| PRF3 incremental refresh on the facts | **Warn, deliberate**: two yearly files, partitioned by nothing useful |
| PRF4 `isAvailableInMdx` off on `Fact Event[Event ID]` | **Warn, deliberate**: it is the key Fact Fatality relates to |

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in 20 s** (after the file-name fix), 10/10, every measure evaluates.
Details in the [run log](../../docs/toolchain.md#run-log).
