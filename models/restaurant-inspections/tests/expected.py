# Expected answers for tests/checks.dax, computed from the data factory's Parquet files with duckdb.
# usage: <python with duckdb> -I tests/expected.py data-factory/inspections/data
import duckdb, sys
D = sys.argv[1]
c = duckdb.connect()
c.execute(f"create view i0 as select * from read_parquet('{D}/inspections.parquet')")
c.execute(f"create view v as select * from read_parquet('{D}/violations.parquet')")
c.execute(f"create view e as select * from read_parquet('{D}/establishments.parquet')")
# previous distinct earlier visit date per establishment
c.execute("""create table i as
with d as (select distinct est_id, date from i0),
p as (select est_id, date, lag(date) over (partition by est_id order by date) prev from d)
select i0.*, p.prev, datediff('day', p.prev, i0.date) days_since,
  coalesce(datediff('day', p.prev, i0.date) <= 60, false) followup,
  case when (i0.source='nyc' and (i0.result_raw like 'Establishment Closed%' or i0.result_raw like 'Establishment re-closed%'))
         or (i0.source='boston' and i0.result_raw in ('HE_Closure','HE_VolClos','HE_TSOP'))
         or (i0.source in ('toronto','montgomery') and i0.result_raw='Closed')
         or (i0.source='marin' and i0.tier=3) then true else false end closed
from i0 left join p using(est_id, date)""")
c.execute("create view r as select * from i where type_norm='routine' and date>='2024-01-01' and date<'2026-11-01'")
def q(t, s):
    print("\n##", t); res = c.execute(s); print([d[0] for d in res.description])
    for row in res.fetchall(): print(row)
q("Q1 totals", "select (select count(*) from i), (select count(*) from v), (select sum(critical::int) from v), (select count(distinct est_id) from i), (select count(*) from (select distinct est_id from e where est_id is not null))")
q("Q2 critical per routine inspection (violation-publishing sources), window", "select source, count(*) n, round(sum(n_critical)/count(*),4) crit, round(sum(n_violations)/count(*),4) viol, round(avg(norm_score),4) norm from r group by 1 order by 1")
q("Q3 at 3+ criticals: rated n, tier>=2 share, closed share", "select source, count(*) filter (where tier is not null) rated, round(avg((tier>=2)::int),4) reinsp, round(avg(closed::int),4) closed_all, round(sum(closed::int)/count(*) filter (where tier is not null),4) closed_rated from r where n_critical>=3 group by 1 order by 1")
q("Q4 published outcome (tier 3 share of rated), routine window, all and first visits", "select source, round(avg((tier=3)::int),4) pub, round(avg((tier=3)::int) filter (where not followup),4) first_visits, round(avg(followup::int),4) followup_share from r group by 1 order by 1")
q("Q5 share citing pests / temperature", "select r.source, round(avg(p),4) pests, round(avg(t),4) temp from (select r.insp_id, r.source, coalesce(max((v.category='pests')::int),0) p, coalesce(max((v.category='temperature_control')::int),0) t from r left join v using(insp_id) where r.source!='austin' group by 1,2) r group by 1 order by 1")
chain = "('STARBUCKS'),('MCDONALD'),('SUBWAY'),('DUNKIN'),('CHIPOTLE'),('BURGER KING'),('7 ELEVEN'),('TACO BELL'),('WENDY'),('DOMINO'),('PANERA'),('POPEYES'),('CHICK FIL A'),('KFC'),('PIZZA HUT'),('PANDA EXPRESS'),('JERSEY MIKE'),('TIM HORTONS')"
c.execute(f"create table ec as select e.*, (select c from (values {chain}) t(c) where e.name_norm like c || '%' or replace(e.name_norm,' ','') like replace(c,' ','') || '%' limit 1) ch from e")
q("Q6 chains", "select r.source, count(*) filter (where ch is not null) n_chain, round(sum(n_critical) filter (where ch is not null)/count(*) filter (where ch is not null),4) chain, round(sum(n_critical) filter (where ch is null)/count(*) filter (where ch is null),4) other from r left join ec using(est_id) where r.source!='austin' group by 1 order by 1")
q("chains count", "select count(*) filter (where ch is not null), count(*) from ec")
q("Q7 temperature summer/winter", "select source, round(avg(t) filter (where m in (6,7,8)),4) summer, round(avg(t) filter (where m in (12,1,2)),4) winter, round(avg(t) filter (where m in (6,7,8))/avg(t) filter (where m in (12,1,2)),4) ratio from (select r.insp_id, r.source, month(r.date) m, coalesce(max((v.category='temperature_control')::int),0) t from r left join v using(insp_id) where r.source!='austin' group by 1,2,3) group by 1 order by 1")
q("Q8 categories all data: violations and critical", "select category, count(*), sum(critical::int) from v group by 1 order by 2 desc")
q("Q9 NYC 2025 vs 2024 routine inspections, crit/insp", "select year(date) y, count(*), round(sum(n_critical)/count(*),4) from i where source='nyc' and type_norm='routine' group by 1 order by 1")
q("inspection type mix", "select type_norm, count(*) from i group by 1 order by 1")
q("first-visit boston routine share", "select count(*), sum(followup::int) from r where source='boston'")
q("last date", "select max(date) from i")
q("null est", "select count(*) from e where est_id is null")
