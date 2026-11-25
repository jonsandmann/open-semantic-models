# Expected answers for tests/checks.dax, from the factory's payments.parquet (not the model's slim copy).
# usage: data-factory/.venv/bin/python -I tests/expected.py
import duckdb, os
P = os.path.expanduser("data-factory/spending/data/payments.parquet")
PASS = r"\bBANK\b|BANCORP|\bTRUST\b|PENSION|RETIREMENT|ANNUITY|BLUE CROSS|BLUE SHIELD|KAISER|DELTA DENTAL|PAYROLL|TREASURER|BOARD OF EDUCATION|PUBLIC PWR AUTH|INTERNAL REVENUE|CREDIT UNION|\bFCU\b|INSURANCE|HEALTH PLAN|AETNA|CIGNA|UNITEDHEALTH|HUMANA|DEFERRED COMP|STATE OF |COUNTY OF |COUNTY TREASURER|DEPARTMENT OF FINANCE"
c = duckdb.connect(); c.sql("SET memory_limit='3GB'")
c.sql(f"create view p as select * from '{P}'")
c.sql(f"create view v as select * from p where function <> 'benefits_debt_nondept' and vendor_norm is not null and not regexp_matches(vendor_norm, '{PASS}')")
def q(t, s): print("\n##", t); print(c.sql(s).fetchall())
q("Q1 lines, total, vendor spending, payees", "select (select count(*) from p), (select sum(amount) from p), (select sum(amount) from v), (select count(distinct vendor_norm) from v)")
q("Q2 Los Angeles FY2026 lines and total", "select count(*), sum(amount) from p where city_slug='los-angeles' and fiscal_year=2026")
q("Q3 Atlanta FY2026: payees, vendor spending, top 10 and top 100 share", """
 with x as (select vendor_norm, sum(amount) m from v where city_slug='atlanta' and fiscal_year=2026 group by 1),
 r as (select *, row_number() over (order by m desc) rk from x)
 select count(*), sum(m), round(100*sum(m) filter (where rk<=10)/sum(m),1), round(100*sum(m) filter (where rk<=100)/sum(m),1) from r""")
q("Q4 vendors paid by 3+ cities, their dollars; paid by all 9", """
 with x as (select vendor_norm, count(distinct city_slug) n, sum(amount) m from v group by 1)
 select count(*) filter (where n>=3), sum(m) filter (where n>=3), count(*) filter (where n=9) from x""")
q("Q5 Motorola Solutions: cities, total, Chicago", """select count(distinct city_slug), sum(amount), sum(amount) filter (where city_slug='chicago')
 from v where vendor_norm='MOTOROLA SOLUTIONS'""")
q("Q6 Austin culture_recreation FY2025, FY2026", """select sum(amount) filter (where fiscal_year=2025), sum(amount) filter (where fiscal_year=2026)
 from p where city_slug='austin' and function='culture_recreation'""")
q("Q7 Atlanta Axon + Motorola per resident (2 years, pop 520070)", """select sum(amount), sum(amount)/520070 from p
 where city_slug='atlanta' and vendor_norm in ('AXON ENTERPRISE','MOTOROLA SOLUTIONS')""")
q("Q8 Chicago FY2025 unmapped share of absolute dollars", """select round(100*sum(abs(amount)) filter (where function='unmapped')/sum(abs(amount)),1) from p where city_slug='chicago' and fiscal_year=2025""")
q("Q9 Kansas City CY2024 negatives", "select sum(amount) filter (where amount<0) from p where city_slug='kansas-city' and fiscal_year=2024")
q("Q10 Boston payments dated Jul-Sep 2025 (calendar), and SF dated lines", """select sum(amount) filter (where city_slug='boston' and payment_date between '2025-07-01' and '2025-09-30'),
 count(*) filter (where city_slug='san-francisco' and payment_date is not null) from p""")
