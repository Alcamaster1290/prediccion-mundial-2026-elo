-- ============================================================
-- 01_schema.sql — Tablas del sistema Premium
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- ============================================================

-- Extensión para hashing SHA-256
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ────────────────────────────────────────────────────────────
-- profiles
-- Se crea automáticamente al registrar un usuario (ver 03_functions.sql)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       text,
  full_name   text,
  is_premium  boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- ────────────────────────────────────────────────────────────
-- premium_codes
-- Nunca se lee desde el frontend (sin política SELECT pública)
-- Los códigos se insertan hasheados desde el dashboard de Supabase
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.premium_codes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code_hash   text UNIQUE NOT NULL,  -- SHA-256 del código en texto plano
  is_used     boolean NOT NULL DEFAULT false,
  used_by     uuid REFERENCES auth.users(id),
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  notes       text  -- uso interno del admin: "Pago Yape - Juan Pérez - 22 may 2026"
);

-- ────────────────────────────────────────────────────────────
-- predictions
-- Datos premium: probabilidades numéricas y análisis por partido
-- Solo accesibles para usuarios con is_premium = true
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.predictions (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id                text,             -- referencia a match_context.json: 'grp-a-j1-kor-cze'
  group_code              text NOT NULL,    -- 'A', 'B', ..., 'L'
  matchday                integer NOT NULL, -- 1, 2, 3
  match_order             integer,          -- orden dentro de la jornada
  team_a                  text NOT NULL,    -- código ISO: 'kor', 'bra', etc.
  team_b                  text NOT NULL,
  team_a_win_probability  numeric(5,2),     -- 0.00 – 100.00
  draw_probability        numeric(5,2),
  team_b_win_probability  numeric(5,2),
  global_tag              text,             -- 'duelo de favoritos', 'favorito vs debutante', etc.
  team_a_context          text,
  team_b_context          text,
  explanation             text,
  is_premium              boolean NOT NULL DEFAULT true,
  published               boolean NOT NULL DEFAULT false,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT probabilities_sum CHECK (
    team_a_win_probability + draw_probability + team_b_win_probability
    BETWEEN 99.5 AND 100.5
  )
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_predictions_group    ON public.predictions(group_code);
CREATE INDEX IF NOT EXISTS idx_predictions_published ON public.predictions(published) WHERE published = true;
CREATE INDEX IF NOT EXISTS idx_profiles_premium     ON public.profiles(is_premium) WHERE is_premium = true;
