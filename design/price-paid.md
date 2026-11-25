# HM Land Registry Price Paid

Model #5. Real estate. Open Government Licence v3.0, which allows copying and republishing, including commercially, with the attribution below. Verified on the downloads page, 24 Nov 2026: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads. One monthly file, 17 MB. No API key. Every answer was computed from that file.

Attribution, which the model and any report must carry: Contains HM Land Registry data © Crown copyright and database right 2026. Licensed under the Open Government Licence v3.0.

## What not to store

The same page says the address fields were matched to Ordnance Survey AddressBase, which includes Royal Mail PAF. OGL does not cover that. **Do not load, and do not commit, postcode, PAON, SAON, street, or locality.** Town, district, and county are the geography this model keeps. The sample file on disk still has the address columns because that is how Land Registry publishes it. The Power Query below drops them before they reach a table. Do not ship the raw CSV in a public repo. Ship the design and a note of the URL.

## Source

| Item | Value |
|---|---|
| Downloads | https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads |
| This file's page | https://www.gov.uk/government/statistical-data-sets/price-paid-data-september-2026 (the “current month” link; the page name lags the file) |
| URL | https://price-paid-data.publicdata.landregistry.gov.uk/pp-monthly-update-new-version.csv |
| Size | 17,108,738 bytes. Last-Modified Wed, 28 Oct 2026 10:12:02 GMT. The page calls it 17.9 MB. |
| Saved as | `samples/price-paid-monthly.csv` (download from the source; not committed) |
| Shape | No header. 98,103 rows, 16 columns, no duplicate transaction id. |
| What the file is | The monthly update of records added, changed, or deleted, not “sales that completed in one month.” Transfer dates run from 6 Jan 1995 to 30 Sep 2026. August 2026 is the busiest transfer month in the file (28,131 rows of any category). |

Columns, in order: transaction id, price (pounds), transfer datetime, postcode, property type, old/new, duration, PAON, SAON, street, locality, town, district, county, PPD category, record status.

| Code | Meaning |
|---|---|
| Property type D, S, T, F, O | Detached, semi-detached, terrace, flat, other |
| Old/new Y, N | New build, or not |
| Duration F, L | Freehold, leasehold |
| PPD category A | Standard Price Paid. Use this for a house-price question |
| PPD category B | Additional (repossessions and other non-standard transfers). 17,584 rows. Keep the flag. Do not mix into the median |
| Record status A, C, D | Added, changed, deleted. 93,495 / 3,056 / 1,552. A delete is not a sale |

## Grain

One fact row per **transaction id** in this monthly file. The date role is the transfer date. A later month's file can carry the same id again with status C or D. When history is appended, keep the latest status per id and drop D. This sample has one row per id, so that rule changes nothing yet.

## Star schema

### Fact Sale

| Column | Type | Notes |
|---|---|---|
| Transaction ID | text | key. The `{GUID}` with braces kept |
| Transfer Date | date | time stripped. FK to Date |
| Price GBP | int64 | pounds. Hidden from default aggregates. Medians must not be a SUM |
| Property Type | text | FK |
| New Build | bool | Y → true |
| Duration | text | FK. Freehold or Leasehold |
| Town | text | |
| District | text | FK |
| County | text | FK to County, through District |
| Category | text | Standard or Additional |
| Record Status | text | Added, Changed, Deleted |
| Is Standard Sale | bool | Category = Standard and Record Status ≠ Deleted. The additive and median measures use this |

Address columns never appear.

### Date (marked date table)

Daily from 1 Jan 1995 through 31 Dec 2026. `Date`, `Year`, `Month Number`, `Month`, `Year Month`, `Year Month Sort`, `Quarter`. Mark on `Date`. Auto date/time off.

### Property Type

`D` Detached, `S` Semi-detached, `T` Terrace, `F` Flat, `O` Other. `Sort` 1–5.

### Duration

`F` Freehold, `L` Leasehold.

### District

`District`, `County`, `Town` is not a key (one district has many towns). Key is District, which is unique in this file's pairing with county. Check before relating: the relationship is District → County, many districts to one county.

### County

`County` key. England and Wales only. Price Paid does not cover Scotland or Northern Ireland.

### Relationships

| From | To | Cardinality | Filter |
|---|---|---|---|
| Fact[Transfer Date] | Date[Date] | many to one | single |
| Fact[Property Type] | Property Type[Code] | many to one | single |
| Fact[Duration] | Duration[Code] | many to one | single |
| Fact[District] | District[District] | many to one | single |
| District[County] | County[County] | many to one | single |

## Measures

Folder in parentheses. Every price measure is filtered to `Is Standard Sale` unless its name says all records. Price is not summed into a “total sales” that a user might read as a count.

Volume

1. **Sales** `#,0` (Volume). `CALCULATE ( COUNTROWS ( 'Fact Sale' ), 'Fact Sale'[Is Standard Sale] )`. Standard transfers that were not deleted.
2. **All records** `#,0` (Audit). `COUNTROWS ( 'Fact Sale' )`. Includes additional and deleted.
3. **Deleted records** `#,0` (Audit). `CALCULATE ( [All records], 'Fact Sale'[Record Status] = "Deleted" )`.
4. **Additional transfers** `#,0` (Audit). Category = Additional, not deleted.

Price. Use median, not mean, as the headline. Mean is pulled by a few high sales.

5. **Median price** `£#,0` (Price). A DAX median over standard sales: `MEDIAN ( 'Fact Sale'[Price GBP] )` inside `CALCULATE` that keeps `Is Standard Sale`. `MEDIAN` ignores the filter if you forget the calculate. Write it as `CALCULATE ( MEDIAN ( 'Fact Sale'[Price GBP] ), 'Fact Sale'[Is Standard Sale] )`.
6. **Mean price** `£#,0` (Price). `CALCULATE ( AVERAGE ( 'Fact Sale'[Price GBP] ), 'Fact Sale'[Is Standard Sale] )`. Say it is the mean.
7. **Total consideration** `£#,0` (Price). `CALCULATE ( SUM ( 'Fact Sale'[Price GBP] ), 'Fact Sale'[Is Standard Sale] )`. The sum of prices, not a typical price.
8. **Lowest price** `£#,0` (Price). `CALCULATE ( MIN ( 'Fact Sale'[Price GBP] ), 'Fact Sale'[Is Standard Sale] )`.
9. **Highest price** `£#,0` (Price). `MAX` with the same filter. Do not put this on a visual that also shows street. Street is not in the model.

Mix

10. **Share of sales** `0.0%` (Mix). `DIVIDE ( [Sales], CALCULATE ( [Sales], ALL ( District ), ALL ( County ), ALL ( 'Property Type' ), ALL ( Duration ) ) )`. Date stays.
11. **Freehold share** `0.0%` (Mix). `DIVIDE ( CALCULATE ( [Sales], Duration[Code] = "F" ), [Sales] )`.
12. **New build sales** `#,0` (Mix). `CALCULATE ( [Sales], 'Fact Sale'[New Build] )`.
13. **Sales under £250,000** `#,0` (Mix). Standard sales with price &lt; 250000.
14. **Sales of £1 million or more** `#,0` (Mix). Price ≥ 1000000.
15. **Share of consideration** `0.0%` (Mix). This county's or type's total consideration divided by all standard consideration in the same dates.

Time

16. **Sales prior month** `#,0` (Time). `CALCULATE ( [Sales], DATEADD ( 'Date'[Date], -1, MONTH ) )`.
17. **Median price prior month** `£#,0` (Time). Same shift around the median.
18. **Median price change** `+£#,0;-£#,0;£0` (Time). `[Median price] - [Median price prior month]`. Prior year is a weak comparison in a single monthly file, because older transfers are only the ones registered late. Do not label a year-on-year move from this file as the market's year-on-year move.

## Power Query M

```powerquery
let
  Source = Csv.Document(Web.Contents("https://price-paid-data.publicdata.landregistry.gov.uk/pp-monthly-update-new-version.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
  Named = Table.RenameColumns(Source, {
    {"Column1","Transaction ID"},{"Column2","Price GBP"},{"Column3","Transfer"},
    {"Column5","Property Type"},{"Column6","New Build Flag"},{"Column7","Duration"},
    {"Column12","Town"},{"Column13","District"},{"Column14","County"},
    {"Column15","Category Code"},{"Column16","Status Code"}}),
  // Column4 postcode, Column8 PAON, Column9 SAON, Column10 street, Column11 locality are never renamed and never selected
  Keep = Table.SelectColumns(Named, {"Transaction ID","Price GBP","Transfer","Property Type","New Build Flag","Duration","Town","District","County","Category Code","Status Code"}),
  Typed = Table.TransformColumnTypes(Keep, {{"Price GBP", Int64.Type}, {"Transfer", type datetime}}),
  Dated = Table.AddColumn(Typed, "Transfer Date", each Date.From([Transfer]), type date),
  Flags = Table.AddColumn(Table.AddColumn(Dated, "New Build", each [New Build Flag] = "Y", type logical), "Is Standard Sale", each [Category Code] = "A" and [Status Code] <> "D", type logical),
  Labels = Table.AddColumn(Table.AddColumn(Flags, "Category", each if [Category Code] = "A" then "Standard" else "Additional"), "Record Status", each if [Status Code] = "A" then "Added" else if [Status Code] = "C" then "Changed" else "Deleted"),
  Fact = Table.SelectColumns(Labels, {"Transaction ID","Transfer Date","Price GBP","Property Type","New Build","Duration","Town","District","County","Category","Record Status","Is Standard Sale"})
in
  Fact
```

Property Type, Duration, District, County, and Date are built from the fact columns after this, plus the five type names and the two duration names entered in small tables and merged. Date is every day from the minimum transfer date through the maximum, not only the dates that occur.

## Ten questions

Standard Price Paid only (category A), record status not Deleted. August 2026 means the transfer date, inside this 28 Oct 2026 update file. It is not the official monthly count of the England and Wales market. Late registrations and this file's deletes are missing or extra relative to a full history.

| # | Question | Expected |
|---|---|---|
| 1 | How many standard sales transferred in August 2026, and what was the median price? | 25,403 sales. Median £295,000. Mean £359,379. Total consideration £9,129,314,595. |
| 2 | Greater London, same month | 2,500 sales. Median £515,000. Mean £630,675. London is 17.3% of August consideration. |
| 3 | Surrey, same month | 593 sales. Median £490,000. Mean £591,964. |
| 4 | County Durham, same month | 210 sales. Median £156,500. Mean £183,957. |
| 5 | Detached houses, August 2026 | 6,434 sales. Median £425,000. Mean £505,991. |
| 6 | Flats, and semi-detached, and terraces, August 2026 | Flats 3,803, median £225,000. Semi-detached 7,873, median £280,000. Terraces 7,293, median £245,000. |
| 7 | Leasehold flats in Greater London, August 2026 | 1,168 sales. Median £400,000. Mean £460,679. |
| 8 | Freehold share, August 2026 | 20,475 of 25,403, which is 80.6%. |
| 9 | Under £250,000, and £1 million or more, August 2026 | 9,426 under £250,000. 563 at £1 million or more. |
| 10 | Standard sales transferred in September 2026 in this same file | 18,508 sales. Median £300,000. Mean £360,353. Fewer than August because the file was published 28 Oct 2026 and September is still arriving. Not a market fall. |

New builds are a bad August question: only 9 standard August transfers are flagged new. Most new-build rows in the file have other transfer months (5,982 standard new builds across the whole file). Do not read that 9 as the new-build market.
