# NASA FIRMS active fire detections

Model #7. Satellite detections, after taxi, electricity, hospitals, retail, price paid, and storm events. NASA LANCE FIRMS country yearly CSVs. No MAP_KEY and no Earthdata login. The area API needs a free MAP_KEY; this model does not use it. Downloaded 24 Nov 2026. Every answer was counted from the Portugal files below.

## Licence and citation

NASA’s Earth Science data-use guidance says data from a NASA-led mission are Creative Commons Zero (CC0) unless a product page marks a restriction. There is no restriction on reuse. NASA asks for a citation anyway. https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance (page current as fetched 24 Nov 2026).

The file `AttributesReadme.txt` in the same country directory says NASA promotes full and open sharing, and asks that anyone who passes LANCE/FIRMS data to a third party follow the citation guidelines and carry the disclaimer. Disclaimer text is in that readme. It points at https://www.earthdata.nasa.gov/data/tools/firms.

Suggested citation: NASA LANCE FIRMS, country yearly active-fire CSVs (MODIS C6.1, VIIRS S-NPP, VIIRS NOAA-20 / JPSS-1), files dated in the table below, accessed 24 Nov 2026, https://firms.modaps.eosdis.nasa.gov/data/country/.

Algorithm papers, not the licence: Schroeder, Oliva, Giglio, Csiszar, “The New VIIRS 375 m active fire detection data product,” Remote Sensing of Environment 143 (2014), doi:10.1016/j.rse.2013.12.008. MODIS fire: Giglio et al., the Collection 6 active-fire product.

## Source

| Item | Value |
|---|---|
| Country page | https://firms.modaps.eosdis.nasa.gov/country/ |
| File index | https://firms.modaps.eosdis.nasa.gov/data/country/yearly_summary_files.txt (filename, size, updated) |
| Attribute readme | https://firms.modaps.eosdis.nasa.gov/data/country/AttributesReadme.txt (3,178 bytes, updated 23 Jun 2025) |
| URL pattern | `https://firms.modaps.eosdis.nasa.gov/data/country/{product}/{year}/{product}_{year}_{Country}.csv` |
| Products | `modis` (Terra and Aqua, 1 km), `viirs-snpp` (Suomi NPP, 375 m), `viirs-jpss1` (NOAA-20, 375 m). No NOAA-21 country archive in the index. |
| Country name | Underscores, as in `United_States` and `New_Zealand`. The file is already clipped to the country. No point-in-polygon step. |
| Columns | VIIRS: latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence (`l`/`n`/`h`), version, bright_ti5, frp, daynight, type. MODIS uses brightness, bright_t31, and confidence 0–100. |
| NRT note | FIRMS says near-real-time rows are replaced by standard processing after about five months. These country files are the archive (VIIRS `version` 2, MODIS `version` 61.03). S-NPP new observations stopped on 2 Nov 2026; the 2025 country file is still the full year. |

The 7-day global CSVs also need no key (`…/data/active_fire/…/csv/…_Global_7d.csv`). They are a rolling window, not a year, and the S-NPP 7-day file was 112 bytes on 24 Nov 2026. The model uses the country archive.

### Scope

Portugal, calendar years 2024 and 2025, three products. Six files, 4,736,168 bytes. Small enough to keep as the sample and large enough to show the overlap rule. The same three products for the United States, Canada, and Australia in 2025 alone are about 472 MB (S-NPP 100.4 + 73.4 + 37.5 MB, NOAA-20 102.7 + 76.0 + 39.7 MB, MODIS 20.8 + 12.7 + 8.9 MB, from the index on 24 Nov 2026). That set is under 1 GB and uses this same model. It was not downloaded.

| File | Bytes | Rows |
|---|---:|---:|
| `viirs-jpss1_2024_Portugal.csv` | 966,085 | 12,010 |
| `viirs-jpss1_2025_Portugal.csv` | 1,113,849 | 13,862 |
| `viirs-snpp_2024_Portugal.csv` | 946,487 | 12,078 |
| `viirs-snpp_2025_Portugal.csv` | 1,065,513 | 13,600 |
| `modis_2024_Portugal.csv` | 252,905 | 3,151 |
| `modis_2025_Portugal.csv` | 391,329 | 4,867 |

Saved under `samples/firms/` (download from the source; not committed).

## Grain

One fact row per detection: one satellite pixel on one overpass. Portugal 2025 NOAA-20 has 13,862 rows. That is not 13,862 fires. The same fire is seen again on the next overpass, and again by another satellite.

**Do not add the three products.** A pixel that all three see becomes three rows. Portugal 2025 summed across NOAA-20, S-NPP, and MODIS is 32,329 rows and 1,394,438.56 MW of FRP. That number counts the same fires two or three times. It is not a measure in this model.

Terra and Aqua stay together inside MODIS. They are the morning and afternoon MODIS overpasses, one product, not a second copy of NOAA-20. Dropping Aqua would throw away half of MODIS.

There is no burned-area measure. FRP is megawatts at the pixel, not hectares. A 375 m pixel and a 1 km pixel are different areas, and a second overpass would add the area again. Burned area is a different product (MCD64A1 / VNP64A1), not this file.

`type` stays on the row. `0` presumed vegetation fire, `1` volcano, `2` static land source, `3` offshore. Portugal 2025 NOAA-20 is 13,521 type 0, 339 type 2, 2 type 3, no volcano. The default count includes every type. A vegetation-only measure filters type 0. Dropping type 2 in Power Query would hide gas flares and industrial heat and make the file disagree with FIRMS.

## Star schema

### Fact Detection

| Column | Type | Notes |
|---|---|---|
| Detection Key | text | `{Source}\|{acq_date}\|{acq_time}\|{latitude}\|{longitude}`. Unique in these six files. |
| Acq Date | date | `acq_date`. UTC calendar date of the acquisition. The only date relationship. |
| Acq Time | text | `acq_time`, HHMM UTC. Not a date. |
| Source | text | `VIIRS NOAA-20`, `VIIRS S-NPP`, or `MODIS`. From the file, not from the instrument column. Both VIIRS files say `instrument = VIIRS`. |
| Satellite | text | `N20`, `N` (S-NPP), `Terra`, `Aqua` |
| Latitude | decimal | WGS84. Hidden. |
| Longitude | decimal | WGS84. Hidden. |
| FRP | decimal | Megawatts. Null if blank, never coerced from text with a suffix. |
| Confidence | text | VIIRS `l` / `n` / `h`. MODIS stored as the 0–100 text and also as Confidence Band. |
| Confidence Band | text | VIIRS: Low, Nominal, High. MODIS: Low if under 30, Nominal if 30–79, High if 80 or more. |
| Day Night | text | `Day` or `Night` from `D` / `N`. This is the satellite’s day/night flag, not local civil time. |
| Type Code | text | `0`–`3` |
| Brightness | decimal | VIIRS `bright_ti4`, MODIS `brightness`. Kelvin. Not compared across instruments. |

No local-date column. Portugal local time is UTC in winter and UTC+1 in summer. A detection at 23:30 UTC on 15 Aug is already 16 Aug in Portugal. The model does not build that second date, because a second date on the same Date table was the CMS failure. Say the caveat on the Acq Date description: the axis is UTC, not local.

### Date

One calendar, marked `dataCategory: Time`, auto date/time off. 1 Jan 2024 through 31 Dec 2025 for this sample. Fact[Acq Date] to Date[Date], many to one, single direction. No end date, no second relationship.

### Source

Three rows. `Sort` puts NOAA-20 first. `Pixel` is 375 m or 1 km, a label, not a number to multiply by detections.

### Satellite

Four rows. `Source` on this table is how Terra and Aqua both roll to MODIS. Relationship Fact[Satellite] to Satellite[Satellite]. Filtering Source on the dimension filters the fact. Do not also relate Fact[Source] to a second copy of the same key.

### Confidence Band

Low, Nominal, High. One meaning for both instruments after the M step above.

### Day Night

Day, Night.

### Hotspot Type

`0` Vegetation, `1` Volcano, `2` Static land source, `3` Offshore.

## Measures

Folder in parentheses. Format after the name.

The source rule, used by every measure in Detections, FRP, and Time: if Source is not filtered, keep VIIRS NOAA-20 only; if exactly one source is selected, keep that source; if two or three sources are selected, return blank. That is the same shape as Census refusing to add both seasonal adjustments. A matrix with Source on rows uses **Detections in source**, which does not apply the rule.

```powerquery
-- the DAX pattern, named here as the rule
VAR SourceCount = DISTINCTCOUNT ( Source[Source] )
RETURN
    SWITCH (
        TRUE (),
        NOT ISFILTERED ( Source ), CALCULATE ( <expr>, Source[Source] = "VIIRS NOAA-20" ),
        SourceCount = 1, <expr>
    )
```

Detections

1. **Detections** `#,0` (Detections). The rule around `COUNTROWS ( 'Fact Detection' )`. Unfiltered, this is NOAA-20. Description says so.
2. **Detections in source** `#,0` (Detections). `COUNTROWS ( 'Fact Detection' )`. One source per row. The total of a source matrix is blank if the total context contains more than one source; do not let Power BI sum the three rows by writing a measure that adds them.
3. **Vegetation detections** `#,0` (Detections). The rule around rows with Type Code `0`.
4. **High confidence detections** `#,0` (Detections). The rule around `Confidence Band = "High"`.
5. **High confidence share** `0.0%` (Detections). `DIVIDE ( [High confidence detections], [Detections] )`. Same source on both sides.
6. **Day share** `0.0%` (Detections). `DIVIDE ( CALCULATE ( [Detections], 'Day Night'[Day Night] = "Day" ), [Detections] )`.
7. **Satellites in scope** `0` (Detections). `DISTINCTCOUNT ( 'Fact Detection'[Satellite] )` under the same rule. MODIS can be 2. NOAA-20 is 1.

FRP. Sum of pixel FRP inside one source. Not a sum of unique fires, and not comparable between VIIRS and MODIS as a physical total (different pixel size).

8. **Total FRP** `#,0.0` (FRP). The rule around `SUM ( 'Fact Detection'[FRP] )`.
9. **Average FRP** `0.00` (FRP). `DIVIDE ( [Total FRP], [Detections] )`. Mean of pixels in context, not the FRP of a fire.
10. **Vegetation FRP** `#,0.0` (FRP). The rule around `CALCULATE ( SUM ( 'Fact Detection'[FRP] ), 'Hotspot Type'[Type Code] = "0" )`.

Time. Blank when the date filter runs past the last acquisition date in the model, including a year row whose calendar continues after the data.

11. **Last Acq Date** `yyyy-mm-dd` (Time). `CALCULATE ( MAX ( 'Fact Detection'[Acq Date] ), REMOVEFILTERS () )`. Hidden.
12. **Detections YTD** `#,0` (Time). `IF ( MAX ( 'Date'[Date] ) <= [Last Acq Date], TOTALYTD ( [Detections], 'Date'[Date] ) )`.
13. **Detections prior year** `#,0` (Time). `CALCULATE ( [Detections], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`. Shifts the UTC acquisition date only.
14. **Detections YoY %** `+0.0%;-0.0%;0.0%` (Time). `IF ( NOT ISBLANK ( [Detections] ), DIVIDE ( [Detections] - [Detections prior year], [Detections prior year] ) )`.
15. **FRP prior year** `#,0.0` (Time). `CALCULATE ( [Total FRP], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )`.
16. **FRP YoY %** `+0.0%;-0.0%;0.0%` (Time). Same shape as detections YoY, on Total FRP.
17. **Peak day** `yyyy-mm-dd` (Time). The Acq Date in context with the most Detections. `MAXX ( TOPN ( 1, ADDCOLUMNS ( VALUES ( 'Date'[Date] ), "@N", [Detections] ), [@N] ), 'Date'[Date] )`. Ties keep the latest date `TOPN` returns; say that. For a full year of NOAA-20 Portugal there is no tie.
18. **Peak day detections** `#,0` (Time). Detections on that date.

Audit

19. **Static land detections** `#,0` (Audit). The rule around Type Code `2`.
20. **Low confidence detections** `#,0` (Audit). The rule around Confidence Band Low.

## Power Query M

Read the index, keep the three products and the country list, and append. Tag Source from the filename so VIIRS is not one bucket.

```powerquery
let
    Index = Csv.Document(Web.Contents("https://firms.modaps.eosdis.nasa.gov/data/country/yearly_summary_files.txt"), [Delimiter = ",", Encoding = 65001]),
    Promoted = Table.PromoteHeaders(Index, [PromoteAllScalars = true]),
    // Scope for the sample answers. For United States, Canada, and Australia 2025, change Countries and Years only.
    Products = {"viirs-jpss1", "viirs-snpp", "modis"},
    Years = {"2024", "2025"},
    Countries = {"Portugal"},
    SourceOf = (product as text) as text =>
        if product = "viirs-jpss1" then "VIIRS NOAA-20"
        else if product = "viirs-snpp" then "VIIRS S-NPP"
        else "MODIS",
    Wanted = Table.SelectRows(Promoted, each
        List.Contains(Products, Text.BeforeDelimiter([filename], "_"))
        and List.Contains(Years, Text.BetweenDelimiters([filename], "_", "_"))
        and List.AnyTrue(List.Transform(Countries, (c) => Text.EndsWith([filename], "_" & c & ".csv")))),
    ReadOne = (file as text) as table =>
        let
            Product = Text.BeforeDelimiter(file, "_"),
            Year = Text.BetweenDelimiters(file, "_", "_"),
            Bin = Web.Contents("https://firms.modaps.eosdis.nasa.gov/data/country/" & Product & "/" & Year & "/" & file),
            Csv = Csv.Document(Bin, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            Headers = Table.PromoteHeaders(Csv, [PromoteAllScalars = true]),
            Tagged = Table.AddColumn(Headers, "Source", each SourceOf(Product), type text)
        in
            Tagged,
    Stacked = Table.Combine(List.Transform(Wanted[filename], ReadOne)),
    Band = Table.AddColumn(Stacked, "Confidence Band", each
        if [instrument] = "VIIRS" then
            if [confidence] = "h" then "High" else if [confidence] = "n" then "Nominal" else if [confidence] = "l" then "Low" else null
        else
            let n = Number.FromText([confidence]) in
            if n >= 80 then "High" else if n >= 30 then "Nominal" else "Low", type text),
    Day = Table.AddColumn(Band, "Day Night", each if [daynight] = "D" then "Day" else if [daynight] = "N" then "Night" else null, type text)
in
    Day
```

Do not append a 7-day file on top of the archive. Do not union NOAA-20 and S-NPP under `instrument = VIIRS`.

## Questions

All figures are Portugal. Detections and FRP are VIIRS NOAA-20 unless the question names another source. Blanks were not present in FRP in these six files. High means VIIRS `h`, or MODIS confidence 80 or above.

1. How many NOAA-20 detections in 2025? **13,862.** In 2024, **12,010.**
2. Year-on-year change in NOAA-20 detections, 2025 against 2024? **+15.4%** (1,852 more). NOAA-20 FRP went from **215,547.16 MW** to **339,014.73 MW**, **+57.3%.**
3. What if someone adds NOAA-20, S-NPP, and MODIS for 2025? **32,329** rows and **1,394,438.56 MW**. The model returns blank for that selection on purpose.
4. Peak UTC day for NOAA-20 in 2025? **15 Aug 2025**, **3,597** detections, **126,836.80 MW** of FRP. In 2024 the peak UTC day was **17 Sep 2024**, **5,399** detections.
5. Which month in 2025 had the most NOAA-20 detections? **August, 10,036** of 13,862 (**72.4%**).
6. High-confidence share, NOAA-20 2025? **1,935 / 13,862 = 14.0%.** The rest are nominal 11,135 and low 792.
7. Day share, NOAA-20 2025? **6,414 / 13,862 = 46.3%** day. Night is the rest, 7,448.
8. How many of the 2025 NOAA-20 rows are presumed vegetation (type 0)? **13,521**, FRP **338,615.76 MW**. Static land sources: **339**. Offshore: **2**.
9. S-NPP 2025, kept as its own source? **13,600** detections, high-confidence share **1,962 / 13,600 = 14.4%**, peak day the same UTC date, **15 Aug 2025**, with **2,608** detections. Not added to NOAA-20.
10. MODIS 2025, Terra and Aqua together, still not added to VIIRS? **4,867** detections (Terra 2,459, Aqua 2,408), total FRP **700,319.20 MW**, average FRP **143.89 MW**, high-confidence share **3,166 / 4,867 = 65.1%**. The higher MODIS FRP is the 1 km pixel, not a bigger fire season than NOAA-20.
