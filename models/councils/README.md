# City Council Votes (8 US councils)

A semantic model of what eight city councils put on their full-council agendas and how members voted, from each
city's Legistar public Web API, joined into one schema by our own data factory: Seattle, Bellevue, Oakland, Boston,
Madison, Denver, Phoenix and San José. 295 meetings, 16,206 agenda lines (4,706 decided), 24,541 member-vote rows
on 1,048 distinct roll calls, 24 Nov 2025 to 24 Nov 2026. The model's point is the one only the join shows:
**counted per roll call instead of per agenda item, Denver's council was unanimous 61% of the time, not 90%, and
Oakland's 70%, not 93%**; Seattle, which votes every item separately, really is 97% unanimous.

## Source

- **Data:** `data-factory/councils/data/` (`meetings.csv`, `items.csv`, `votes.csv`, `item_votes.csv`), built
  24 Nov 2026 by `fetch.py` and `build.py`. Schema in `schema.md`, sources in `SOURCES.md`, checks in `QUALITY.md`,
  findings and red team in `FINDINGS.md`.
- `data/prep.py` (duckdb, read only on the factory) writes the model's four Parquet files (`meetings`, `items`,
  `votes`, `members`; 0.5 MB together, gitignored): meeting dates onto items and votes, the roll-call columns from
  `item_votes.csv` onto items, `money_counted` (below) and a `(blank)` vote value for the 8 rows the API left empty.
- **Licence:** the cities' public meeting records, read through Legistar's public Web API (no key). Granicus
  publishes no separate licence for the API; cite the city clerk's records. No personal data beyond the names of
  elected officials on public roll calls.
- **Not at a public URL.** The model reads the Parquet files from `CouncilsFolder`. For the service test they were
  copied to the `CivicData` lakehouse in Semantic Models Lab (`Files/councils/`) with `fab cp`.

### What the data can and can't say (from the factory's quality checks and red team)

- **Coverage differs by city; read `City[Roll Call Practice]` and `City[Coverage]` first.** Bellevue and San José
  publish agendas but no actions or votes (decided items blank). Boston records actions but only voice votes (no roll
  calls). Madison takes a roll call only when contested, so its 7% "unanimous" is an artifact. **Denver (26 of 49
  meetings, to 1 Jun 2026) and Phoenix (5 of 22) are partial**: `Meetings` counts every meeting, items only those
  loaded. Oakland's last weeks rest on draft minutes.
- **Block roll calls.** Denver, Oakland and Phoenix take one roll call for a block of items and copy its VoteIds
  onto every item. `Unanimous Share per Item` repeats the block; `Unanimous Share per Roll Call` counts it once.
  Count no votes with `No Votes` (distinct VoteId), never by row.
- **Consent items are unanimous by construction**: a member who objects pulls the item first.
- **"Voted on its own" is selected for controversy**, so `Split Share of Own Votes` by topic measures what gets
  pulled, not what is controversial in general.
- **Topics are a first-match regex on the title, about 70 to 77% right** on a 30-item hand check, with systematic
  misses (grants and developer agreements under contract; honorary street namings under transportation). Topic
  splits are directional; vote and consent figures don't depend on topics.
- **Dollar figures are the first amount in the title**, not an appropriation or `MatterCost`. `Decided Dollars`
  counts each city and matter once and leaves out Oakland's resolution on state Prop 1 ($11.25 billion) and a Boston
  request for information on $558.7 million of ARPA money. Contract totals include grants and developer agreements.
- `matter_status` in the factory is the status at fetch time, not a history; it is not loaded.

## Grain and size

| Fact | Grain | Rows |
|---|---|---|
| Fact Meeting | one full-council meeting | 295 |
| Fact Item | one agenda line with a title or a matter | 16,206 |
| Fact Vote | one member on one item's roll call (absent members kept) | 24,541 (10,024 distinct member votes) |

## Star schema

```
              Date (1 day) 1 --*  Fact Meeting  *-- 1  City (8)
                           1 --*  Fact Item     *-- 1  City, Topic (20)
                           1 --*  Fact Vote     *-- 1  City, Topic, Member (66), Vote Value (16)
```

Every relationship is many-to-one, single direction. One marked date table (meeting date). Votes carry their item's
city, date, topic and consent flag, so the shared dimensions filter all three facts directly and no fact filters
another.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Meeting, Fact Item, Fact Vote | above | Meeting Key, Item Key, Vote Key | measures only |
| City | 8 | City (Legistar client) | City Name, State, Roll Call Practice, Records Actions, Coverage |
| Member | 66 | Member Key (city and person id) | Member, Member City |
| Topic | 20 | Topic | Topic Label (sorted in first-match order) |
| Vote Value | 16 | Vote Value | Vote Group (Yes, No, Abstain, Absent, Other) |
| Date | 426 (Nov 2025 to Dec 2026) | Date | Year, Quarter, Month, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `CouncilsFolder` | OneLake URL of `CivicData/Files/councils` | Folder holding the four Parquet files |
| `CouncilFiles` | shared, not loaded | `AzureStorage.DataLake ( CouncilsFolder )` |
| `Calendar` | shared, not loaded | 2025-11-01 to 2026-12-31 |

No incremental refresh: the factory rebuilds the whole snapshot (TmdlCheck's PRF3 warning, accepted).

## Measures (28)

| Folder | Measures |
|---|---|
| Volume | Meetings, Agenda Items, Decided Items |
| Roll Calls | Items with Roll Call, Roll Calls, Unanimous Items, Unanimous Share per Item, Unanimous Roll Calls, Unanimous Share per Roll Call, Share of Roll-Call Items in Blocks, Own-Vote Roll Calls, Split Share of Own Votes |
| Consent | Consent Items, Consent Share of Decided, Unanimous Share on Consent, Unanimous Share off Consent |
| Money | Decided Dollars, Items with Dollar Figure, Median Dollar Figure |
| Votes | Member Vote Rows, Member Votes, Absences |
| Dissent | No Votes, Members with a No, Top Dissenter, Top Dissenter No Votes, Top Dissenter Share |
| About | Attribution |

## Best-practice checklist

- Star schema, many-to-one single-direction relationships, no bi-directional or many-to-many; one marked date table,
  auto date/time off, implicit measures discouraged.
- Every table, column, measure and expression has a description; every measure a format string and display folder;
  percentages in percent format; sort-by columns on month, quarter, topic and vote group.
- Fact columns hidden and not available in MDX; dimension keys marked `isKey`; fixed decimal (currency) for money,
  no floating point; DIVIDE everywhere, no IFERROR; rates `COALESCE` their numerators so zero reads 0%, not blank.
- Distinct-count measures where the source repeats a fact (block roll calls), so no figure double-counts.
- One connector (`AzureStorage.DataLake`); one parameter to repoint it.

## Ten business questions (acceptance checks)

Expected answers computed first from the factory's raw CSVs with duckdb (`tests/expected.py`), independently of the
model's Parquet; they also match `FINDINGS.md`.

| # | Question | Expected (duckdb) |
|---|---|---|
| 1 | How much is loaded? | 295 meetings, 16,206 items, 4,706 decided, 24,541 vote rows, 1,048 roll calls |
| 2 | Denver unanimous, per item vs per roll call | 89.9% of 936 items vs **60.6%** of 241 roll calls |
| 3 | Oakland unanimous, per item vs per roll call | 92.5% of 496 vs **69.6%** of 92 |
| 4 | Oakland consent share of decided; unanimous on / off consent | 82.7%; 97.6% / 63.5% |
| 5 | Which topics carry the money? | contract 693 items $3.244 bn (median $1.0M); budget 231, $2.032 bn ($0.8M); other 75, $191M ($4,000) |
| 6 | Contracts voted on their own, share with a no | 149, **57.0%** |
| 7 | Oakland no votes and top dissenter | 40; Carroll Fife 17 (42.5%) |
| 8 | Denver no votes and top dissenter | 242; Chris Hinds 63 (26.0%) |
| 9 | Seattle roll calls, unanimous share | 634, 96.7% |
| 10 | Meetings and decided items by city; meetings in 2026 Q1 | Bellevue 47/1/13, Boston 32/690/8, Denver 49/1,141/13, Madison 25/1,383/6, Oakland 21/510/6, Phoenix 22/347/6, San José 57/0/15, Seattle 42/634/13 |

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/councils/CouncilVotes.SemanticModel/definition`):
loads, validates, round-trips; every error rule passes (PRF3 warns: no incremental refresh, by design).

**In Fabric (25 Nov 2026, F2):** lakehouse **CivicData**; Parquet in
`Files/councils/`; `fab import` as "City Council Votes"; OAuth2 on the OneLake source; full refresh **Completed in
6 s**. The first query run found what TmdlCheck can't: `Member[...]` unquoted fails in the engine (`MEMBER` is a
reserved word), so four Dissent measures returned a syntax error; quoted as `'Member'[...]`, re-imported, refreshed
(3 s). `tests/checks.dax` **10/10** (San José's decided items read blank, i.e. zero); all 28 measures evaluate; zero
orphan keys on any relationship. Capacity paused; `az rest` `properties.state` = `Paused`.
