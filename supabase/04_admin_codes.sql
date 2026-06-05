-- ============================================================
-- 04_admin_codes.sql — Gestión manual de códigos premium
-- Ejecutar en Supabase Dashboard → SQL Editor (como admin)
-- NUNCA commitear códigos en texto plano
-- ============================================================

-- ── Generar un código nuevo ───────────────────────────────────
-- 1. Decide el código en texto plano (ej: 'WWCMAY2026-JUAN')
-- 2. Almacena solo el hash:
--
-- INSERT INTO public.premium_codes (code_hash, notes)
-- VALUES (
--   encode(extensions.digest('TU-CODIGO-AQUI', 'sha256'), 'hex'),
--   'Pago Yape S/15 - Juan Pérez - 22 may 2026'
-- );
--
-- 3. Envía el código en texto plano ('TU-CODIGO-AQUI') por email al usuario.
-- 4. NUNCA almacenes el código en texto plano en ningún sistema.

-- ── Ver estado de códigos (sin revelar el hash completo) ──────
SELECT
  id,
  left(code_hash, 8) || '...' AS code_hash_preview,
  is_used,
  used_by,
  used_at,
  notes,
  created_at
FROM public.premium_codes
ORDER BY created_at DESC;

-- ── Ver usuarios premium ──────────────────────────────────────
SELECT
  p.id,
  p.email,
  p.full_name,
  p.is_premium,
  p.updated_at AS premium_since
FROM public.profiles p
WHERE p.is_premium = true
ORDER BY p.updated_at DESC;

-- ── Revocar premium manualmente (si hay fraude) ───────────────
-- UPDATE public.profiles SET is_premium = false WHERE id = 'uuid-del-usuario';

-- ── Ejemplo: insertar predicción de prueba ────────────────────
-- INSERT INTO public.predictions (
--   match_id, group_code, matchday, match_order,
--   team_a, team_b,
--   team_a_win_probability, draw_probability, team_b_win_probability,
--   global_tag, team_a_context, team_b_context, explanation,
--   is_premium, published
-- ) VALUES (
--   'grp-a-j1-kor-cze', 'A', 1, 2,
--   'kor', 'cze',
--   52.0, 25.0, 23.0,
--   'Duelo parejo',
--   'Corea del Sur llega con Son como líder indiscutido y un 3-4-2-1 que presiona alto.',
--   'Chequia tiene calidad europea pero llegó al Mundial por repechaje con margen ajustado.',
--   'Ventaja táctica para Corea, pero Chequia puede sorprender si cierra líneas correctamente.',
--   true, true
-- );
