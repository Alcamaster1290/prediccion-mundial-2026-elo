-- 28_predictions_free_finished.sql
-- Exposes per-match prediction cards for FINISHED matches to everyone
-- (anonymous visitors + logged-in free users), while keeping unplayed
-- matches and the Monte Carlo qualification data premium-only.
--
-- Model: a match's prediction becomes public the moment its match_results
-- row reaches status='finished'. No manual flagging — it auto-unlocks as
-- the tournament progresses. predictions.match_order maps 1:1 to
-- match_results.match_number.
--
-- Apply AFTER 02_rls.sql and 09_tournament_core.sql.
-- The existing premium policy ("predictions: premium users read published")
-- stays intact; permissive SELECT policies are combined with OR, so premium
-- users keep seeing all 72 matches.

-- predictions already has an implicit SELECT grant for anon; keep it explicit
-- so the Data API can reach the table for the new policy.
GRANT SELECT ON TABLE public.predictions TO anon, authenticated;

DROP POLICY IF EXISTS "predictions: public read finished matches" ON public.predictions;
CREATE POLICY "predictions: public read finished matches"
  ON public.predictions FOR SELECT
  TO anon, authenticated
  USING (
    published = true
    AND EXISTS (
      SELECT 1
      FROM public.match_results mr
      WHERE mr.match_number = public.predictions.match_order
        AND mr.status = 'finished'
    )
  );

-- ── Verify after applying ─────────────────────────────────────────────────────
-- As anon  → only predictions whose match is finished (12 today).
-- As premium → all 72 (via the existing premium policy).
--
--   SELECT count(*) FROM public.predictions;   -- run as anon: 12 ; as premium: 72
