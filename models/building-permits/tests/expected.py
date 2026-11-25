# Expected answers for tests/checks.dax, from permits.parquet + housing_units.parquet.
# usage: data-factory .venv python -I tests/expected.py
import sys, duckdb
P = sys.argv[1] if len(sys.argv) > 1 else "data/permits.parquet"
H = sys.argv[2] if len(sys.argv) > 2 else "data/housing_units.parquet"
c = duckdb.connect()
c.sql("SET memory_limit='3GB'")
c.sql(f"create view p as select * from '{P}'")
c.sql(f"create view h as select * from '{H}'")
c.sql("create table f as select p.*, h.housing_units as hu from p left join h using (permit_id)")
def q(t, s):
    print("\n##", t)
    res = c.sql(s)
    print(res.fetchall())
q("Q1 totals", "select count(*), count(*) filter (where issued_date is not null), round(sum(hu),0) from f")
q("Q2 Austin 2023-25 per 1000", """
select round(sum(hu) filter (where year(issued_date) between 2023 and 2025),0),
       round(sum(hu) filter (where year(issued_date) between 2023 and 2025)/3.0/993588*1000,2)
from f where jurisdiction='Austin, TX'""")
q("Q3 median days 2025 new_res SF and Montgomery", """
select jurisdiction, median(days_apply_to_issue)
from f where category='new_residential' and year(issued_date)=2025 and days_apply_to_issue is not null
  and jurisdiction in ('San Francisco, CA','Montgomery County, MD')
group by 1""")
q("Q4 NYC Jan-Oct 2026 vs 2025 hu", """
select sum(hu) filter (where issued_date between date '2025-01-01' and date '2025-10-31'),
       sum(hu) filter (where issued_date between date '2026-01-01' and date '2026-10-31')
from f where jurisdiction='New York, NY'""")
q("Q5 Seattle Jan-Sep hu", """
select sum(hu) filter (where issued_date between date '2025-01-01' and date '2025-09-30'),
       sum(hu) filter (where issued_date between date '2026-01-01' and date '2026-09-30')
from f where jurisdiction='Seattle, WA'""")
q("Q6 LA 2023-25 hu including mixed-use", "select round(sum(hu) filter (where year(issued_date) between 2023 and 2025),0) from f where jurisdiction='Los Angeles, CA'")
q("Q7 Chicago new construction valuation 2023 and 2025", """
select round(sum(valuation_usd) filter (where category in ('new_residential','new_nonresidential') and year(issued_date)=2023 and valuation_usd between 1 and 2e9)/1e9,2),
       round(sum(valuation_usd) filter (where category in ('new_residential','new_nonresidential') and year(issued_date)=2025 and valuation_usd between 1 and 2e9)/1e9,2)
from f where jurisdiction='Chicago, IL'""")
q("Q8 NYC 200+ share 2023-25", """
select sum(units_added), sum(units_added) filter (where units_added>=200),
       round(100.0*sum(units_added) filter (where units_added>=200)/sum(units_added),0)
from f where jurisdiction='New York, NY' and category='new_residential' and units_added>0 and year(issued_date) between 2023 and 2025""")
q("Q9 LA per 1000 2023-25", """
select round(sum(hu) filter (where year(issued_date) between 2023 and 2025)/3.0/3878704*1000,2)
from f where jurisdiction='Los Angeles, CA'""")
q("Q10 Seattle new_res applications Jan-Oct", """
select count(*) filter (where applied_date between date '2025-01-01' and date '2025-10-31'),
       count(*) filter (where applied_date between date '2026-01-01' and date '2026-10-31')
from f where jurisdiction='Seattle, WA' and category='new_residential'""")
