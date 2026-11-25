# NOAA Storm Events

Model #6. Climate and weather, after taxi, electricity, hospitals, retail, and price paid. NOAA National Centers for Environmental Information Storm Events Database, bulk CSV. U.S. government work, public domain. No API key. Downloaded 24 Nov 2026. Every answer was counted from the 2025 files below.

GHCN-Daily is the worse fit. A year of station-days is several gigabytes, the grain is a station observation rather than a loss, and magnitude still cannot be averaged across elements. Storm Events is the loss ledger: one weather event, a place, a begin date, damage, deaths.

## Source

| Item | Value |
|---|---|
| Bulk index | https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/ |
| Format | `Storm-Data-Bulk-csv-Format.pdf` in that directory (11 Mar 2026, 341,218 bytes). File names: `StormEvents_<table>-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz`. `d` is the data year. `c` is the day the file was built. |
| Readme | Same directory, `README` (24 Mar 2026). A new `c` date means the year was replaced. Older `c` files for the same `d` year are left in the index. |
| Sample, details | https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_details-ftp_v1.0_d2025_c20261119.csv.gz |
| Sample size | 15,571,365 bytes. Last-Modified Thu, 19 Nov 2026 17:43 GMT. Saved as `samples/StormEvents_details-ftp_v1.0_d2025_c20261119.csv.gz` (download from the source; not committed). |
| Sample, fatalities | https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/StormEvents_fatalities-ftp_v1.0_d2025_c20261119.csv.gz |
| Fatalities size | 10,943 bytes. Same vintage. Saved beside the details file. |
| Locations file | Same index, `StormEvents_locations-ftp_v1.0_d2025_c20261119.csv.gz`, 1,186,061 bytes. Not in the sample and not loaded. Several points per event. Joining it and summing damage multiplies the loss. |
| What the sample is | Data year 2025, creation date 19 Nov 2026. 73,505 detail rows, 932 fatality rows. Begin dates run 1 Jan 2025 through 31 Dec 2025. The 2026 file on the same index (`d2026_c20261119`, 11,624,261 bytes) is a partial year. Do not treat it as a full year. |

The index also still lists an older 2025 details file, `d2025_c20260819` (12,585,209 bytes, 19 Aug 2026). Loading both vintages double-counts the year. Power Query keeps the greatest `c` date per data year and ignores the rest.

Suggested citation: NOAA National Centers for Environmental Information, Storm Events Database, bulk CSV vintage c20261119, accessed 24 Nov 2026, https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/.

## Grain

**Fact Event.** One row per `EVENT_ID`. In the 2025 file, 73,505 ids, all unique. An episode (`EPISODE_ID`, 9,932 distinct) is the storm system; the event is the county or zone segment. Damage and the death counts sit on the event. Sum event rows. Never sum a copy of those numbers onto locations, and never add an episode total on top.

**Fact Fatality.** One row per `FATALITY_ID` (932 in the 2025 file). This is who died, where, and whether the death was direct. It is not a second copy of damage. Death measures on Fact Event use `DEATHS_DIRECT` and `DEATHS_INDIRECT` only. Death measures on Fact Fatality use `COUNTROWS` only. Do not add the two. They are not equal in this file: event rows sum to 926 deaths (645 direct, 281 indirect); the fatality file has 932 rows (649 direct, 283 indirect).

County (`CZ_TYPE = C`, 42,265) and zone (`Z`, 31,240) are both events. A zone is not the sum of its counties. There is no rollup measure from zone to county.

## Star schema

### Fact Event

| Column | Type | Notes |
|---|---|---|
| Event ID | text | Primary key |
| Episode ID | text | Not a key. `Episodes` is a distinct count |
| Begin Date | date | Date part of `BEGIN_DATE_TIME`. Only relationship to Date |
| End Date | date | Date part of `END_DATE_TIME`. Only relationship to End Date |
| State | text | FK to State. 51 states and DC plus 17 marine areas and territories in this file |
| Event Type | text | FK to Event Type |
| CZ Type | text | `County` or `Zone` |
| CZ Name | text | County or zone name, not a key by itself |
| Property Damage USD | decimal | Parsed from `DAMAGE_PROPERTY`. Null when blank, never zero-filled |
| Crop Damage USD | decimal | Parsed from `DAMAGE_CROPS`. Null when blank |
| Deaths Direct | int | On this fact only |
| Deaths Indirect | int | On this fact only |
| Injuries Direct | int | |
| Injuries Indirect | int | |
| Tornado Scale | text | `TOR_F_SCALE`. Blank except tornadoes |
| Tornado Length Miles | decimal | `TOR_LENGTH`. Blank except tornadoes |
| Tornado Width Yards | decimal | `TOR_WIDTH`. Blank except tornadoes |
| Magnitude | decimal | Meaning depends on event type (hail inches, wind knots). Hidden. Not additive |

Narratives, azimuths, and raw lat/lon stay out. Begin lat/lon is one point, not the locations file.

Damage strings in this file use a trailing `K`, `M`, or `B` (100, 1,000, 1,000,000). 16,389 property cells and 17,126 crop cells are blank.

### Fact Fatality

| Column | Type | Notes |
|---|---|---|
| Fatality ID | text | Primary key |
| Event ID | text | FK to Fact Event, one direction, so fatality filters can reach the event’s state and type. Fact Event does not filter back |
| Fatality Date | date | Only relationship to Fatality Date |
| Fatality Type | text | `Direct` or `Indirect` (`D` / `I`) |
| Fatality Location | text | NOAA place class (vehicle, outside, and so on), not a street |
| Age | int | Null when blank |
| Sex | text | |

No damage columns.

### Date, End Date, Fatality Date

Three copies of one calendar, 1 Jan 1950 through 31 Dec of the latest loaded year. Mark each `dataCategory: Time`. Auto date/time off.

Each fact date has one meaning and one table:

| Fact column | Table | Meaning |
|---|---|---|
| Fact Event[Begin Date] | Date | Day the event began. The slicer for “storms in May” |
| Fact Event[End Date] | End Date | Day the event ended. Not the begin day |
| Fact Fatality[Fatality Date] | Fatality Date | Day the person died. Not the event begin day |

No inactive second relationship back onto Date. A page that should share one slicer syncs the three date tables in the report. The model does not.

### State

`State` (key), `State FIPS` where NOAA sends one, `Geography Kind` (`State`, `Territory`, or `Marine`). Marine names in the 2025 file include `ATLANTIC NORTH`, `GULF OF MEXICO`, and the Great Lakes. They are not counties of a state.

### Event Type

`Event Type` (key), `Event Group` (convective, flood, winter, tropical, heat and drought, other). Group is a label for filtering. It is not a second grain and it is not summed as its own fact. Tornado, hail, and thunderstorm wind stay separate types so magnitudes are never averaged together.

### Relationships

| From | To | Cardinality | Filter |
|---|---|---|---|
| Fact Event[Begin Date] | Date[Date] | many to one | single |
| Fact Event[End Date] | End Date[Date] | many to one | single |
| Fact Event[State] | State[State] | many to one | single |
| Fact Event[Event Type] | Event Type[Event Type] | many to one | single |
| Fact Fatality[Event ID] | Fact Event[Event ID] | many to one | single, fatality filters the event |
| Fact Fatality[Fatality Date] | Fatality Date[Date] | many to one | single |

## Measures

Folder in parentheses. Format after the name. Property and crop are summed with `COALESCE` inside one `SUMX`, because a blank `SUM` plus a number is blank in DAX.

Volume

1. **Events** `#,0` (Volume). `COUNTROWS ( 'Fact Event' )`. One per event id.
2. **Episodes** `#,0` (Volume). `DISTINCTCOUNT ( 'Fact Event'[Episode ID] )`. A storm system. Not the sum of events.
3. **States in scope** `0` (Volume). `DISTINCTCOUNT ( 'Fact Event'[State] )`.

Loss. Blank damage stays out of the sum. It is not a zero that was withheld.

4. **Property damage** `$#,0` (Loss). `SUM ( 'Fact Event'[Property Damage USD] )`.
5. **Crop damage** `$#,0` (Loss). `SUM ( 'Fact Event'[Crop Damage USD] )`.
6. **Total damage** `$#,0` (Loss). `SUMX ( 'Fact Event', COALESCE ( 'Fact Event'[Property Damage USD], 0 ) + COALESCE ( 'Fact Event'[Crop Damage USD], 0 ) )`. Events with both amounts blank add nothing.
7. **Events with property damage** `#,0` (Loss). Count of rows where property damage is not blank and is greater than zero.
8. **Damage per event** `$#,0` (Loss). `DIVIDE ( [Total damage], [Events] )`. This is total reported loss over all events in context, including events with no damage figure. Say that in the description. It is not the mean of the damage column.

Deaths on the event. These do not read Fact Fatality.

9. **Deaths** `#,0` (Deaths). `SUMX ( 'Fact Event', COALESCE ( 'Fact Event'[Deaths Direct], 0 ) + COALESCE ( 'Fact Event'[Deaths Indirect], 0 ) )`.
10. **Direct deaths** `#,0` (Deaths). `SUM ( 'Fact Event'[Deaths Direct] )`.
11. **Injuries** `#,0` (Deaths). Same `SUMX` pattern as Deaths, over the two injury columns.
12. **Events with a death** `#,0` (Deaths). Rows where direct plus indirect is greater than zero.

Deaths on the person file. These do not read the event death columns.

13. **Fatality records** `#,0` (Fatality file). `COUNTROWS ( 'Fact Fatality' )`.
14. **Direct fatality records** `#,0` (Fatality file). `CALCULATE ( [Fatality records], 'Fact Fatality'[Fatality Type] = "Direct" )`.

Tornado. Blank unless the event type in context is Tornado, so a hail row cannot contribute a width.

15. **Tornadoes** `#,0` (Tornado). `CALCULATE ( [Events], 'Event Type'[Event Type] = "Tornado" )`. Ignores a conflicting event-type filter by setting it, so the card stays a tornado count.
16. **EF2 or stronger** `#,0` (Tornado). Tornadoes whose scale is EF2, EF3, EF4, or EF5. EFU is not stronger.
17. **Tornado path miles** `#,0.0` (Tornado). `CALCULATE ( SUM ( 'Fact Event'[Tornado Length Miles] ), 'Event Type'[Event Type] = "Tornado" )`. Sum of segment lengths, not a single track.
18. **Average magnitude** `0.00` (Tornado). `IF ( HASONEVALUE ( 'Event Type'[Event Type] ), AVERAGE ( 'Fact Event'[Magnitude] ) )`. Blank when more than one event type is in context. Hail inches and wind speeds are different units.

Time. The guard blanks the measure when the filter runs past the last begin date in the model, including a year row that still contains later months. Prior year uses `SAMEPERIODLASTYEAR` on Date only (event begin). It does not shift End Date or Fatality Date.

19. **Events YTD** `#,0` (Time). `IF ( MAX ( 'Date'[Date] ) <= [Last Begin Date], TOTALYTD ( [Events], 'Date'[Date] ) )`.
20. **Property damage YTD** `$#,0` (Time). Same guard around `TOTALYTD ( [Property damage], 'Date'[Date] )`.
21. **Events prior year** `#,0` (Time). `CALCULATE ( [Events], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
22. **Property damage YoY %** `+0.0%;-0.0%;0.0%` (Time). `IF ( NOT ISBLANK ( [Property damage] ), DIVIDE ( [Property damage] - [Property damage prior year], [Property damage prior year] ) )`. The prior-year measure is the `SAMEPERIODLASTYEAR` twin of property damage, same folder, hidden if the field list gets crowded. It is measure 23 in the build.

Audit

24. **Last Begin Date** `yyyy-mm-dd` (Audit). `CALCULATE ( MAX ( 'Fact Event'[Begin Date] ), REMOVEFILTERS () )`. Hidden. The YTD guard reads it.
25. **Blank property cells** `#,0` (Audit). Count of event rows whose property damage is blank.

## Power Query M

List the index, keep gzip names, parse `d` and `c`, and keep one file per data year: the max `c`. Do not append every file the index still hosts.

```powerquery
let
    Index = Web.Contents("https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"),
    Page = Text.FromBinary(Index),
    Names = List.Distinct(List.Select(
        Text.SplitAny(Page, " ""<>"),
        each Text.StartsWith(_, "StormEvents_details-ftp_v1.0_d") and Text.EndsWith(_, ".csv.gz"))),
    Parsed = List.Transform(Names, each [
        Name = _,
        Year = Text.Middle(_, Text.PositionOf(_, "_d") + 2, 4),
        Built = Text.Middle(_, Text.PositionOf(_, "_c") + 2, 8)
    ]),
    Latest = Table.Group(Table.FromRecords(Parsed), {"Year"}, {{"Built", each List.Max([Built]), type text}, {"Name", each Table.Max(_, "Built")[Name], type text}}),
    ReadYear = (file as text) as table =>
        let
            Bin = Web.Contents("https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/" & file),
            Csv = Csv.Document(Binary.Decompress(Bin, Compression.GZip), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            Promoted = Table.PromoteHeaders(Csv, [PromoteAllScalars = true])
        in
            Promoted,
    Dollars = (raw as nullable text) as nullable number =>
        let
            t = Text.Upper(Text.Trim(raw)),
            Last = if t = "" then "" else Text.End(t, 1),
            Mult = if Last = "K" then 1000 else if Last = "M" then 1000000 else if Last = "B" then 1000000000 else if Last = "H" then 100 else 1,
            Num = if List.Contains({"K", "M", "B", "H"}, Last) then Text.Start(t, Text.Length(t) - 1) else t
        in
            if t = "" then null else Number.FromText(Num) * Mult,
    Events = Table.Combine(List.Transform(Latest[Name], ReadYear)),
    Kept = Table.SelectColumns(Events, {
        "EVENT_ID", "EPISODE_ID", "BEGIN_DATE_TIME", "END_DATE_TIME", "STATE", "STATE_FIPS",
        "EVENT_TYPE", "CZ_TYPE", "CZ_NAME", "DAMAGE_PROPERTY", "DAMAGE_CROPS",
        "DEATHS_DIRECT", "DEATHS_INDIRECT", "INJURIES_DIRECT", "INJURIES_INDIRECT",
        "TOR_F_SCALE", "TOR_LENGTH", "TOR_WIDTH", "MAGNITUDE"}),
    Typed = Table.TransformColumns(Kept, {
        {"DAMAGE_PROPERTY", Dollars},
        {"DAMAGE_CROPS", Dollars}
    })
in
    Typed
```

Fact Fatality uses the same latest-`c` rule on `StormEvents_fatalities-ftp_v1.0_d`. Map `D` to Direct and `I` to Indirect. Do not select a damage column; the file has none. Leave the locations files unread.

Date, End Date, and Fatality Date are one calendar query referenced three times (`Table.SelectColumns` of a shared `Calendar` expression), not three downloads.

## Questions

Answers are the 2025 vintage `c20261119` only. Property and crop blanks are excluded from sums, not counted as zero.

1. How many storm events did NOAA log in 2025? **73,505.** Event ids are unique.
2. How many episodes is that? **9,932.** Distinct `EPISODE_ID`.
3. What property damage is on those events? **$4,631,120,360.**
4. What crop damage? **$273,029,900.** Total damage, property plus crop with blanks as nothing, is **$4,904,150,260.**
5. How many deaths are on the event rows? **926** (645 direct, 281 indirect). The fatality file has **932** rows (649 direct, 283 indirect). The model does not add 926 and 932.
6. How many tornadoes, and how many were EF5? **1,644** tornadoes, **1** EF5: event 1278899, Ransom County, North Dakota, begin 20 Jun 2025 22:04.
7. How many deaths are on tornado event rows? **65.**
8. Which state has the largest total damage, and how many events? **Missouri, $1,791,939,000** (property $1,791,384,000, crop $555,000) on **2,840** events. One Missouri tornado (event 1262207, 16 May 2025) is stored as `1.60B` property damage.
9. Property damage for events that began in May 2025? **$1,773,718,960.** That question filters Date (begin), not End Date.
10. How many Texas tornadoes, and what property damage? **143** events, **$16,062,500.** Hail events in the same file, any state: **9,238.** Average magnitude stays blank if hail and tornado are both in the filter.
