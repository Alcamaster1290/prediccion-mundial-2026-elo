-- 10_standings_views.sql
-- Public live standings and best-thirds projections from match_results.
-- Apply after 09_tournament_core.sql.

CREATE OR REPLACE VIEW public.v_group_match_results
WITH (security_invoker = true)
AS
SELECT
  match_number,
  upper(group_id) AS group_id,
  home_team,
  away_team,
  home_goals,
  away_goals,
  status,
  kickoff_utc,
  stadium,
  city,
  updated_at
FROM public.match_results
WHERE phase = 'group';

CREATE OR REPLACE VIEW public.v_group_standings
WITH (security_invoker = true)
AS
WITH match_team_stats AS (
  SELECT
    upper(group_id) AS group_id,
    home_team AS team_code,
    1 AS pj,
    CASE WHEN home_goals > away_goals THEN 1 ELSE 0 END AS pg,
    CASE WHEN home_goals = away_goals THEN 1 ELSE 0 END AS pe,
    CASE WHEN home_goals < away_goals THEN 1 ELSE 0 END AS pp,
    home_goals AS gf,
    away_goals AS gc,
    CASE
      WHEN home_goals > away_goals THEN 3
      WHEN home_goals = away_goals THEN 1
      ELSE 0
    END AS pts
  FROM public.match_results
  WHERE phase = 'group'
    AND home_goals IS NOT NULL
    AND away_goals IS NOT NULL
  UNION ALL
  SELECT
    upper(group_id) AS group_id,
    away_team AS team_code,
    1 AS pj,
    CASE WHEN away_goals > home_goals THEN 1 ELSE 0 END AS pg,
    CASE WHEN away_goals = home_goals THEN 1 ELSE 0 END AS pe,
    CASE WHEN away_goals < home_goals THEN 1 ELSE 0 END AS pp,
    away_goals AS gf,
    home_goals AS gc,
    CASE
      WHEN away_goals > home_goals THEN 3
      WHEN away_goals = home_goals THEN 1
      ELSE 0
    END AS pts
  FROM public.match_results
  WHERE phase = 'group'
    AND home_goals IS NOT NULL
    AND away_goals IS NOT NULL
),
aggregated AS (
  SELECT
    gm.group_id,
    gm.team_code,
    gm.draw_position,
    coalesce(sum(mts.pj), 0)::integer AS pj,
    coalesce(sum(mts.pg), 0)::integer AS pg,
    coalesce(sum(mts.pe), 0)::integer AS pe,
    coalesce(sum(mts.pp), 0)::integer AS pp,
    coalesce(sum(mts.gf), 0)::integer AS gf,
    coalesce(sum(mts.gc), 0)::integer AS gc,
    coalesce(sum(mts.gf), 0)::integer - coalesce(sum(mts.gc), 0)::integer AS dg,
    coalesce(sum(mts.pts), 0)::integer AS pts
  FROM public.group_memberships gm
  LEFT JOIN match_team_stats mts
    ON mts.group_id = gm.group_id
   AND mts.team_code = gm.team_code
  GROUP BY gm.group_id, gm.team_code, gm.draw_position
)
SELECT
  a.group_id,
  a.team_code,
  t.name AS team_name,
  t.flag_url,
  a.draw_position,
  a.pj,
  a.pg,
  a.pe,
  a.pp,
  a.gf,
  a.gc,
  a.dg,
  a.pts,
  row_number() OVER (
    PARTITION BY a.group_id
    ORDER BY a.pts DESC, a.dg DESC, a.gf DESC, a.draw_position ASC
  )::integer AS group_rank
FROM aggregated a
JOIN public.teams t ON t.team_code = a.team_code;

CREATE OR REPLACE VIEW public.v_best_thirds
WITH (security_invoker = true)
AS
SELECT
  row_number() OVER (
    ORDER BY pts DESC, dg DESC, gf DESC, group_id ASC
  )::integer AS third_rank,
  group_id,
  team_code,
  team_name,
  flag_url,
  pj,
  pg,
  pe,
  pp,
  gf,
  gc,
  dg,
  pts,
  (row_number() OVER (
    ORDER BY pts DESC, dg DESC, gf DESC, group_id ASC
  ) <= 8) AS classified
FROM public.v_group_standings
WHERE group_rank = 3;

CREATE OR REPLACE FUNCTION public.get_group_standings()
RETURNS SETOF public.v_group_standings
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM public.v_group_standings
  ORDER BY group_id, group_rank;
$$;

CREATE OR REPLACE FUNCTION public.get_best_thirds()
RETURNS SETOF public.v_best_thirds
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM public.v_best_thirds
  ORDER BY third_rank;
$$;

CREATE OR REPLACE FUNCTION public.get_live_results()
RETURNS SETOF public.match_results
LANGUAGE sql
STABLE
AS $$
  SELECT *
  FROM public.match_results
  ORDER BY match_number;
$$;

GRANT SELECT ON TABLE
  public.v_group_match_results,
  public.v_group_standings,
  public.v_best_thirds
TO anon, authenticated;

GRANT EXECUTE ON FUNCTION public.get_group_standings() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_best_thirds() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_live_results() TO anon, authenticated;
