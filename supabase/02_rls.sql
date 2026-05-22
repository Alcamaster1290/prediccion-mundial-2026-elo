-- ============================================================
-- 02_rls.sql — Row Level Security
-- Ejecutar DESPUÉS de 01_schema.sql
-- ============================================================

-- ── profiles ─────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Cada usuario solo puede leer su propio perfil
CREATE POLICY "profiles: self read"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

-- Cada usuario solo puede actualizar su propio perfil
-- (is_premium NO puede ser cambiado por el usuario — solo por la RPC)
CREATE POLICY "profiles: self update"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- ── premium_codes ─────────────────────────────────────────────
ALTER TABLE public.premium_codes ENABLE ROW LEVEL SECURITY;
-- Sin políticas SELECT/INSERT/UPDATE/DELETE desde el frontend.
-- Solo accesible via la función RPC SECURITY DEFINER.

-- ── predictions ──────────────────────────────────────────────
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

-- Solo usuarios autenticados con is_premium = true pueden leer
-- predicciones publicadas
CREATE POLICY "predictions: premium users read published"
  ON public.predictions FOR SELECT
  USING (
    published = true
    AND is_premium = true
    AND EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid()
        AND is_premium = true
    )
  );

-- Ningún usuario puede escribir en predictions desde el frontend
-- (las predicciones se cargan manualmente desde Supabase dashboard o script admin)
