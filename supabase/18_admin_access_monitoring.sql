-- 18_admin_access_monitoring.sql
-- Admin full-read access for app data plus a private content status RPC.
-- Apply after 17_admin_premium_codes.sql.

DROP POLICY IF EXISTS "predictions: admin read all" ON public.predictions;
CREATE POLICY "predictions: admin read all"
  ON public.predictions FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "team strengths: admin read all" ON public.team_strength_snapshots;
CREATE POLICY "team strengths: admin read all"
  ON public.team_strength_snapshots FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "simulation runs: admin read all" ON public.simulation_runs;
CREATE POLICY "simulation runs: admin read all"
  ON public.simulation_runs FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "simulation standings: admin read all" ON public.simulation_group_standings;
CREATE POLICY "simulation standings: admin read all"
  ON public.simulation_group_standings FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "simulation terceros: admin read all" ON public.simulation_terceros_table;
CREATE POLICY "simulation terceros: admin read all"
  ON public.simulation_terceros_table FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "players: admin read all" ON public.players;
CREATE POLICY "players: admin read all"
  ON public.players FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

CREATE OR REPLACE FUNCTION public.admin_get_content_status()
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor uuid := (select auth.uid());
  latest_run_id uuid;
  latest_run_created_at timestamptz;
  latest_run_completed_at timestamptz;
  latest_run_runs integer;
  latest_run_scenario text;
  latest_run_active boolean;
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    RETURN jsonb_build_object('success', false, 'message', 'No autorizado.');
  END IF;

  SELECT
    sr.id,
    sr.created_at,
    sr.completed_at,
    sr.runs,
    sr.scenario_name,
    sr.is_active
  INTO
    latest_run_id,
    latest_run_created_at,
    latest_run_completed_at,
    latest_run_runs,
    latest_run_scenario,
    latest_run_active
  FROM public.simulation_runs sr
  ORDER BY sr.is_active DESC, sr.created_at DESC
  LIMIT 1;

  RETURN jsonb_build_object(
    'success', true,
    'simulation', jsonb_build_object(
      'latest_run_id', latest_run_id,
      'scenario_name', latest_run_scenario,
      'runs', latest_run_runs,
      'is_active', latest_run_active,
      'created_at', latest_run_created_at,
      'completed_at', latest_run_completed_at,
      'total_runs', (SELECT count(*) FROM public.simulation_runs),
      'standings_rows_for_latest', (
        SELECT count(*)
        FROM public.simulation_group_standings sgs
        WHERE sgs.simulation_run = latest_run_id
      ),
      'terceros_rows_for_latest', (
        SELECT count(*)
        FROM public.simulation_terceros_table stt
        WHERE stt.simulation_run = latest_run_id
      ),
      'strength_rows', (SELECT count(*) FROM public.team_strength_snapshots),
      'players_rows', (SELECT count(*) FROM public.players)
    ),
    'real_results', jsonb_build_object(
      'total_matches', (SELECT count(*) FROM public.match_results),
      'group_matches', (SELECT count(*) FROM public.match_results WHERE phase = 'group'),
      'loaded_results', (
        SELECT count(*)
        FROM public.match_results
        WHERE status <> 'scheduled'
           OR home_goals IS NOT NULL
           OR away_goals IS NOT NULL
      ),
      'finished_matches', (SELECT count(*) FROM public.match_results WHERE status = 'finished'),
      'live_matches', (SELECT count(*) FROM public.match_results WHERE status = 'live'),
      'last_updated_at', (SELECT max(updated_at) FROM public.match_results)
    ),
    'published_predictions', jsonb_build_object(
      'published', (SELECT count(*) FROM public.predictions WHERE published = true),
      'drafts', (SELECT count(*) FROM public.predictions WHERE published = false),
      'total', (SELECT count(*) FROM public.predictions),
      'last_created_at', (SELECT max(created_at) FROM public.predictions),
      'last_updated_at', (SELECT max(updated_at) FROM public.predictions)
    )
  );
END;
$$;

REVOKE ALL ON FUNCTION public.admin_get_content_status() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.admin_get_content_status() TO authenticated;
