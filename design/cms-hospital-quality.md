# CMS hospital quality (Care Compare)

Model #3. U.S. government work, public domain in the United States (17 USC 105). CMS asks that reuse not imply the government endorses a product (42 USC 1320b-10). Downloaded 24 Nov 2026. Every answer was computed from these two files. No API key.

## Source

| Item | Value |
|---|---|
| Topic | https://data.cms.gov/provider-data/topics/hospitals (catalog release 12 Nov 2026) |
| About using the data | https://data.cms.gov/provider-data/topics/long-term-care-hospitals/about-using-government-data (same catalog: public domain, attribution appreciated) |
| Dictionary | https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/hospital/HOSPITAL_Data_Dictionary.pdf (October 2026, about 1 MB) |
| Hospital General Information | https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv |
| Complications and Deaths, hospital | https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0/download?format=csv |
| Dataset pages | https://data.cms.gov/provider-data/dataset/xubh-q36u and https://data.cms.gov/provider-data/dataset/ynj2-r877 |
| Sizes | General information 1,565,956 bytes, 5,435 rows. Complications 24,020,540 bytes, 95,740 rows. Together under 50 MB. Not gitignored. |
| Saved as | `samples/cms-hospital-general.csv` (download from the source; not committed), `samples/cms-complications-hospital.csv` (download from the source; not committed) |
| What this release is | One catalog snapshot. Measure rows carry a performance window (mostly 1 Jul 2022–30 Jun 2025 or 1 Jul 2023–30 Jun 2025). Overall stars do not. Older snapshots live in the hospital archive (https://data.cms.gov/provider-data/archived-data/hospitals). Load those later as more `Release Date` values. Do not load national or state rollup files into the fact. |

Do not add CMS claims microdata, and do not add anything that carries the AHA UB-04 specification. Those are not in these files and are not public domain. Street and phone in the general-information file are the hospital's published Care Compare address, not a patient address. Keep them off reports if a visual does not need them. The model may store them on the hospital dimension.

## Grain

Two facts, one hospital dimension.

- **Fact Measure Result:** one row per facility × measure × performance window. 95,740 rows in this file (4,787 facilities × 20 measures). `Start Date` and `End Date` are the window CMS used, not the day the file was posted.
- **Fact Overall Rating:** one row per facility × catalog release. This sample has one release, 12 Nov 2026, so 5,435 rows. Stars are a separate fact because they have no performance window and they cover hospitals that are absent from the complications file.

## Star schema

### Hospital

From general information. `Facility ID` is the key (6-character CMS id, text, keep leading zeros).

| Column | Notes |
|---|---|
| Facility ID | key |
| Facility Name | |
| Hospital Type | Acute Care Hospitals, Critical Access Hospitals, Psychiatric, VA, children's, DoD, cancer, rural emergency |
| Hospital Ownership | |
| Emergency Services | Yes/No |
| Birthing Friendly | Y or blank |
| Address, City, ZIP Code, County, Telephone | published facility fields. Hide Address and Telephone (`summarizeBy: none`) |
| State Code | FK to State |

### State

`State Code` (key), `State Name`. 56 codes in this file (states, DC, and territories). Static names in M.

### Measure

`Measure ID` (key), `Measure Name`, `Family` (Mortality, Surgical complication, Patient safety). Sort column `Measure Sort`. Built from the distinct measure rows, not typed by hand: the file has 20 ids (`MORT_30_AMI`, `MORT_30_HF`, `MORT_30_PN`, `MORT_30_COPD`, `MORT_30_STK`, `MORT_30_CABG`, `COMP_HIP_KNEE`, `Hybrid_HWM`, `ISCMR`, `PSI_03`, `PSI_06`, `PSI_08` through `PSI_15`, `PSI_90`).

### Date (marked date table)

Daily from 1 Jul 2022 through 31 Dec 2026 so both performance windows and the 12 Nov 2026 release fit. Columns: `Date`, `Year`, `Month Number`, `Month`, `Year Month`, `Year Month Sort`. Mark on `Date`. Auto date/time off.

### Fact Measure Result

| Column | Type | Notes |
|---|---|---|
| Facility ID | text | FK |
| Measure ID | text | FK |
| Start Date | date | role-playing, inactive relationship |
| End Date | date | active FK to Date |
| Release Date | date | 2026-11-12 for every row of this file. Inactive FK |
| Score | decimal | blank stays null. CMS publishes "Not Available" as text. Do not coerce that to zero |
| Denominator | decimal | cases. Null when not numeric |
| Lower Estimate, Higher Estimate | decimal | interval. Null when blank |
| Compared to National | text | see values below |
| Footnote | text | |

`Compared to National` in this file: Not Available (61,885), No Different Than the National Rate (27,504), Number of Cases Too Small (2,613), No Different Than the National Value (2,589), Worse Than the National Rate (683), Better Than the National Rate (266), Worse Than the National Value (139), Better Than the National Value (61). Death-rate rows (`MORT_30_*`) are all "Not Available" in the comparison column even when `Score` is numeric. Do not treat a blank comparison as "same as national."

### Fact Overall Rating

`Facility ID`, `Release Date` (active date FK), `Overall Rating` (whole number 1–5, null when "Not Available"), `Mortality Measures`, `Mortality Better`, `Mortality No Different`, `Mortality Worse`, and the same three counts for Safety and Readmission. Patient-experience and timely-care columns in the source are mostly empty in this release. Leave them out until a release fills them.

### Relationships

| From | To | Cardinality | Cross filter | Active |
|---|---|---|---|---|
| Fact Measure Result[Facility ID] | Hospital[Facility ID] | many to one | single | yes |
| Fact Measure Result[Measure ID] | Measure[Measure ID] | many to one | single | yes |
| Fact Measure Result[End Date] | Date[Date] | many to one | single | yes |
| Fact Measure Result[Start Date] | Date[Date] | many to one | single | no |
| Fact Measure Result[Release Date] | Date[Date] | many to one | single | no |
| Fact Overall Rating[Facility ID] | Hospital[Facility ID] | many to one | single | yes |
| Fact Overall Rating[Release Date] | Date[Date] | many to one | single | yes |
| Hospital[State Code] | State[State Code] | many to one | single | yes |

## Measures

Folder in parentheses. A score of "Not Available" is null, so averages ignore it.

Result

1. **Results** `#,0` (Volume). `COUNTROWS ( 'Fact Measure Result' )`. Rows, not hospitals.
2. **Hospitals with a result** `#,0` (Volume). `DISTINCTCOUNT ( 'Fact Measure Result'[Facility ID] )`.
3. **Reported scores** `#,0` (Volume). `CALCULATE ( [Results], NOT ISBLANK ( 'Fact Measure Result'[Score] ) )`.
4. **Average score** `0.00` (Result). `AVERAGE ( 'Fact Measure Result'[Score] )`. Unweighted. Say so. CMS rates are not all on one scale (`PSI_90` is near 1, death rates are near 12).
5. **Denominator weighted score** `0.00` (Result). `DIVIDE ( SUMX ( 'Fact Measure Result', [Score] * [Denominator] ), SUM ( 'Fact Measure Result'[Denominator] ) )`. Use inside one measure.
6. **Total denominator** `#,0` (Result). `SUM ( 'Fact Measure Result'[Denominator] )`.

Comparison

7. **Better than national** `#,0` (Comparison). `CALCULATE ( [Results], 'Fact Measure Result'[Compared to National] IN { "Better Than the National Rate", "Better Than the National Value" } )`.
8. **Worse than national** `#,0` (Comparison). Same pattern for the two "Worse Than…" strings.
9. **No different than national** `#,0` (Comparison). The two "No Different…" strings.
10. **Too small to compare** `#,0` (Comparison). `Compared to National = "Number of Cases Too Small"`.
11. **Share worse** `0.0%` (Comparison). `DIVIDE ( [Worse than national], [Better than national] + [Worse than national] + [No different than national] )`. Leaves out Not Available and too-small.

Stars (on Fact Overall Rating)

12. **Rated hospitals** `#,0` (Stars). `CALCULATE ( COUNTROWS ( 'Fact Overall Rating' ), NOT ISBLANK ( 'Fact Overall Rating'[Overall Rating] ) )`.
13. **Average stars** `0.00` (Stars). `AVERAGE ( 'Fact Overall Rating'[Overall Rating] )`.
14. **Five star hospitals** `#,0` (Stars). `CALCULATE ( [Rated hospitals], 'Fact Overall Rating'[Overall Rating] = 5 )`.
15. **One star hospitals** `#,0` (Stars). Rating = 1.
16. **Five star share** `0.0%` (Stars). `DIVIDE ( [Five star hospitals], [Rated hospitals] )`.
17. **Birthing friendly hospitals** `#,0` (Hospital). `CALCULATE ( COUNTROWS ( Hospital ), Hospital[Birthing Friendly] = "Y" )`.
18. **Hospitals** `#,0` (Hospital). `COUNTROWS ( Hospital )`.

Safety counts stored on the star fact (already a count, so sum them only at hospital grain, one release)

19. **Safety measures worse** `#,0` (Stars). `SUM ( 'Fact Overall Rating'[Safety Worse] )`. Sum of CMS's per-hospital counts.
20. **Mortality measures worse** `#,0` (Stars). `SUM ( 'Fact Overall Rating'[Mortality Worse] )`.

## Power Query M

```powerquery
let
  Source = Csv.Document(Web.Contents("https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Promote = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  Keep = Table.SelectColumns(Promote, {"Facility ID","Facility Name","Address","City/Town","State","ZIP Code","County/Parish","Telephone Number","Hospital Type","Hospital Ownership","Emergency Services","Meets criteria for birthing friendly designation"}),
  Rename = Table.RenameColumns(Keep, {{"City/Town","City"},{"State","State Code"},{"County/Parish","County"},{"Telephone Number","Telephone"},{"Meets criteria for birthing friendly designation","Birthing Friendly"}}),
  Hospital = Table.TransformColumnTypes(Rename, {{"Facility ID", type text},{"ZIP Code", type text}})
in
  Hospital
```

```powerquery
let
  Source = Csv.Document(Web.Contents("https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0/download?format=csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Promote = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  Keep = Table.SelectColumns(Promote, {"Facility ID","Measure ID","Measure Name","Compared to National","Denominator","Score","Lower Estimate","Higher Estimate","Footnote","Start Date","End Date"}),
  Types = Table.TransformColumnTypes(Keep, {{"Facility ID", type text},{"Start Date", type date},{"End Date", type date},{"Score", type number},{"Denominator", type number},{"Lower Estimate", type number},{"Higher Estimate", type number}}),
  // type number turns "Not Available" into null, which is what the averages require
  Release = Table.AddColumn(Types, "Release Date", each #date(2026, 11, 12), type date),
  Fact = Table.SelectColumns(Release, {"Facility ID","Measure ID","Start Date","End Date","Release Date","Score","Denominator","Lower Estimate","Higher Estimate","Compared to National","Footnote"})
in
  Fact
```

Overall rating from the same general-information URL, columns `Facility ID`, `Hospital overall rating`, and the MORT/Safety/READM count columns. Replace `"Not Available"` with null before typing the rating as a number. Add `Release Date = #date(2026,11,12)`.

Measure dimension: `Table.Distinct` of `Measure ID` and `Measure Name` from the fact query, plus a `Family` column (`Text.StartsWith` `MORT` → Mortality, `COMP` or `ISCMR` or `Hybrid` → Surgical complication, `PSI` → Patient safety).

State: the distinct `State Code` values, names entered for the 50 states plus DC, PR, GU, VI, AS, MP. Date: `List.Dates(#date(2022,7,1), Duration.Days(#date(2026,12,31)-#date(2022,7,1))+1, #duration(1,0,0,0))`.

When an archive zip is added, append its rows with that archive's release date. Do not union a national file.

## Ten questions

This catalog release only. Averages are unweighted unless the question says weighted. "Rated" means overall rating 1 through 5.

| # | Question | Expected |
|---|---|---|
| 1 | How many acute care hospitals are rated, and how many have 5 stars? | 2,654 rated of 3,094 acute care hospitals. 290 have 5 stars (10.93%). 175 have 1 star. |
| 2 | California acute care hospitals with 5 stars | 25 of 257 rated. |
| 3 | Mean overall stars, New York acute care hospitals that are rated | 2.70 on 122 hospitals (2.7049). |
| 4 | Among states with at least 20 rated acute care hospitals, which has the highest share of 1-star hospitals? | Mississippi, 11 of 46 (23.91%). West Virginia is next (4 of 21). |
| 5 | Unweighted mean heart-attack death rate (`MORT_30_AMI`) where a score is published | 11.83 (11.8302) across 1,933 hospitals. Window 1 Jul 2022–30 Jun 2025. Denominator-weighted mean is 11.75 (11.7536). The comparison column is "Not Available" on every AMI row. |
| 6 | Southeast Health Medical Center, Dothan AL (`010001`) | Overall rating 4. Heart-attack death rate 13.5 on 234 cases. Hip/knee complication rate 3.8 on 33 cases, comparison "Not Available". |
| 7 | Hospitals worse than the national inpatient surgical complications mortality rate (`ISCMR`) | 272 worse, 152 better, 1,892 no different. Window 1 Jul 2023–30 Jun 2025. 1,993 are Not Available and 478 are too small. |
| 8 | Hospitals worse than the national value on the PSI-90 safety composite | 139 worse, 61 better, 2,589 no different. Unweighted mean score where numeric: 0.99 (0.9941) on 2,789 hospitals. Window 1 Jul 2023–30 Jun 2025. |
| 9 | Pressure-ulcer rate (`PSI_03`) worse than national | 157 worse, 39 better, 2,733 no different. Same window as PSI-90. |
| 10 | Acute care hospitals CMS marks birthing-friendly | 2,035 of 3,094. |

A query item that averages `Score` across measure ids is not a fair item. Pin the measure. A query item that treats AMI "Not Available" as worse, or as zero, is wrong.
