# NASA FIRMS Active Fires

A star-schema semantic model of satellite active-fire detections from NASA's Fire Information for Resource
Management System (FIRMS): every hotspot pixel that VIIRS on NOAA-20, VIIRS on Suomi NPP, and MODIS on Terra and Aqua
saw over a country, with its fire radiative power (FRP), confidence and hotspot type. Loaded by default: Portugal,
2024 and 2025.

## Source

- **Publisher:** NASA LANCE FIRMS, [country yearly files](https://firms.modaps.eosdis.nasa.gov/country/), listed in
  [`yearly_summary_files.txt`](https://firms.modaps.eosdis.nasa.gov/data/country/yearly_summary_files.txt) and read
  from `https://firms.modaps.eosdis.nasa.gov/data/country/{product}/{year}/{product}_{year}_{Country}.csv`. Products
  `viirs-jpss1` (NOAA-20, 375 m), `viirs-snpp` (Suomi NPP, 375 m), `modis` (Terra and Aqua, 1 km, Collection 6.1).
  These are the archive (standard processing: VIIRS version 2, MODIS 61.03), not near-real-time rows. Field notes:
  [`AttributesReadme.txt`](https://firms.modaps.eosdis.nasa.gov/data/country/AttributesReadme.txt).
- **Files checked here:** the six Portugal files for 2024 and 2025 (4.7 MB, 59,568 rows), committed in
  `samples/firms/` (download from the source; not committed).
- **Licence:** NASA Earth science data from a NASA-led mission is open, with no restriction on reuse (Creative Commons
  Zero unless a product page says otherwise:
  [NASA data use guidance](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance)).
  No MAP_KEY and no Earthdata login is needed for the country files.
- **Required citation** (NASA asks anyone who passes LANCE/FIRMS data to a third party to follow its citation
  guidelines and carry the disclaimer; `AttributesReadme.txt`). Put this on every report built from the model; it is
  the model's `Citation` measure and a model annotation:

  > We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS)
  > (https://www.earthdata.nasa.gov/firms), part of NASA's Earth Science Data and Information System (ESDIS).
  > Data: NASA LANCE FIRMS country yearly active-fire CSVs (MODIS C6.1, VIIRS S-NPP, VIIRS NOAA-20), accessed 24 Nov
  > 2026, https://firms.modaps.eosdis.nasa.gov/data/country/.

- **Disclaimer** (NASA's, carried as the `Disclaimer` measure and a model annotation):

  > The LANCE system is operated by the NASA/GSFC Earth Science Data and Information System (ESDIS). The information
  > presented through LANCE, Rapid Response, GIBS, Worldview, and FIRMS are provided "as is" and users bear all
  > responsibility and liability for their use of data. Full disclaimer: https://www.earthdata.nasa.gov/data/tools/firms

- **Algorithm references** (not the licence): Schroeder, Oliva, Giglio, Csiszar, "The New VIIRS 375 m active fire
  detection data product", Remote Sensing of Environment 143 (2014), doi:10.1016/j.rse.2013.12.008; Giglio et al.,
  the MODIS Collection 6 active fire product.
- **Refreshed by:** Power Query M in the model, anonymous, from the one Web source `https://firms.modaps.eosdis.nasa.gov/`
  (the root answers 200; `data/country/` answers 404, so every file is a `RelativePath`).

### Field caveats

- **A detection is not a fire.** One fire is seen on every overpass and by every satellite.
- **Never add the products.** Portugal 2025 across NOAA-20, S-NPP and MODIS is 32,329 rows and 1,394,438.56 MW: the
  same fires two or three times. The model returns blank for that selection (the source rule, below).
- **FRP is pixel megawatts,** not burned area and not the power of a fire. VIIRS and MODIS totals are not comparable
  (375 m vs 1 km pixels: MODIS 2025 averages 143.89 MW a pixel, NOAA-20 24.46). There is no burned-area measure;
  that is a different product (MCD64A1 / VNP64A1).
- **Dates are UTC.** Portugal is UTC+1 in summer, so a detection at 23:30 UTC on 15 Aug is 16 Aug locally. The model
  has one date, the UTC acquisition date; it does not build a local date on the same table.
- **Every hotspot type is counted** by default (Portugal 2025 NOAA-20: 13,521 vegetation, 339 static land source,
  2 offshore); vegetation measures keep type 0.
- Latitude and longitude are fixed decimal to four places (about 11 m; the pixel is 375 m or 1 km).

## Grain and size

`Fact Detection`: one row per **detection** (one pixel, one overpass, one product). Portugal 2024 and 2025: 59,568
rows (NOAA-20 25,872, S-NPP 25,678, MODIS 8,018). Detection Key (source, date, time, latitude, longitude) is unique.

## Star schema

```
Source (3)          1 --* Fact Detection *-- 1  Date (UTC acquisition date)
Satellite (4)       1 --* Fact Detection *-- 1  Country
Confidence Band (3) 1 --* Fact Detection *-- 1  Day Night (2)
                          Fact Detection *-- 1  Hotspot Type (4)
```

Every relationship is many-to-one, single direction. One date, one date table.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Detection | 59,568 | none (all columns hidden) | measures only |
| Source | 3 | Source | Source (NOAA-20 first), Instrument, Pixel |
| Satellite | 4 | Satellite (N20, N, Terra, Aqua) | Satellite, Satellite Name, Source |
| Country | one per country loaded | Country | Country |
| Confidence Band | 3 | Confidence Band | Low, Nominal, High (VIIRS l/n/h; MODIS under 30, 30 to 79, 80 and over) |
| Day Night | 2 | Day Night | Day, Night (the satellite's flag, not local time) |
| Hotspot Type | 4 | Type Code | Hotspot Type (vegetation, volcano, static land source, offshore) |
| Date | one per day, 1 Jan FirstYear to 31 Dec LastYear | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month, Month Start |

## Parameters and shared queries

| Name | Default | Purpose |
|---|---|---|
| `FirmsBaseUrl` | `https://firms.modaps.eosdis.nasa.gov/` | The one Web data source |
| `Countries` | `Portugal` | Comma-separated FIRMS country names (`United_States`, `Canada`, ...) |
| `FirstYear`, `LastYear` | 2024, 2025 | Calendar years to load; the Date table spans the same whole years |
| `FirmsDetections` | shared, not loaded | The index filtered to the three products, countries and years; every file read, tagged with its source and country, typed |
| `Calendar` | shared, not loaded | The calendar the Date table loads |

No incremental refresh: six files, 4.7 MB; a full refresh took 14 s on an F2. The same model scales by parameter:
the United States, Canada and Australia for 2025 are about 470 MB of CSV (not loaded here).

## The source rule

Every measure in the Detections, FRP and Time folders applies it: **no Source or Satellite picked -> VIIRS NOAA-20
only; exactly one source picked (by Source, or by satellites that all belong to one source, such as Terra + Aqua) ->
that source; two or three sources picked -> blank.** NOAA-20 is the default because it is the newest 375 m sensor with
a full archive for these years (Suomi NPP stopped new observations on 2 Nov 2026). For a matrix with Source on rows,
use `Detections in source`: it shows each source on its own row and leaves the total blank, so the rows are never
summed. This is the same shape as Census Retail refusing to add the two seasonal adjustments.

## Measures (23)

| Folder | Measures |
|---|---|
| Detections | Detections, Detections in source, Vegetation detections, High confidence detections, High confidence share, Day share, Satellites in scope |
| FRP | Total FRP, Average FRP, Vegetation FRP |
| Time | Detections YTD, Detections prior year, Detections YoY %, FRP prior year, FRP YoY %, Peak day, Peak day detections, Last Acq Date (hidden) |
| Audit | Static land detections, Low confidence detections, All product rows (hidden: adds products, audit only) |
| About | Citation, Disclaimer |

- `Peak day` is the UTC date in context with the most detections; on a tie, the latest tied date.
- YTD is blank for a period that starts after the last acquisition date; prior year shifts only the days up to the
  last acquisition date (the repo's convention).

## Ten business questions (acceptance checks)

Portugal; NOAA-20 unless the question names another source. Expected answers are from Grok's design
(`design/nasa-firms.md`), recomputed independently from the six raw CSVs with Python (`csv` + `Decimal`) before
deploying; `tests/checks.dax` asks each one of the deployed model.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | NOAA-20 detections, 2025 and 2024 | 13,862; 12,010 | 13,862; 12,010 | Pass |
| 2 | Year on year, 2025 vs 2024 | +15.4%; FRP 339,014.73 vs 215,547.16 MW, +57.3% | +15.42%; identical FRP, +57.28% | Pass |
| 3 | All three products added, 2025 | 32,329 rows, 1,394,438.56 MW; the model returns blank | Detections, Total FRP and Detections in source blank; audit rows 32,329 | Pass |
| 4 | Peak UTC day | 2025-08-15, 3,597, 126,836.80 MW; 2024-09-17, 5,399 | identical | Pass |
| 5 | Month with the most detections, 2025 | August, 10,036 of 13,862 (72.4%) | August 10,036, 72.40% | Pass |
| 6 | High-confidence share, 2025 | 1,935 / 13,862 = 14.0%; nominal 11,135; low 792 | identical (13.96%) | Pass |
| 7 | Day share, 2025 | 6,414 / 13,862 = 46.3%; night 7,448 | identical (46.27%) | Pass |
| 8 | Presumed vegetation, 2025 | 13,521, FRP 338,615.76 MW; static land 339; offshore 2 | identical | Pass |
| 9 | S-NPP 2025 on its own | 13,600; high 1,962 (14.4%); peak 2025-08-15 with 2,608 | identical | Pass |
| 10 | MODIS 2025, Terra and Aqua together | 4,867 (Terra 2,459, Aqua 2,408); FRP 700,319.20; average 143.89; high 3,166 (65.1%) | identical; satellites in scope 2 | Pass |

Also checked: Terra + Aqua picked as satellites = 4,867 (one source), NOAA-20 + Terra = blank; the source matrix
shows 13,862 / 13,600 / 4,867 per row; unfiltered `Detections` = 25,872 (NOAA-20, both years) and unfiltered
`Detections in source` blank; YTD June 2025 773, prior year for August 2025 699; 59,568 rows, 59,568 distinct keys,
zero orphan keys on every relationship; all 23 measures evaluate.

## Changes from the design (`design/nasa-firms.md`)

- **Fact columns are hidden, so the sliceable fields are dimensions:** Confidence Band, Day Night, Hotspot Type and
  Country are tables, not visible fact columns.
- **The source rule counts sources from both Source and Satellite** (`INTERSECT` of the sources each allows), not
  `ISFILTERED ( Source )` alone: with the design's version, picking Terra left Source unfiltered, so the rule forced
  NOAA-20 and Terra returned blank.
- **Satellite is related to the fact directly** (not through Source), with a `Source` label column the rule reads.
- **One data source.** `Web.Contents` on the site root with `RelativePath` for the index and every file, because the
  service's credential test calls the root and `data/country/` answers 404.
- **Countries and years are parameters** and the Date table follows them, instead of a fixed list in M and a fixed
  2024 to 2025 calendar.
- **`Peak day` uses `TOPN` over the dates ordered by `[Detections]`** directly (no added column).
- **Added:** `All product rows` (hidden, audit: proves the products-added figure without exposing it), `Disclaimer`,
  `Country`. Brightness and coordinates are fixed decimal.
- **YTD guard and prior year follow the repo's convention**, not the design's "blank past the last date".

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/nasa-firms/NasaFirms.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except one deliberate warning
(PRF3, incremental refresh: six small yearly files). TmdlCheck first failed `Peak day`'s reference to an added column
(`[DayDetections]`); rewritten without it.

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in 14 s**, 10/10, all 23 measures evaluate. Details in the
[run log](../../docs/toolchain.md#run-log).
