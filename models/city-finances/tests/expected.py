# Expected answers for tests/checks.dax, from the factory's city_finances.csv (values in USD millions there).
# usage: data-factory/.venv/bin/python -I tests/expected.py
import duckdb, os
F = os.path.expanduser("data-factory/cities/data/city_finances.csv")
c = duckdb.connect()
c.sql(f"create view f as select * from read_csv('{F}', types={{'fips_place': 'VARCHAR'}})")
c.sql("create view l as select * from f where (fips_place, fiscal_year) in (select fips_place, max(fiscal_year) from f group by 1)")
def q(t, s): print("\n##", t); print(c.sql(s).fetchall())
def v(city, fy, fig): return f"(select sum(value) from f where city='{city}' and fiscal_year={fy} and figure_id='{fig}')"
q("Q1 rows, cities, hand-checked rows, cities passing every sum check", """select count(*), count(distinct fips_place), count(*) filter (where checked='pass'),
 (select count(*) from (select fips_place from f group by 1 having bool_and(table_sums_ok))) from f""")
q("Q2 Seattle FY2025 total revenues, total expenses, net position ($M)", f"select {v('Seattle',2025,'rev_total')}, {v('Seattle',2025,'exp_total')}, {v('Seattle',2025,'np_total')}")
q("Q3 Latest year, all cities: total expenses, population of those cities, per resident", """
 with e as (select fips_place, sum(value) m, any_value(population) p from l where figure_id='exp_total' group by 1)
 select sum(m), sum(p), sum(m)*1e6/sum(p), count(*) from e""")
q("Q4 San Francisco FY2025 expenses per resident", "select sum(value)*1e6/any_value(population) from f where city='San Francisco' and fiscal_year=2025 and figure_id='exp_total'")
q("Q5 Los Angeles total revenues FY2025, FY2024, growth", f"select {v('Los Angeles',2025,'rev_total')}, {v('Los Angeles',2024,'rev_total')}, {v('Los Angeles',2025,'rev_total')}/{v('Los Angeles',2024,'rev_total')}-1")
q("Q6 Latest year: cities with negative unrestricted net position, and the most negative", """
 select count(*) filter (where u<0), arg_min(city, u), min(u) from (select city, sum(value) u from l where figure_id='np_unrestricted' group by 1)""")
q("Q7 Phoenix FY2025 public safety share of total expenses", f"select {v('Phoenix',2025,'exp_public_safety')}/{v('Phoenix',2025,'exp_total')}")
q("Q8 Seattle FY2025 business-type share of expenses", f"select {v('Seattle',2025,'exp_business_type_total')}/{v('Seattle',2025,'exp_total')}")
q("Q9 Latest year net pension liability: cities reporting, total, per resident of those cities", """
 with e as (select fips_place, sum(value) m, any_value(population) p from l where figure_id='net_pension_liability' group by 1)
 select count(*), sum(m), sum(m)*1e6/sum(p) from e""")
q("Q10 Washington cities (latest): count with data, property tax share of total revenues across them", """
 select count(distinct fips_place), sum(value) filter (where figure_id='rev_property_tax')/sum(value) filter (where figure_id='rev_total')
 from l where state='WA' and fips_place in (select fips_place from read_csv('""" + os.path.expanduser("data-factory/cities/sources/cities.csv") + """', types={'fips_place':'VARCHAR'}) where "group"<>'top50')""")
