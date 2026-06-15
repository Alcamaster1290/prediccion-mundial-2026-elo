-- 29_bracket_public_projection.sql
-- Public, percentage-free projection of the knockout bracket entrants so that
-- NON-premium users can see the flags and seeding positions of the projected
-- qualifiers — while the qualification percentages and the full Monte Carlo
-- data stay premium-only.
--
-- The simulation_* tables are premium-gated (07_prediction_engine_rls_hardening).
-- This SECURITY DEFINER function reads them on the server and returns ONLY team
-- codes + ordinal info (rank, qualifies) for the active run. No probabilities
-- ever leave the database through it.
--
-- Apply AFTER 05_prediction_engine_schema.sql and 09_tournament_core.sql.

CREATE OR REPLACE FUNCTION public.get_bracket_projection()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  WITH active AS (
    SELECT id
    FROM public.simulation_runs
    WHERE is_active = true
    ORDER BY created_at DESC
    LIMIT 1
  ),
  gs AS (
    SELECT gm.group_id,
           s.team_code,
           s.first_pct,
           s.second_pct
    FROM public.simulation_group_standings s
    JOIN active a              ON s.simulation_run = a.id
    JOIN public.group_memberships gm ON gm.team_code = s.team_code
  ),
  firsts AS (
    SELECT DISTINCT ON (group_id) group_id, team_code AS code
    FROM gs
    ORDER BY group_id, first_pct DESC NULLS LAST
  ),
  -- El 2.° es el mayor second_pct EXCLUYENDO al proyectado 1.°, para no repetir
  -- el mismo equipo en ambos puestos cuando lidera las dos columnas.
  seconds AS (
    SELECT DISTINCT ON (gs.group_id) gs.group_id, gs.team_code AS code
    FROM gs
    JOIN firsts f ON f.group_id = gs.group_id
    WHERE gs.team_code <> f.code
    ORDER BY gs.group_id, gs.second_pct DESC NULLS LAST
  ),
  thirds AS (
    SELECT t.group_id, t.team_code AS code
    FROM public.simulation_terceros_table t
    JOIN active a ON t.simulation_run = a.id
  ),
  groups_json AS (
    SELECT COALESCE(jsonb_agg(
             jsonb_build_object(
               'group',  f.group_id,
               'first',  f.code,
               'second', s.code,
               'third',  th.code
             ) ORDER BY f.group_id
           ), '[]'::jsonb) AS g
    FROM firsts f
    LEFT JOIN seconds s ON s.group_id = f.group_id
    LEFT JOIN thirds  th ON th.group_id = f.group_id
  ),
  terceros_json AS (
    SELECT COALESCE(jsonb_agg(
             jsonb_build_object(
               'group',     t.group_id,
               'code',      t.team_code,
               'rank',      t.rank,
               'qualifies', t.qualifies
             ) ORDER BY t.rank
           ), '[]'::jsonb) AS t
    FROM public.simulation_terceros_table t
    JOIN active a ON t.simulation_run = a.id
  )
  SELECT jsonb_build_object(
    'groups',   (SELECT g FROM groups_json),
    'terceros', (SELECT t FROM terceros_json)
  );
$$;

REVOKE ALL ON FUNCTION public.get_bracket_projection() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_bracket_projection() TO anon, authenticated;

-- ── Verify after applying ─────────────────────────────────────────────────────
-- As anon:  SELECT public.get_bracket_projection();
--   → { "groups": [ {group, first, second, third}, ... 12 ],
--       "terceros": [ {group, code, rank, qualifies}, ... 12 ] }   (codes only)
-- The premium simulation_* tables remain 401 for anon.
