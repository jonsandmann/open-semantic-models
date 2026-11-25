# Builds the model's Parquet files from the data factory's councils CSVs (read only).
# usage: data-factory/.venv/bin/python -I data/prep.py   (from models/councils)
import duckdb, os
SRC = os.path.expanduser("data-factory/councils/data")
OUT = os.path.dirname(os.path.abspath(__file__))
c = duckdb.connect()
c.sql(f"create view mt as select * from read_csv('{SRC}/meetings.csv', all_varchar=true)")
c.sql(f"create view it as select *, row_number() over () as rn from read_csv('{SRC}/items.csv', all_varchar=true)")
c.sql(f"create view vt as select * from read_csv('{SRC}/votes.csv', all_varchar=true)")
c.sql(f"create view iv as select * from read_csv('{SRC}/item_votes.csv', all_varchar=true)")

c.sql(f"""copy (select city || '|' || meeting_id as meeting_key, city, cast(meeting_date as date) as meeting_date, body
from mt) to '{OUT}/meetings.parquet' (format parquet)""")

# Money: decided items with a $ figure, each city + matter (or item) counted once, first in file order (analyze.py);
# two figures that are not city money are left out (FINDINGS.md 3): Oakland's Prop 1 state bond, Boston's ARPA RFI.
c.sql("""create table items as
select it.city, it.city || '|' || it.meeting_id as meeting_key, it.city || '|' || it.item_id as item_key,
  cast(m.meeting_date as date) as meeting_date, it.topic,
  cast(it.decided as int) as decided, cast(it.consent as int) as consent,
  try_cast(it.money_usd as double) as money_usd,
  case when iv.item_id is not null then it.city || '|' || iv.roll_call_id end as roll_call_key,
  try_cast(iv.block_size as int) as block_size, try_cast(iv.unanimous as int) as unanimous,
  try_cast(iv.no as int) as no_count, it.rn
from it join mt m using (city, meeting_id)
left join iv on iv.city = it.city and iv.item_id = it.item_id""")
c.sql("""create table money_first as
select item_key from (
  select item_key, row_number() over (partition by i.city, coalesce(nullif(m.matter_id,''), m.item_id) order by i.rn) r
  from items i join it m on i.item_key = m.city || '|' || m.item_id
  where i.decided = 1 and i.money_usd is not null) where r = 1""")
c.sql(f"""copy (select i.city, meeting_key, item_key, meeting_date, topic, decided, consent, money_usd,
  case when f.item_key is not null and not ((i.city = 'oakland' and money_usd = 11250000000) or (i.city = 'boston' and money_usd = 558700000))
       then money_usd end as money_counted,
  roll_call_key, block_size, unanimous, no_count
from items i left join money_first f using (item_key) order by rn) to '{OUT}/items.parquet' (format parquet)""")

YES = "('in favor','aye','yes','yea')"; NO = "('opposed','no','nay')"
c.sql(f"""copy (select v.city, v.city || '|' || v.item_id as item_key, v.city || '|' || v.vote_id as vote_key,
  v.city || '|' || v.person_id as member_key, coalesce(nullif(v.vote_value,''), '(blank)') as vote_value,
  cast(m.meeting_date as date) as meeting_date, i.topic, cast(i.consent as int) as consent
from vt v join it i using (city, item_id) join mt m on m.city = v.city and m.meeting_id = v.meeting_id
) to '{OUT}/votes.parquet' (format parquet)""")
c.sql(f"""copy (select city || '|' || person_id as member_key, city, max(person_name) as person_name
from vt group by all) to '{OUT}/members.parquet' (format parquet)""")
for f in ("meetings", "items", "votes", "members"):
    print(f, c.sql(f"select count(*) from '{OUT}/{f}.parquet'").fetchall()[0][0])
print(c.sql(f"select distinct vote_value from '{OUT}/votes.parquet' order by 1").fetchall())
print(c.sql(f"select count(*), count(distinct member_key || vote_key) from '{OUT}/votes.parquet'").fetchall())
print(c.sql(f"select min(meeting_date), max(meeting_date) from '{OUT}/meetings.parquet'").fetchall())
print(c.sql(f"select count(*) , count(distinct item_key) from '{OUT}/items.parquet'").fetchall())
