# Expected answers for tests/checks.dax, computed from the factory's raw CSVs (not the model's Parquet).
# usage: data-factory/.venv/bin/python -I tests/expected.py
import duckdb, os
S = os.path.expanduser("data-factory/councils/data")
c = duckdb.connect()
for t in ("meetings", "items", "votes", "item_votes"):
    c.sql(f"create view {t} as select * from read_csv('{S}/{t}.csv', all_varchar=true)")
def q(t, s):
    print("\n##", t); print(c.sql(s).fetchall())
q("Q1 totals", """select (select count(*) from meetings), (select count(*) from items),
 (select count(*) from items where decided='1'), (select count(*) from votes),
 (select count(distinct city||roll_call_id) from item_votes)""")
for city in ("denver", "oakland"):
    q(f"Q2/3 {city} unanimous per item / per roll call", f"""
    with d as (select iv.* from item_votes iv join items i using (city, item_id) where i.decided='1' and iv.city='{city}')
    select count(*), round(100.0*avg(unanimous::int),1),
      count(distinct roll_call_id),
      round(100.0*count(distinct roll_call_id) filter (where unanimous='1')/count(distinct roll_call_id),1) from d""")
q("Q4 Oakland consent share; unanimous consent vs rest", """
 select round(100.0*count(*) filter (where consent='1')/count(*),1),
  round(100.0*avg(iv.unanimous::int) filter (where consent='1'),1),
  round(100.0*avg(iv.unanimous::int) filter (where consent<>'1'),1)
 from items i left join item_votes iv using (city,item_id) where i.city='oakland' and decided='1'""")
q("Q5 contract dollars (each matter once, decided)", """
 with r as (select *, row_number() over () rn from items),
 f as (select *, row_number() over (partition by city, coalesce(nullif(matter_id,''), item_id) order by rn) k
       from r where decided='1' and money_usd is not null and money_usd<>'')
 select topic, count(*), sum(money_usd::double), median(money_usd::double) from f where k=1 group by 1 order by 3 desc limit 3""")
q("Q6 contract items voted on their own: count, % with a no", """
 select count(*), round(100.0*avg((unanimous<>'1')::int),1) from item_votes iv join items i using (city,item_id)
 where block_size='1' and topic='contract'""")
for city in ("oakland", "denver"):
    q(f"Q7/8 {city} no votes (distinct VoteId), top dissenter", f"""
    with n as (select distinct vote_id, person_name from votes where city='{city}' and lower(trim(vote_value)) in ('opposed','no','nay'))
    select person_name, count(*) c, (select count(*) from n), round(100.0*count(*)/(select count(*) from n),1) from n group by 1 order by 2 desc limit 2""")
q("Q9 Seattle roll calls and unanimous share", """
 select count(distinct roll_call_id), round(100.0*count(distinct roll_call_id) filter (where unanimous='1')/count(distinct roll_call_id),1)
 from item_votes where city='seattle'""")
q("Q10 meetings by city; decided items Bellevue/San Jose; Seattle meetings 2026 Q1", """
 select city, count(*), (select count(*) from items i where i.city=m.city and decided='1'),
  count(*) filter (where meeting_date between '2026-01-01' and '2026-03-31') from meetings m group by 1 order by 1""")
