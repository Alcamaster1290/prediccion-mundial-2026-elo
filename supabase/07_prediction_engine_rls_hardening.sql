-- 07_prediction_engine_rls_hardening.sql
-- Restricts prediction engine outputs to premium users only.
-- Apply AFTER 05_prediction_engine_schema.sql.
-- Does NOT modify: profiles, premium_codes, predictions, national_elo_ratings.

-- ── Drop old public-read policies ────────────────────────────────────────────
DROP POLICY IF EXISTS "public read strengths"            ON team_strength_snapshots;
DROP POLICY IF EXISTS "public read simulation runs"      ON simulation_runs;
DROP POLICY IF EXISTS "public read simulation standings" ON simulation_group_standings;
DROP POLICY IF EXISTS "public read players"              ON players;

-- ── Premium-only read policies ────────────────────────────────────────────────
CREATE POLICY "premium read strengths"
  ON team_strength_snapshots FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read simulation runs"
  ON simulation_runs FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read simulation standings"
  ON simulation_group_standings FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles p
      WHERE p.id = auth.uid() AND p.is_premium = true
    )
  );

CREATE POLICY "premium read players"
  ON players FOR SELECT
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
    EXECUTE 'DROP POLICY IF EXISTS "public read terceros" ON simulation_terceros_table';
    EXECUTE '
      CREATE POLICY "premium read terceros"
        ON simulation_terceros_table FOR SELECT
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
-- Anon (no session) → should return 0 rows:
--   SET ROLE anon; SELECT count(*) FROM team_strength_snapshots;
-- Authenticated non-premium → 0 rows
-- Authenticated premium → data visible
--
-- national_elo_ratings intentionally stays public (mirrors public data).
