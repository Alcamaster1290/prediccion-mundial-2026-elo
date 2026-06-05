-- 21_admin_team_content_monitor.sql
-- Private admin RPC for per-team data coverage across Supabase tables.
-- Apply after 20_fix_premium_code_crypto.sql.

CREATE OR REPLACE FUNCTION public.admin_get_team_data_status()
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor uuid := (select auth.uid());
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    RETURN jsonb_build_object('success', false, 'message', 'No autorizado.');
  END IF;

  RETURN (
    WITH latest_run AS (
      SELECT sr.id
      FROM public.simulation_runs sr
      ORDER BY sr.is_active DESC, sr.created_at DESC
      LIMIT 1
    ),
    player_counts AS (
      SELECT
        p.team_code,
        count(*)::integer AS player_rows,
        count(*) FILTER (WHERE p.titular)::integer AS starter_rows,
        count(*) FILTER (WHERE coalesce(p.elo_club, p.elo_player) IS NOT NULL)::integer AS player_elo_rows
      FROM public.players p
      GROUP BY p.team_code
    ),
    strength_latest AS (
      SELECT DISTINCT ON (tss.team_code)
        tss.team_code,
        tss.strength_score,
        tss.method,
        tss.created_at
      FROM public.team_strength_snapshots tss
      ORDER BY tss.team_code, tss.created_at DESC
    ),
    prediction_teams AS (
      SELECT
        p.team_a AS team_code,
        count(*)::integer AS prediction_rows,
        count(*) FILTER (WHERE p.published)::integer AS published_prediction_rows
      FROM public.predictions p
      GROUP BY p.team_a
      UNION ALL
      SELECT
        p.team_b AS team_code,
        count(*)::integer AS prediction_rows,
        count(*) FILTER (WHERE p.published)::integer AS published_prediction_rows
      FROM public.predictions p
      GROUP BY p.team_b
    ),
    prediction_counts AS (
      SELECT
        pt.team_code,
        sum(pt.prediction_rows)::integer AS prediction_rows,
        sum(pt.published_prediction_rows)::integer AS published_prediction_rows
      FROM prediction_teams pt
      GROUP BY pt.team_code
    ),
    simulation_counts AS (
      SELECT
        sgs.team_code,
        count(*)::integer AS simulation_rows
      FROM public.simulation_group_standings sgs
      WHERE sgs.simulation_run = (SELECT lr.id FROM latest_run lr)
      GROUP BY sgs.team_code
    ),
    team_rows AS (
      SELECT
        t.team_code,
        t.name,
        t.group_id,
        t.flag_url,
        coalesce(pc.player_rows, 0) AS player_rows,
        coalesce(pc.starter_rows, 0) AS starter_rows,
        coalesce(pc.player_elo_rows, 0) AS player_elo_rows,
        sl.strength_score,
        sl.method AS strength_method,
        (tp.team_code IS NOT NULL) AS has_profile,
        coalesce(tp.published, false) AS profile_published,
        (tpp.team_code IS NOT NULL) AS has_premium_profile,
        coalesce(sc.simulation_rows, 0) AS simulation_rows,
        coalesce(pr.prediction_rows, 0) AS prediction_rows,
        coalesce(pr.published_prediction_rows, 0) AS published_prediction_rows,
        array_remove(ARRAY[
          CASE WHEN coalesce(pc.player_rows, 0) < 26 THEN 'players' END,
          CASE WHEN coalesce(pc.starter_rows, 0) < 11 THEN 'starters' END,
          CASE
            WHEN coalesce(pc.player_rows, 0) > 0
             AND coalesce(pc.player_elo_rows, 0) < 11
            THEN 'player_elo'
          END,
          CASE WHEN sl.team_code IS NULL THEN 'strength' END,
          CASE WHEN tp.team_code IS NULL OR coalesce(tp.published, false) = false THEN 'profile' END,
          CASE WHEN tpp.team_code IS NULL THEN 'advanced_profile' END,
          CASE WHEN coalesce(sc.simulation_rows, 0) = 0 THEN 'simulation' END,
          CASE WHEN coalesce(pr.published_prediction_rows, 0) < 3 THEN 'predictions' END
        ]::text[], NULL) AS db_missing
      FROM public.teams t
      LEFT JOIN player_counts pc ON pc.team_code = t.team_code
      LEFT JOIN strength_latest sl ON sl.team_code = t.team_code
      LEFT JOIN public.team_profiles tp ON tp.team_code = t.team_code
      LEFT JOIN public.team_profile_premium tpp ON tpp.team_code = t.team_code
      LEFT JOIN simulation_counts sc ON sc.team_code = t.team_code
      LEFT JOIN prediction_counts pr ON pr.team_code = t.team_code
    )
    SELECT jsonb_build_object(
      'success', true,
      'summary', (
        SELECT jsonb_build_object(
          'total_teams', count(*),
          'teams_with_players', count(*) FILTER (WHERE player_rows >= 26),
          'teams_with_profiles', count(*) FILTER (WHERE profile_published),
          'teams_with_advanced_profiles', count(*) FILTER (WHERE has_premium_profile),
          'teams_with_strength', count(*) FILTER (WHERE strength_score IS NOT NULL),
          'teams_with_simulation', count(*) FILTER (WHERE simulation_rows > 0),
          'teams_with_predictions', count(*) FILTER (WHERE published_prediction_rows >= 3),
          'teams_complete_db', count(*) FILTER (WHERE cardinality(db_missing) = 0)
        )
        FROM team_rows
      ),
      'teams', coalesce((
        SELECT jsonb_agg(
          jsonb_build_object(
            'team_code', team_code,
            'name', name,
            'group_id', group_id,
            'flag_url', flag_url,
            'player_rows', player_rows,
            'starter_rows', starter_rows,
            'player_elo_rows', player_elo_rows,
            'strength_score', strength_score,
            'strength_method', strength_method,
            'has_profile', has_profile,
            'profile_published', profile_published,
            'has_premium_profile', has_premium_profile,
            'simulation_rows', simulation_rows,
            'prediction_rows', prediction_rows,
            'published_prediction_rows', published_prediction_rows,
            'db_missing', db_missing
          )
          ORDER BY group_id, team_code
        )
        FROM team_rows
      ), '[]'::jsonb)
    )
  );
END;
$$;

REVOKE ALL ON FUNCTION public.admin_get_team_data_status() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.admin_get_team_data_status() TO authenticated;
