-- 14_simulation_snapshots.sql
-- Active/versioned Monte Carlo snapshots.
-- Apply after 07_prediction_engine_rls_hardening.sql and 13_staff_roles.sql.

ALTER TABLE public.simulation_runs
  ADD COLUMN IF NOT EXISTS scenario_name text NOT NULL DEFAULT 'baseline',
  ADD COLUMN IF NOT EXISTS model_version text,
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS input_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_simulation_runs_one_active_scenario
  ON public.simulation_runs (scenario_name)
  WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_simulation_runs_active_created
  ON public.simulation_runs (is_active, created_at DESC);

CREATE OR REPLACE VIEW public.v_active_simulation_run
WITH (security_invoker = true)
AS
SELECT *
FROM public.simulation_runs
WHERE is_active = true
ORDER BY created_at DESC
LIMIT 1;

CREATE OR REPLACE FUNCTION public.get_active_simulation_snapshot()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
  WITH active_run AS (
    SELECT *
    FROM public.v_active_simulation_run
    LIMIT 1
  )
  SELECT jsonb_build_object(
    'run', to_jsonb(active_run),
    'standings', coalesce((
      SELECT jsonb_agg(to_jsonb(sgs) ORDER BY sgs.qualified_pct DESC)
      FROM public.simulation_group_standings sgs
      WHERE sgs.simulation_run = active_run.id
    ), '[]'::jsonb),
    'terceros', coalesce((
      SELECT jsonb_agg(to_jsonb(stt) ORDER BY stt.rank)
      FROM public.simulation_terceros_table stt
      WHERE stt.simulation_run = active_run.id
    ), '[]'::jsonb)
  )
  FROM active_run;
$$;

DROP POLICY IF EXISTS "simulation runs: staff update active" ON public.simulation_runs;
CREATE POLICY "simulation runs: staff update active"
  ON public.simulation_runs FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('editor')))
  WITH CHECK ((select public.has_staff_role('editor')));

GRANT SELECT ON TABLE public.v_active_simulation_run TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_active_simulation_snapshot() TO authenticated;
