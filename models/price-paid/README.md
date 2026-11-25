# HM Land Registry Price Paid

A star-schema semantic model of residential property sales in England and Wales from HM Land Registry's Price Paid
Data: sales counts, median and mean prices, consideration, price bands, mix by place, property type, tenure and build,
and month-on-month comparisons. No address-level field is in the model.

> Contains HM Land Registry data © Crown copyright and database right 2026. This data is licensed under the Open
> Government Licence v3.0.

## Source

- **Publisher:** HM Land Registry, [Price Paid Data downloads](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads).
- **File:** `https://price-paid-data.publicdata.landregistry.gov.uk/pp-monthly-update-new-version.csv`, the current
  monthly update (CSV, no header, 16 columns). The copy checked here: 17,108,738 bytes, Last-Modified 28 Oct 2026,
  98,103 rows. The `PricePaidUrl` parameter can point at `pp-complete.csv` or a yearly file instead; the shaping is
  the same.
- **Licence:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
  Copying, publishing and commercial use are allowed with the attribution above, which the model also carries: the
  `Attribution` measure (folder About; put it on every report page, the year follows the latest transfer loaded), the
  `Fact Sale` and `PricePaidUrl` descriptions and a model annotation.
- **Refreshed by:** Power Query M in the model (`Csv.Document` + `Web.Contents`), anonymous, no API key. The Web data
  source is the full file URL (the bare host answers 403, which would fail the service's credential test). Full refresh
  on an F2: 8 s.
- **The raw file is not in this repo.** `samples/price-paid-monthly.csv` (download from the source; not committed) is gitignored: it carries the address
  columns.

### Personal data and addresses

HM Land Registry's guidance ([About the Price Paid Data](https://www.gov.uk/guidance/about-the-price-paid-data))
says users have an obligation under the Open Government Licence to make sure their use does not breach the Data
Protection Act 2018 or the Privacy and Electronic Communications Regulations 2003 (it addresses direct marketing in
particular). It also says the OGL does not cover third-party rights: the address data is processed against Ordnance
Survey AddressBase Premium, which incorporates Royal Mail PAF, and Royal Mail and Ordnance Survey permit its use only
for personal or non-commercial use or to display residential property price information; any other use needs Royal
Mail's permission. So the model **never loads** postcode, PAON (house number or
name), SAON (flat), street or locality: the shared query `PricePaid` selects the other columns by position before
anything is named or typed. The finest geography is town within district. Do not join this model back to addresses,
and do not use it to profile individuals.

### Field caveats

- **A monthly update is not a month of sales.** The file holds the records added, changed or deleted that month, with
  transfer dates from 1995 on; the newest months are still arriving (Land Registry: registration typically lags the sale by 2 weeks to 2 months, so the two most recent months are incomplete).
  August 2026 is its busiest transfer month. A fall into September is registration timing, not the market.
- **Standard vs additional.** Category A (standard) is a single residential property sold for value; category B
  (additional) is repossessions, buy-to-lets identified by a mortgage, non-private buyers and property typed Other.
  Every price and sales measure reads standard, not-deleted records only.
- **Deleted is not a sale.** Status D withdraws an earlier record. When monthly files are appended into a history,
  keep the latest status per transaction id and drop deletes (this file has one row per id).
- **New builds** are registered late: only 9 standard August 2026 transfers are flagged new in this file.
- Place names are as published, upper case (`GREATER LONDON`). The file has no region; Scotland and Northern Ireland
  are not covered.

## Grain and size

`Fact Sale` holds one row per **transaction id** in the file: 98,103 rows (79,318 standard sales, 17,233 additional
transfers, 1,552 deletes), transfer dates 6 Jan 1995 to 30 Sep 2026; 1,816 locations, 320 districts, 114 counties.

## Star schema

```
                  Date (marked, daily)
                        | 1
                        |
   Location 1 ----- * Fact Sale * ----- 1 Property Type
   Duration 1 -----/  |   |    \----- 1 Build
              Category 1   1 Record Status
```

All seven relationships are many-to-one from the fact, single direction, active.

| Table | Rows | Key | Visible attributes |
|---|---|---|---|
| Fact Sale | 98,103 | none (all columns hidden) | measures only |
| Date | one per day, 1 Jan 1995 to 31 Dec of the refresh year | Date | Year, Quarter, Year Quarter, Month, Month Short, Month Number, Year Month (`YYYY-MM`), Month Start |
| Location | 1,816 | Location Key (`District\|Town`, hidden) | Town, District, County |
| Property Type | 5 | Property Type Code (hidden) | Property Type (Detached, Semi-detached, Terraced, Flat or maisonette, Other, in that order) |
| Duration | 3 | Duration Code (hidden) | Duration (Freehold, Leasehold, Unknown) |
| Build | 2 | Build | Build (New build, Established) |
| Category | 2 | Category | Category, Category Code |
| Record Status | 4 | Record Status | Record Status (Added, Changed, Deleted, Other) |

## Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `PricePaidUrl` | the monthly update URL above | The one Web data source |
| `CalendarStart` | 1995-01-01 | First day of the Date table (Price Paid starts in 1995) |
| `CalendarEnd` | 31 December of the current year (computed) | Whole years |

`PricePaid` is a shared, unloaded query that reads the file once (dropping the address columns) and feeds the fact
and Location. No incremental refresh: one 17 MB file.

## Measures (19)

| Folder | Measures |
|---|---|
| Volume | Sales |
| Price | Median price, Mean price, Total consideration, Lowest price, Highest price |
| Mix | Share of sales, Freehold share, New build sales, Sales under £250,000, Sales of £1 million or more, Share of consideration |
| Time | Sales prior month, Median price prior month, Median price change |
| Audit | All records, Deleted records, Additional transfers |
| About | Attribution |

- **Median is the headline price**; the mean is pulled up by a few very high sales and is labelled as the mean.
  Price is never summed into something that reads as a count (Total consideration is the money, not a price).
- **Shares** remove location, property type, tenure and build filters and keep dates.
- **Prior month** shifts dates back one month. No year-on-year measure: in one update file older months hold only
  late registrations, so a year-on-year move would not be the market's.

## Ten business questions (acceptance checks)

Standard sales (category A, not deleted), pinned to the 28 Oct 2026 file; months are transfer months. Expected
answers were recomputed from the raw CSV with Python (csv, statistics), independently of the M; `tests/checks.dax`
asks each one of the deployed model.

| # | Question | Expected | Model (24 Nov 2026) | |
|---|---|---|---|---|
| 1 | All standard sales, Aug 2026 | 25,403; median £295,000; mean £359,379; total £9,129,314,595 | same | Pass |
| 2 | Greater London, Aug 2026 | 2,500; median £515,000; mean £630,675; 17.3% of consideration | 2,500; £515,000; £630,675; 17.27% (9.84% of sales) | Pass |
| 3 | Surrey, Aug 2026 | 593; median £490,000; mean £591,964 | same | Pass |
| 4 | County Durham, Aug 2026 | 210; median £156,500; mean £183,957 | same | Pass |
| 5 | Detached, Aug 2026 | 6,434; median £425,000; mean £505,991 | same (25.3% of sales) | Pass |
| 6 | Flats; semi-detached; terraced, Aug 2026 | 3,803 at £225,000; 7,873 at £280,000; 7,293 at £245,000 | same; Other blank | Pass |
| 7 | Leasehold flats in Greater London, Aug 2026 | 1,168; median £400,000; mean £460,679 | same | Pass |
| 8 | Freehold share, Aug 2026 | 20,475 of 25,403, 80.6% | 20,475 of 25,403, 80.60% | Pass |
| 9 | Under £250,000; £1 million or more, Aug 2026 | 9,426; 563 | 9,426; 563 | Pass |
| 10 | Standard sales, Sep 2026, same file | 18,508; median £300,000; mean £360,353 | same | Pass |

Also checked (every measure evaluated): July 2026 4,302 sales at a £280,000 median, so Median price change +£15,000;
9 new-build sales; August all records 28,131, 75 deleted, 2,653 additional; lowest £10,000, highest £15,600,000;
whole file 98,103 records, 1,552 deleted, 17,233 additional, 79,318 sales, median £300,000; the Attribution text;
1,816 locations, 320 districts, 114 counties; zero orphan keys on all seven relationships. All matched the raw file.

## Changes from the design (`design/price-paid.md`)

- **Location instead of District → County.** The design snowflaked District to County and left Town on the fact; a
  flat Location dimension (town within district, with county) keeps the star one hop deep and makes Town sliceable.
  Region is not in the file, so it is not in the model.
- **Small dimensions for Build, Category and Record Status** instead of visible fact columns (fact columns stay
  hidden); Duration gains Unknown (`U`, in historic files).
- **Data source is the full file URL**, not the host (403).
- **Filters use KEEPFILTERS**, so Freehold share under a Leasehold filter reads 0, not the overall share.
- **Added:** Attribution measure; Median price change is blank unless both months have sales.

## Validation

**TOM on macOS** (`dotnet run --project tools/TmdlCheck -- models/price-paid/PricePaid.SemanticModel/definition`):
deserializes, `Model.Validate()` has no errors, round-trips, and all 30 rules pass except one deliberate warning:
PRF3 (incremental refresh on the fact), skipped because the source is one 17 MB file.

Model #3's lesson (TmdlCheck passed a measure the engine rejected) is why `tests/checks.dax` queries every measure.

**In a Fabric workspace (24 Nov 2026, F2):** deployed with `fab import` to Semantic Models Lab, anonymous credentials
on the one Web source, full refresh **Completed in 8 s**, all 19 measures evaluated, and the 10 questions matched
**10/10**. Details in the [run log](../../docs/toolchain.md#run-log).
