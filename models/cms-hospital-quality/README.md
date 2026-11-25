# CMS Hospital Quality

A star-schema semantic model of US hospital quality from CMS Care Compare: the overall star rating and the
per-group counts behind it for every hospital, and each hospital's results on the 20 complications and deaths
measures (death rates, surgical complications, patient-safety indicators) with CMS's comparison to the national rate.

## Source

- **Publisher:** Centers for Medicare & Medicaid Services (CMS), [Provider Data Catalog, Hospitals](https://data.cms.gov/provider-data/topics/hospitals).
- **Files** (CSV downloads from the catalog's datastore API, no API key; the copies checked here, catalog release
  12 Nov 2026, are in `samples/` (download from the source; not committed)):
  - Hospital General Information, dataset [`xubh-q36u`](https://data.cms.gov/provider-data/dataset/xubh-q36u):
    5,435 rows, 1.6 MB (`cms-hospital-general.csv`, committed).
  - Complications and Deaths - Hospital, dataset [`ynj2-r877`](https://data.cms.gov/provider-data/dataset/ynj2-r877):
    95,740 rows, 24 MB (`cms-complications-hospital.csv`, gitignored as over 10 MB; download it from the dataset page).
  - Field definitions: the [CMS hospital data dictionary](https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/hospital/HOSPITAL_Data_Dictionary.pdf).
- **Licence:** public domain in the United States. CMS data is a work of the US government (17 USC 105); CMS asks for
  attribution ("Source: Centers for Medicare & Medicaid Services, Care Compare") and that reuse not imply the
  government endorses a product (42 USC 1320b-10).
- **Refreshed by:** Power Query M in the model (`Web.Contents` + `Csv.Document`), straight from data.cms.gov,
  anonymous. The release date is read at refresh from each dataset's metastore entry (`released`).
- **Not included:** national and state rollup files (they would double-count), claims microdata, and anything carrying
  the AHA UB-04 specification (not public domain).

### Field caveats

- **"Not Available" is not zero.** CMS writes `Not Available` (and `Not Applicable` for the PSI 90 denominator) in
  numeric fields; the model loads them as blank, so averages ignore them and counts skip them.
- **The comparison column is often empty of meaning.** `Compared to National` is `Not Available` on every
  `MORT_30_*` death-rate row even where a score is published, and on 61,885 of 95,740 rows overall. It is never
  "same as national"; the model counts it apart (`Not available to compare`).
- **Scores are on different scales** (death rates near 12 per 100, PSI 90 a ratio near 1) and every measure here is
  lower-is-better. `Average score` returns blank unless one measure is in scope.
- **Performance windows differ by measure:** 1 Jul 2022 to 30 Jun 2025 for the 30-day death rates, 1 Jul 2023 to
  30 Jun 2025 for ISCMR and the PSIs, 1 Apr 2023 to 31 Mar 2025 for hip/knee complications, 1 Jul 2024 to 30 Jun 2025
  for the hybrid hospital-wide mortality rate. The star rating carries no window.
- **Address and telephone** are the hospital's published Care Compare contact fields, not patient data. They are
  hidden on the Hospital table; keep them off reports that don't need them.
- **One release.** The datastore URLs always serve the current release. Older releases are in the
  [hospital archive](https://data.cms.gov/provider-data/archived-data/hospitals); loading them would mean appending
  their rows with their own release date (every measure already reads only the latest release in context).

## Grain and size

- `Fact Measure Result`: one row per **facility x measure x performance window x release**. 95,740 rows
  (4,787 facilities x 20 measures), 51,682 with a published score.
- `Fact Overall Rating`: one row per **facility x release**. 5,435 rows, 3,166 with a star rating. A separate fact
  because stars have no performance window and cover hospitals absent from the complications file.

## Star schema

```
Hospital (5,435)  1 --* Fact Measure Result *-- 1  Quality Measure (20)
                        Fact Measure Result *-- 1  Performance Date   End Date (active); Start Date (inactive, dashed)
                        Fact Measure Result *-- 1  Release Date       catalog release
Hospital (5,435)  1 --* Fact Overall Rating *-- 1  Release Date       catalog release
```

Every relationship is many-to-one from a fact, single direction. The Start Date link is inactive and used
through `USERELATIONSHIP` (`Results by window start`).

### Two dates, two date tables (role-playing)

The two facts are dated by different things, so the model has two marked date tables rather than one shared one:

| Date table | Means | Filters | Not related to |
|---|---|---|---|
| **Performance Date** | The performance window CMS measured: active on the window's **End Date**, inactive on its Start Date | Fact Measure Result | Fact Overall Rating (stars have no window) |
| **Release Date** | The catalog release CMS posted the data in (12 Nov 2026 today) | Fact Measure Result and Fact Overall Rating | |

On one shared Date table a slicer blanked one fact or the other: a 2025 slicer (when the windows end) emptied the
stars, and the release day emptied the scores. Now:

| Visual | Date to use |
|---|---|
| Scores, comparisons, result counts over time ("death rates for windows ending in 2025") | **Performance Date** (Year, Year Quarter) |
| Star ratings, Hospitals rated, the `… measures worse` counts | **Release Date**, or no date at all (they read the latest release in context) |
| A page that mixes stars and scores | **Release Date**; a Performance Date slicer there filters the scores only and leaves the stars whole |
| Which release a figure comes from, release-over-release comparison once archives are loaded | **Release Date** (`Results by release`, `Latest result release`, `Latest release date`) |
| Counting windows by when they started | Performance Date with `Results by window start` |

`Hospitals` and `Birthing friendly hospitals` count the Hospital dimension and ignore both date tables (see Measures).

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Measure Result | 95,740 | none (all columns hidden) | measures only |
| Fact Overall Rating | 5,435 | none (all columns hidden) | measures only |
| Hospital | 5,435 | Facility ID (6-character CCN, text) | Facility Name, Hospital Type, Hospital Ownership, Emergency Services, Birthing Friendly, City, ZIP Code, County, State Code, State Name |
| Quality Measure | 20 | Measure ID | Measure ID, Measure Name (sorted by family), Family (Mortality, Surgical complication, Patient safety) |
| Performance Date | one per day, 1 Jan 2022 to 31 Dec of the refresh year | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month, Month Start |
| Release Date | one per day, same range | Date | same columns as Performance Date |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `CmsBaseUrl` | `https://data.cms.gov/provider-data/` | The one Web data source (root answers 200); files are `RelativePath`s |
| `CalendarStart` | 2022-01-01 | First day of both date tables (the year of the earliest window) |
| `CalendarEnd` | 31 December of the current year (computed) | Whole years, covers the latest release |
| `GeneralInformation` | shared query, not loaded | General information CSV + release date; feeds Hospital and Fact Overall Rating |
| `ComplicationsAndDeaths` | shared query, not loaded | Complications CSV + release date; feeds Fact Measure Result and Quality Measure |

No incremental refresh: two CSVs, about 26 MB together; a full refresh took 15 to 20 seconds on an F2.

## Measures (28)

| Folder | Measures |
|---|---|
| Volume | Results, Hospitals with a result, Reported scores, Results by window start, Results by release |
| Result | Average score, Denominator weighted score, Total denominator |
| Comparison | Better than national, Worse than national, No different than national, Too small to compare, Not available to compare, Share worse, Share better |
| Stars | Hospitals rated, Average stars, Five star hospitals, One star hospitals, Five star share, One star share, Mortality measures worse, Safety measures worse, Readmission measures worse |
| Hospital | Hospitals, Birthing friendly hospitals |
| Audit | Latest release date, Latest result release |

Notes on the logic:

- **Average score** is unweighted (each hospital counts once) and blank unless exactly one quality measure is in scope.
  **Denominator weighted score** weights by eligible cases over rows with both a score and a denominator (blank for
  PSI 90, which has no denominator).
- **Share worse / better** divide by the compared results only (better + no different + worse); Not Available and
  too-small are left out of both sides.
- **Every measure on either fact reads the latest release in context** (`Latest release date` for stars,
  `Latest result release` for results), so a hospital is never counted twice once archived releases are added, even
  when two releases' performance windows fall in the same Performance Date filter. The three `… measures worse` sum
  CMS's per-hospital counts within that release. `Results by release` drops any Performance Date filter: put Release
  Date on the axis to count each release's rows.
- **`Hospitals` counts the dimension.** It follows Hospital filters (type, state, ownership) but not Performance Date,
  Release Date or Quality Measure, because relationships filter from dimensions to facts. Use `Hospitals with a result`
  for hospitals that reported in a period or on a measure, and `Hospitals rated` for rated ones.

## Ten business questions (acceptance checks)

Pinned to the 12 Nov 2026 catalog release. Expected answers come from Grok's design (`design/cms-hospital-quality.md`)
and were recomputed independently from the raw CSVs with Python (`csv` + `Decimal`) before deploying;
`tests/checks.dax` asks each one of the deployed model. "Rated" means an overall rating of 1 to 5.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | Acute care hospitals: rated, 5 star, 1 star | 2,654 rated of 3,094; 290 five star (10.93%); 175 one star | 2,654 of 3,094; 290 (10.93%); 175 | Pass |
| 2 | California acute care, 5 star | 25 of 257 rated | 25 of 257 | Pass |
| 3 | Mean stars, rated New York acute care | 2.7049 on 122 | 2.7049 on 122 | Pass |
| 4 | Highest 1-star share, states with 20+ rated acute care | Mississippi 11 of 46 (23.91%); West Virginia next, 4 of 21 | MS 11/46 (23.91%); WV 4/21 (19.05%) | Pass |
| 5 | Heart-attack death rate `MORT_30_AMI` | 11.8302 on 1,933; weighted 11.7536; window 2022-07-01 to 2025-06-30; comparison Not Available on every row | 11.8302 on 1,933; 11.7536; same window; 4,787 Not Available | Pass |
| 6 | Southeast Health Medical Center, Dothan AL (`010001`) | Rating 4; AMI 13.5 on 234; hip/knee 3.8 on 33, Not Available | 4; 13.5 on 234; 3.8 on 33, Not Available | Pass |
| 7 | `ISCMR` vs national | 272 worse, 152 better, 1,892 no different, 1,993 Not Available, 478 too small; window 2023-07-01 to 2025-06-30 | identical | Pass |
| 8 | `PSI_90` vs national | 139 worse, 61 better, 2,589 no different; mean 0.9941 on 2,789 | identical | Pass |
| 9 | `PSI_03` vs national | 157 worse, 39 better, 2,733 no different | identical | Pass |
| 10 | Birthing-friendly acute care hospitals | 2,035 of 3,094 | 2,035 of 3,094 | Pass |

Also checked: 95,740 result rows, 5,435 rating rows and hospitals, 20 measures, release 2026-11-12; zero fact rows
without a Hospital, Quality Measure or Date; `Average score` blank across measures; the inactive relationships count
23,935 results by a 2022 window start and all 95,740 by the 2026 release; every one of the 27 measures evaluates.

## Changes from the design (`design/cms-hospital-quality.md`)

- **No State table: state folded into Hospital** (`State Code`, `State Name`). Hospital -> State made a snowflake, and
  a dimension on the many side of a relationship is treated as a fact (its columns must all hide, PRF2). The 56 codes
  are named in M with USPS names.
- **`Measure` table is `Quality Measure`**: `MEASURE` is a DAX keyword and the bare name reads badly in queries.
- **`Hybrid_HWM` is Mortality**, not Surgical complication: it is CMS's hybrid hospital-wide all-cause mortality rate.
  Families are Mortality 7, Surgical complication 2 (COMP_HIP_KNEE, ISCMR), Patient safety 11.
- **Release date read from CMS**, not hard-coded `#date(2026, 11, 12)`: each dataset's metastore `released` field,
  so a refresh after the next release is labelled correctly.
- **One data source.** `Web.Contents(CmsBaseUrl, [RelativePath, Query])` instead of full URLs, so the service sees
  one static source whose root answers 200 (the credential-test gotcha from model #1). Each CSV is downloaded once
  into a shared query that two tables reference.
- **Robust M.** Numbers parsed with `try Number.FromText … otherwise null` (the design's `type number` turns `Not
  Available` into cell errors, not clean nulls); dates parsed with an explicit `MM/dd/yyyy` format; star and count columns get
  the same treatment.
- **`Average score` and `Denominator weighted score` are blank across measures**, enforcing the design's own warning
  that a cross-measure average is not fair. The weighted score sums denominators only where a score exists.
- **`Rated hospitals` -> `Hospitals rated`** (the BPA percentage rule matches `Rate` in a measure name).
- **Star measures take the latest release in context** (the design's plain counts would double-count once archived
  releases are appended). Single-release answers are unchanged.
- **Denominator is a whole number** (int64; no fractional cases in the file); scores and estimates are fixed decimal
  (at most two decimals in the file).
- **Added:** `Not available to compare`, `Share better`, `One star share`, `Readmission measures worse`,
  `Results by window start` and `Results by release` (the inactive relationships had no measure using them),
  `Latest release date`. Readmission counts are on the rating fact alongside mortality and safety.
- **Date tables start 1 Jan 2022** (whole years) and end with the current year instead of a fixed 31 Dec 2026.
- **Two date tables, not one** (Grok's review, 24 Nov 2026): Performance Date for the measurement window and Release
  Date for the catalog release. One shared Date table on End Date and on the rating's Release Date made a date slicer
  blank either the stars or the scores.
- Hospital types in the file are `Childrens` and also include `Long-term` (5), not listed in the design.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/cms-hospital-quality/CmsHospitalQuality.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except one deliberate warning:

| Rule | Status |
|---|---|
| Descriptions on every table, column, measure and expression | Pass |
| Format strings; `%` formats on percentages; visible measures in display folders | Pass |
| `summarizeBy: none` on numeric columns; implicit measures discouraged | Pass |
| Foreign keys hidden; dimension keys `isKey`; month, year-month and measure labels sorted | Pass |
| Marked date table; auto date/time off | Pass |
| Many-to-one, single-direction relationships on matching types; no islands | Pass |
| Fixed decimal (no floating point); fact columns hidden, `isAvailableInMdx: false` | Pass |
| DIVIDE, no IFERROR, column/measure reference style, every reference resolves | Pass |
| PRF3 incremental refresh on the facts | **Warn, deliberate**: each fact is one CSV snapshot with no date to partition on |

TmdlCheck passed a measure the engine rejected: a DAX variable named `Rows` (reserved) in `Denominator weighted score`
failed only at query time in the service. Renamed `ScoredRows`.

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in about 20 s**, and the 10 questions matched **10/10**. Details in
the [run log](../../docs/toolchain.md#run-log).

**After Grok's review (24 Nov 2026):** redeployed with the two date tables and the release-pinned result measures;
refresh 16 s; the 10 questions still **10/10**, check 13 shows the role-playing dates (performance year 2025: 95,740
results and 3,166 rated hospitals; release year 2026: the same), and all 28 measures evaluate.
