-- 07_prediction_engine_rls_hardening.sql
-- Restricts prediction engine outputs to premium users only.
-- Apply AFTER 05_prediction_engine_schema.sql.
-- Does NOT modify: profiles, premium_codes, predictions, national_elo_ratings.

-- ── Drop old public-read policies ────────────────────────────────────────────
DROP POLICY IF EXISTS "public read strengths"            ON team_strength_snapshots;
DROP POLICY IF EXISTS "public read simulation runs"      ON simulation_runs;
DROP POLICY IF EXISTS "public read simulation standings" ON simulation_group_standings;
DROP POLICY IF EXISTS "public read players"              ON players;
DROP POLICY IF EXISTS "premium read strengths"           ON team_strength_snapshots;
DROP POLICY IF EXISTS "premium read simulation runs"     ON simulation_runs;
DROP POLICY IF EXISTS "premium read simulation standings" ON simulation_group_standings;
DROP POLICY IF EXISTS "premium read players"             ON players;

-- Keep Data API exposure explicit and least-privilege for premium tables.
REVOKE SELECT ON TABLE
  team_strength_snapshots,
  simulation_runs,
  simulation_group_standings,
  players
FROM anon;

GRANT SELECT ON TABLE
  team_strength_snapshots,
  simulation_runs,
  simulation_group_standings,
  players
TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  team_strength_snapshots,
  simulation_runs,
  simulation_group_standings,
  players
TO service_role;

-- ── Premium-only read policies ────────────────────────────────────────────────
CREATE POLICY "premium read strengths"
  ON team_strength_snapshots FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read simulation runs"
  ON simulation_runs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read simulation standings"
  ON simulation_group_standings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read players"
  ON players FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

-- ── simulation_terceros_table (conditional — may not exist yet) ───────────────
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'simulation_terceros_table'
  ) THEN
    EXECUTE 'DROP POLICY IF EXISTS "public read" ON simulation_terceros_table';
    EXECUTE 'DROP POLICY IF EXISTS "public read terceros" ON simulation_terceros_table';
    EXECUTE 'DROP POLICY IF EXISTS "premium read terceros" ON simulation_terceros_table';
    EXECUTE 'REVOKE SELECT ON TABLE simulation_terceros_table FROM anon';
    EXECUTE 'GRANT SELECT ON TABLE simulation_terceros_table TO authenticated';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE simulation_terceros_table TO service_role';
    EXECUTE '
      CREATE POLICY "premium read terceros"
        ON simulation_terceros_table FOR SELECT
        TO authenticated
        USING (
          EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.is_premium = true
          )
        )
    ';
  END IF;
END $$;

-- ── Verify after applying ─────────────────────────────────────────────────────
-- Anon (no session) → no table access after REVOKE.
-- Authenticated non-premium → 0 rows
-- Authenticated premium → data visible
--
-- national_elo_ratings intentionally stays public (mirrors public data).
