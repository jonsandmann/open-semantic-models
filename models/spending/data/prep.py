# Builds the model's slim Parquet files from the data factory's spending/data/payments.parquet (read only).
# usage: data-factory/.venv/bin/python -I data/prep.py   (from models/spending)
import duckdb, os
SRC = os.path.expanduser("data-factory/spending/data/payments.parquet")
OUT = os.path.dirname(os.path.abspath(__file__))
# pipeline/analyze.py's pass-through payees: left out of Vendor Spending along with function benefits_debt_nondept.
PASS = r"\bBANK\b|BANCORP|\bTRUST\b|PENSION|RETIREMENT|ANNUITY|BLUE CROSS|BLUE SHIELD|KAISER|DELTA DENTAL|PAYROLL|TREASURER|BOARD OF EDUCATION|PUBLIC PWR AUTH|INTERNAL REVENUE|CREDIT UNION|\bFCU\b|INSURANCE|HEALTH PLAN|AETNA|CIGNA|UNITEDHEALTH|HUMANA|DEFERRED COMP|STATE OF |COUNTY OF |COUNTY TREASURER|DEPARTMENT OF FINANCE"
c = duckdb.connect()
c.sql("SET memory_limit='3GB'")
c.sql(f"create view p as select * from '{SRC}'")
c.sql(f"""create table vendor as select row_number() over (order by vendor_norm) as vendor_key, vendor_norm,
  regexp_matches(vendor_norm, '{PASS}') as pass_through from (select distinct vendor_norm from p where vendor_norm is not null)""")
c.sql("insert into vendor values (0, '(no payee)', false)")
c.sql("""create table dept as select row_number() over (order by city_slug, d) as department_key, city_slug, d as department
  from (select distinct city_slug, coalesce(nullif(trim(department_raw), ''), '(blank)') d from p)""")
c.sql(f"""copy (select p.city_slug as city, p.fiscal_year, p.payment_date, cast(p.amount as decimal(18,2)) as amount,
  coalesce(v.vendor_key, 0) as vendor_key, d.department_key, p.function,
  case when p.function <> 'benefits_debt_nondept' and p.vendor_norm is not null and not coalesce(v.pass_through, false) then 1 else 0 end as vendor_spend
from p left join vendor v on v.vendor_norm = p.vendor_norm
join dept d on d.city_slug = p.city_slug and d.department = coalesce(nullif(trim(p.department_raw), ''), '(blank)')
order by city, fiscal_year, vendor_key) to '{OUT}/payments.parquet' (format parquet, compression zstd)""")
# Cities Paid: how many of the nine cities paid the payee as vendor spending, over both years (FINDINGS.md 1).
c.sql(f"""copy (select v.vendor_key, v.vendor_norm as vendor, v.pass_through, coalesce(n.cities, 0)::bigint as cities_paid
from vendor v left join (select vendor_key, count(distinct city) cities from '{OUT}/payments.parquet' where vendor_spend = 1 group by 1) n
using (vendor_key) order by 1) to '{OUT}/vendors.parquet' (format parquet)""")
c.sql(f"copy (select department_key, city_slug as city, department from dept order by 1) to '{OUT}/departments.parquet' (format parquet)")
for f in ("payments", "vendors", "departments"):
    print(f, c.sql(f"select count(*) from '{OUT}/{f}.parquet'").fetchall()[0][0], os.path.getsize(f"{OUT}/{f}.parquet") // 1024, "KB")
print(c.sql(f"select sum(amount), sum(amount) filter (where vendor_spend=1), min(payment_date), max(payment_date), count(*) filter (where payment_date is null) from '{OUT}/payments.parquet'").fetchall())
print(c.sql("select distinct function from p order by 1").fetchall())
print(c.sql("select city_slug, city, state, fiscal_year_end_mmdd, min(fiscal_year), max(fiscal_year) from p group by all order by 1").fetchall())
