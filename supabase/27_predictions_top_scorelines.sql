-- 27_predictions_top_scorelines.sql
-- Marcadores exactos más probables por partido, derivados de la misma grilla
-- Poisson del modelo (reescalados al 1X2 ajustado por draw_bias).
-- Formato: [{"score":"2-1","pct":12.4}, ...] ordenado por probabilidad.

ALTER TABLE public.predictions
  ADD COLUMN IF NOT EXISTS top_scorelines jsonb;

NOTIFY pgrst, 'reload schema';
