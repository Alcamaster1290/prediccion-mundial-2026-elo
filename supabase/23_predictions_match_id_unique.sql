-- 23_predictions_match_id_unique.sql
-- Make predictions.match_id compatible with PostgREST upserts using
-- on_conflict=match_id. Partial unique indexes cannot be inferred there.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.predictions
    WHERE match_id IS NOT NULL
    GROUP BY match_id
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'Cannot create unique index on public.predictions(match_id): duplicate match_id rows exist.';
  END IF;
END;
$$;

DROP INDEX IF EXISTS public.idx_predictions_match_id_unique;
CREATE UNIQUE INDEX idx_predictions_match_id_unique
  ON public.predictions(match_id);

NOTIFY pgrst, 'reload schema';
