# Builds the model's Parquet files from the data factory's cities/data/city_finances.csv and sources/ (read only).
# usage: data-factory/.venv/bin/python -I data/prep.py   (from models/city-finances)
import duckdb, os
SRC = os.path.expanduser("data-factory/cities")
OUT = os.path.dirname(os.path.abspath(__file__))
c = duckdb.connect()
c.sql(f"create view f as select * from read_csv('{SRC}/data/city_finances.csv', types={{'fips_place': 'VARCHAR'}})")
c.sql(f"create view s as select * from read_csv('{SRC}/sources/cities.csv', types={{'fips_place': 'VARCHAR'}})")
# City Group: Seattle is 'top50+wa' in the source and goes in Top 50 US city (one group per city).
# Latest = the fiscal year of the city's own report; Prior = that report's comparative column.
c.sql("create table latest as select fips_place, max(fiscal_year) fy from f group by 1")
c.sql(f"""copy (select f.row_id, f.fips_place as city_key, f.fiscal_year,
  case when f.fiscal_year = l.fy then 'Latest' else 'Prior' end as year_position,
  f.fiscal_year_end, f.figure_id, f.source_label, cast(round(f.value * 1000000) as decimal(18,0)) as value_usd,
  f.fips_place || '|' || f.fiscal_year as report_key, f.page, f.extraction_method,
  case f.checked when 'pass' then 1 else 0 end as hand_checked
from f join latest l using (fips_place) order by f.fips_place, f.fiscal_year, f.figure_id) to '{OUT}/figures.parquet' (format parquet)""")
c.sql(f"""copy (select f.fips_place || '|' || f.fiscal_year as report_key, any_value(f.fiscal_year_end) as fiscal_year_end,
  any_value(f.source_pdf_url) as source_pdf_url
from f group by f.fips_place, f.fiscal_year order by 1) to '{OUT}/reports.parquet' (format parquet)""")
c.sql(f"""copy (select s.fips_place as city_key, s.city || ', ' || s.state as city, s.state, s.population_2024 as population,
  case when s."group" like 'top50%' then 'Top 50 US city' else 'Washington near Bellevue' end as city_group,
  t.fips_place is not null as in_data, coalesce(t.sums_ok, false) as table_sums_ok
from s left join (select fips_place, bool_and(table_sums_ok) sums_ok from f group by 1) t using (fips_place)
order by population desc) to '{OUT}/cities.parquet' (format parquet)""")
for x in ("figures", "reports", "cities"):
    print(x, c.sql(f"select count(*) from '{OUT}/{x}.parquet'").fetchall()[0][0])
print(c.sql(f"select count(*) filter (where in_data), count(*) filter (where table_sums_ok) from '{OUT}/cities.parquet'").fetchall())
print(c.sql(f"select year_position, fiscal_year, count(distinct city_key) from '{OUT}/figures.parquet' group by all order by all").fetchall())
print(c.sql(f"select count(*) from (select row_id from '{OUT}/figures.parquet' group by 1 having count(*)>1)").fetchall())
