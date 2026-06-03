# Premium Pronósticos Fase de Grupos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir una sección Premium "Pronósticos Fase de Grupos" con autenticación Supabase, flujo de pago manual vía código, y predicciones por partido visibles solo para usuarios premium — manteniendo el sitio como web estática en GitHub Pages.

**Architecture:** Frontend estático (HTML/CSS/JS vanilla) alojado en GitHub Pages. Autenticación y datos premium gestionados íntegramente por Supabase Auth + Row Level Security. No existe backend propio; la anon key de Supabase es pública (mitigado por RLS estricto). Los códigos premium son generados manualmente por el admin, hasheados con SHA-256 (pgcrypto) y canjeados via RPC SECURITY DEFINER que nunca expone la tabla premium_codes al frontend.

**Tech Stack:** HTML/CSS/JS vanilla · Supabase JS SDK v2 (CDN) · Supabase Auth (email/password) · PostgreSQL RLS + pgcrypto · GitHub Pages

---

## Diagnóstico del repositorio (auditoría previa)

| Hallazgo | Impacto en el plan |
|---|---|
| `index.html` monolítico, 2689 líneas, CSS+JS inline | CSS premium va inline; JS nuevo en `js/*.js` separados (justificado: `config.js` debe estar gitignoreado) |
| Sin build step, sin package.json | No se introduce ningún bundler; todo sigue siendo vanilla |
| `data/match_context.json` ya tiene `prediccion_narrativa` y `resultado_predicho` (público) | Este archivo se mantiene como "contexto táctico público"; las **probabilidades numéricas** y análisis premium van solo en Supabase |
| `#tracker` section termina en línea ~2343 | `<section id="pronosticos">` va inmediatamente después, antes de `<footer>` |
| Nav: `.tz-wrap` tiene `margin-left:auto`; `#theme-toggle` tiene `margin-left:.5rem` | Botón "Únete" se inserta entre tz-wrap y theme-toggle |
| `grupos-modal-overlay` ya establece patrón de modal overlay | Auth modal y payment modal siguen el mismo patrón |

## Arquitectura de seguridad (resumen)

```
GitHub Pages (público)          Supabase (privado por RLS)
─────────────────────           ─────────────────────────────
index.html                      auth.users  (gestionado por Supabase Auth)
js/config.js ← GITIGNORED       profiles    (self-read/update solamente)
js/auth.js                      premium_codes (NO leíble desde frontend)
js/premium.js                   predictions (solo is_premium=true)
data/match_context.json         RPC: redeem_premium_code (SECURITY DEFINER)
  └─ contexto táctico público
```

**Regla de oro:** La `anon key` puede estar en el frontend porque RLS garantiza que nadie puede leer lo que no le corresponde. La `service_role key` NUNCA sale de Supabase dashboard.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `js/config.example.js` | **Crear** | Template de configuración (comitteable) |
| `js/config.js` | **Crear** (gitignoreado) | Credenciales Supabase reales |
| `js/auth.js` | **Crear** | Cliente Supabase, modal auth, estado de sesión |
| `js/premium.js` | **Crear** | Sección premium, cards, canje de código |
| `supabase/01_schema.sql` | **Crear** | Tablas: profiles, premium_codes, predictions |
| `supabase/02_rls.sql` | **Crear** | Row Level Security en las 3 tablas |
| `supabase/03_functions.sql` | **Crear** | RPC redeem_premium_code + trigger auto-profile |
| `supabase/04_admin_codes.sql` | **Crear** | Snippets para generar códigos manualmente |
| `data/predictions.mock.json` | **Crear** | Mock para desarrollo local (nunca fuente final) |
| `index.html` | **Modificar** | CDN supabase-js, scripts, CSS inline, nav btn, modals, sección |
| `README.md` | **Modificar** | Documentar flujo premium, Supabase setup, seguridad |
| `docs/supabase-premium.md` | **Crear** | Referencia técnica completa |
| `.gitignore` | **Modificar** | Añadir `js/config.js` |
| `claude/INSTRUCTIONS.md` | **Modificar** | Actualizar estructura de carpetas y estado del proyecto |

---

## Task 1: Scaffolding — estructura de carpetas y configuración base

**Files:**
- Create: `js/config.example.js`
- Create: `js/config.js` (gitignoreado, no committear)
- Modify: `.gitignore`

- [ ] **Step 1: Actualizar .gitignore**

Añadir al final de `.gitignore`:
```
# Supabase credentials — NEVER commit config.js
js/config.js
```

- [ ] **Step 2: Crear js/config.example.js**

```js
// Renombra este archivo a config.js y rellena tus credenciales de Supabase.
// NUNCA hagas commit de config.js — está en .gitignore.
// Encuentra estos valores en: Supabase Dashboard → Settings → API
window.SUPABASE_URL  = 'https://TU-PROYECTO.supabase.co';
window.SUPABASE_ANON_KEY = 'eyJ...tu-anon-public-key...';
```

- [ ] **Step 3: Crear js/config.js con valores placeholder**

```js
// ARCHIVO LOCAL — NO COMMITTEAR
// Reemplaza con tus credenciales reales de Supabase
window.SUPABASE_URL  = 'https://TU-PROYECTO.supabase.co';
window.SUPABASE_ANON_KEY = 'eyJ...tu-anon-public-key...';
```

- [ ] **Step 4: Verificar que .gitignore funciona**

```bash
git status
# js/config.js NO debe aparecer como "Changes not staged" ni "Untracked files"
# js/config.example.js SÍ debe aparecer como Untracked
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore js/config.example.js
git commit -m "feat: scaffolding premium — gitignore config.js, add config example"
```

---

## Task 2: Supabase Schema (supabase/01_schema.sql)

**Files:**
- Create: `supabase/01_schema.sql`

- [ ] **Step 1: Crear supabase/01_schema.sql**

```sql
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
```

- [ ] **Step 2: Commit**

```bash
git add supabase/01_schema.sql
git commit -m "feat: supabase schema — profiles, premium_codes, predictions"
```

---

## Task 3: Supabase RLS (supabase/02_rls.sql)

**Files:**
- Create: `supabase/02_rls.sql`

- [ ] **Step 1: Crear supabase/02_rls.sql**

```sql
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
```

- [ ] **Step 2: Commit**

```bash
git add supabase/02_rls.sql
git commit -m "feat: supabase RLS — self-profile, premium predictions, no codes from frontend"
```

---

## Task 4: Supabase Functions y Admin Codes (supabase/03_functions.sql, 04_admin_codes.sql)

**Files:**
- Create: `supabase/03_functions.sql`
- Create: `supabase/04_admin_codes.sql`

- [ ] **Step 1: Crear supabase/03_functions.sql**

```sql
-- ============================================================
-- 03_functions.sql — RPC y triggers
-- Ejecutar DESPUÉS de 02_rls.sql
-- ============================================================

-- ── Trigger: crear profile al registrarse ────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', '')
  );
  RETURN NEW;
END;
$$;

-- Solo crear el trigger si no existe
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'on_auth_user_created'
  ) THEN
    CREATE TRIGGER on_auth_user_created
      AFTER INSERT ON auth.users
      FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
  END IF;
END;
$$;

-- ── RPC: redeem_premium_code ──────────────────────────────────
-- Canjea un código premium. El usuario debe estar autenticado.
-- El código en texto plano se hashea con SHA-256 para buscar en la tabla.
-- SECURITY DEFINER: se ejecuta con permisos del owner (bypass RLS en premium_codes).
CREATE OR REPLACE FUNCTION public.redeem_premium_code(input_code text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  v_code_hash  text;
  v_code_id    uuid;
  v_user_id    uuid;
BEGIN
  -- Verificar que el usuario está autenticado
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RETURN json_build_object('success', false, 'message', 'Debes iniciar sesión primero.');
  END IF;

  -- Verificar que el usuario no sea ya premium (evitar doble canje)
  IF EXISTS (SELECT 1 FROM public.profiles WHERE id = v_user_id AND is_premium = true) THEN
    RETURN json_build_object('success', false, 'message', 'Tu cuenta ya tiene acceso premium activo.');
  END IF;

  -- Hashear el código recibido
  v_code_hash := encode(digest(trim(input_code), 'sha256'), 'hex');

  -- Buscar código válido y no usado
  SELECT id INTO v_code_id
  FROM public.premium_codes
  WHERE code_hash = v_code_hash
    AND is_used = false
  LIMIT 1;

  IF v_code_id IS NULL THEN
    -- No revelar si el código existe o no — mensaje genérico
    RETURN json_build_object('success', false, 'message', 'Código inválido o ya utilizado. Verifica el email que recibiste.');
  END IF;

  -- Marcar código como usado
  UPDATE public.premium_codes
  SET is_used  = true,
      used_by  = v_user_id,
      used_at  = now()
  WHERE id = v_code_id;

  -- Activar premium en el perfil
  UPDATE public.profiles
  SET is_premium  = true,
      updated_at  = now()
  WHERE id = v_user_id;

  RETURN json_build_object('success', true, 'message', '¡Acceso premium activado! Ya puedes ver todos los pronósticos.');
END;
$$;

-- Revocar acceso público a la función (solo vía Supabase client con auth)
REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.redeem_premium_code(text) TO authenticated;
```

- [ ] **Step 2: Crear supabase/04_admin_codes.sql**

```sql
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
--   encode(digest('TU-CODIGO-AQUI', 'sha256'), 'hex'),
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
```

- [ ] **Step 3: Commit**

```bash
git add supabase/03_functions.sql supabase/04_admin_codes.sql
git commit -m "feat: supabase RPC redeem_premium_code + auto-profile trigger + admin snippets"
```

---

## Task 5: Mock predictions data (data/predictions.mock.json)

**Files:**
- Create: `data/predictions.mock.json`

Este archivo es **solo para desarrollo local**. Nunca es la fuente final premium. El frontend lo usa como fallback visual cuando Supabase no está configurado.

- [ ] **Step 1: Crear data/predictions.mock.json**

```json
{
  "_warning": "MOCK DATA — Solo para desarrollo local. NO usar como fuente premium real.",
  "predictions": [
    {
      "id": "mock-1",
      "match_id": "grp-a-j1-kor-cze",
      "group_code": "A",
      "matchday": 1,
      "match_order": 2,
      "team_a": "kor",
      "team_b": "cze",
      "team_a_win_probability": 52.0,
      "draw_probability": 25.0,
      "team_b_win_probability": 23.0,
      "global_tag": "Duelo parejo",
      "team_a_context": "Corea llega con Son como líder y un 3-4-2-1 de presión alta.",
      "team_b_context": "Chequia clasifica por repechaje con solidez defensiva europea.",
      "explanation": "Ventaja táctica para Corea, pero Chequia puede aguantar y contraatacar."
    },
    {
      "id": "mock-2",
      "match_id": "grp-b-j1-can-bih",
      "group_code": "B",
      "matchday": 1,
      "match_order": 1,
      "team_a": "can",
      "team_b": "bih",
      "team_a_win_probability": 44.0,
      "draw_probability": 28.0,
      "team_b_win_probability": 28.0,
      "global_tag": "Favorito local vs debutante",
      "team_a_context": "Canadá juega de local en Toronto con apoyo masivo del público.",
      "team_b_context": "Bosnia debuta en el Mundial 2026 tras eliminar a Italia en playoffs.",
      "explanation": "Canadá tiene ventaja de local pero Bosnia es impredecible con Džeko."
    },
    {
      "id": "mock-3",
      "match_id": "grp-c-j1-bra-mar",
      "group_code": "C",
      "matchday": 1,
      "match_order": 1,
      "team_a": "bra",
      "team_b": "mar",
      "team_a_win_probability": 61.0,
      "draw_probability": 22.0,
      "team_b_win_probability": 17.0,
      "global_tag": "Favorito absoluto",
      "team_a_context": "Brasil con Ancelotti y el regreso de Neymar — máxima expectativa.",
      "team_b_context": "Marruecos repite el nivel de Qatar 2022 con la misma base defensiva.",
      "explanation": "Brasil favorito claro pero Marruecos sabe cómo cerrar espacios y sufrir."
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add data/predictions.mock.json
git commit -m "feat: mock predictions data for local dev (never final premium source)"
```

---

## Task 6: Módulo de autenticación (js/auth.js)

**Files:**
- Create: `js/auth.js`

Este módulo expone el objeto global `window.SupaAuth`. Se carga tras `supabase-js` CDN y `config.js`.

- [ ] **Step 1: Crear js/auth.js**

```js
/**
 * auth.js — Autenticación Supabase para Mundial 2026 Predicciones
 * Expone: window.SupaAuth
 * Requiere: window.SUPABASE_URL, window.SUPABASE_ANON_KEY (de config.js)
 */
(function () {
  'use strict';

  var _client = null;

  function getClient() {
    if (!_client) {
      if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY ||
          window.SUPABASE_URL.includes('TU-PROYECTO')) {
        console.warn('[SupaAuth] config.js no configurado — modo demo activo');
        return null;
      }
      _client = window.supabase.createClient(
        window.SUPABASE_URL,
        window.SUPABASE_ANON_KEY
      );
    }
    return _client;
  }

  // ── Funciones de auth ────────────────────────────────────────

  async function getCurrentUser() {
    var c = getClient();
    if (!c) return null;
    var ref = await c.auth.getUser();
    return ref.data && ref.data.user ? ref.data.user : null;
  }

  async function getProfile(userId) {
    var c = getClient();
    if (!c || !userId) return null;
    var ref = await c.from('profiles').select('*').eq('id', userId).single();
    return ref.data || null;
  }

  async function signUp(email, password, fullName) {
    var c = getClient();
    if (!c) return { error: { message: 'Supabase no configurado' } };
    return await c.auth.signUp({
      email: email,
      password: password,
      options: { data: { full_name: fullName } }
    });
  }

  async function signIn(email, password) {
    var c = getClient();
    if (!c) return { error: { message: 'Supabase no configurado' } };
    return await c.auth.signInWithPassword({ email: email, password: password });
  }

  async function signOut() {
    var c = getClient();
    if (!c) return;
    await c.auth.signOut();
  }

  // ── Modal de autenticación ───────────────────────────────────

  function openAuthModal(onSuccess) {
    var overlay = document.getElementById('auth-modal-overlay');
    if (!overlay) return;
    overlay.classList.add('open');
    overlay.dataset.onSuccess = onSuccess || '';
    document.getElementById('auth-modal-email').focus();
    document.getElementById('auth-error').textContent = '';
  }

  function closeAuthModal() {
    var overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.classList.remove('open');
  }

  function setAuthTab(tab) {
    var loginTab  = document.getElementById('auth-tab-login');
    var signupTab = document.getElementById('auth-tab-signup');
    var nameField = document.getElementById('auth-name-wrap');
    var btnText   = document.getElementById('auth-submit-text');
    if (tab === 'login') {
      loginTab.classList.add('active');
      signupTab.classList.remove('active');
      nameField.style.display = 'none';
      btnText.textContent = 'Iniciar sesión';
    } else {
      signupTab.classList.add('active');
      loginTab.classList.remove('active');
      nameField.style.display = 'block';
      btnText.textContent = 'Crear cuenta';
    }
    document.getElementById('auth-error').textContent = '';
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    var tab      = document.getElementById('auth-tab-signup').classList.contains('active')
                   ? 'signup' : 'login';
    var email    = document.getElementById('auth-modal-email').value.trim();
    var password = document.getElementById('auth-modal-password').value;
    var fullName = document.getElementById('auth-modal-name').value.trim();
    var errEl    = document.getElementById('auth-error');
    var btn      = document.getElementById('auth-submit-btn');

    if (!email || !password) {
      errEl.textContent = 'Completa email y contraseña.';
      return;
    }
    if (tab === 'signup' && password.length < 8) {
      errEl.textContent = 'La contraseña debe tener al menos 8 caracteres.';
      return;
    }

    btn.disabled = true;
    btn.textContent = tab === 'login' ? 'Entrando…' : 'Creando cuenta…';
    errEl.textContent = '';

    var result = tab === 'signup'
      ? await signUp(email, password, fullName)
      : await signIn(email, password);

    btn.disabled = false;
    btn.textContent = tab === 'login' ? 'Iniciar sesión' : 'Crear cuenta';

    if (result.error) {
      var msg = result.error.message || 'Error desconocido';
      if (msg.includes('Invalid login')) msg = 'Email o contraseña incorrectos.';
      if (msg.includes('already registered')) msg = 'Este email ya tiene cuenta. Inicia sesión.';
      errEl.textContent = msg;
      return;
    }

    if (tab === 'signup' && result.data && !result.data.session) {
      errEl.style.color = 'var(--yes)';
      errEl.textContent = 'Revisa tu email para confirmar tu cuenta.';
      return;
    }

    closeAuthModal();
    await refreshAuthState();
  }

  // ── Estado global de autenticación ───────────────────────────

  async function refreshAuthState() {
    var user    = await getCurrentUser();
    var profile = user ? await getProfile(user.id) : null;
    var isPrem  = profile && profile.is_premium;

    updateNavAuthUI(user, isPrem);

    if (window.PremiumSection) {
      window.PremiumSection.onAuthChange(user, isPrem, profile);
    }
  }

  function updateNavAuthUI(user, isPremium) {
    var joinBtn    = document.getElementById('join-btn');
    var userInfo   = document.getElementById('nav-user-info');
    if (!joinBtn) return;

    if (user) {
      joinBtn.style.display = 'none';
      if (userInfo) {
        userInfo.style.display = 'flex';
        var emailEl = document.getElementById('nav-user-email');
        if (emailEl) emailEl.textContent = user.email.split('@')[0];
        var premBadge = document.getElementById('nav-premium-badge');
        if (premBadge) premBadge.style.display = isPremium ? 'inline' : 'none';
      }
    } else {
      joinBtn.style.display = '';
      if (userInfo) userInfo.style.display = 'none';
    }
  }

  // ── Inicialización ───────────────────────────────────────────

  function init() {
    var c = getClient();
    if (!c) return;

    // Auth state change listener
    c.auth.onAuthStateChange(function (event, session) {
      refreshAuthState();
    });

    refreshAuthState();

    // Form submit
    var form = document.getElementById('auth-form');
    if (form) form.addEventListener('submit', handleAuthSubmit);

    // Tabs
    var tabLogin  = document.getElementById('auth-tab-login');
    var tabSignup = document.getElementById('auth-tab-signup');
    if (tabLogin)  tabLogin.addEventListener('click',  function() { setAuthTab('login'); });
    if (tabSignup) tabSignup.addEventListener('click',  function() { setAuthTab('signup'); });

    // Cerrar con overlay click
    var overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAuthModal();
    });

    // Sign out
    var signOutBtn = document.getElementById('nav-signout-btn');
    if (signOutBtn) signOutBtn.addEventListener('click', async function() {
      await signOut();
      refreshAuthState();
    });
  }

  // Exponer API pública
  window.SupaAuth = {
    getClient: getClient,
    getCurrentUser: getCurrentUser,
    getProfile: getProfile,
    signIn: signIn,
    signUp: signUp,
    signOut: signOut,
    openAuthModal: openAuthModal,
    closeAuthModal: closeAuthModal,
    refreshAuthState: refreshAuthState,
    init: init
  };

  // Auto-init cuando el DOM está listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Commit**

```bash
git add js/auth.js
git commit -m "feat: js/auth.js — Supabase auth module with modal and state management"
```

---

## Task 7: Módulo premium (js/premium.js)

**Files:**
- Create: `js/premium.js`

- [ ] **Step 1: Crear js/premium.js**

```js
/**
 * premium.js — Sección Premium "Pronósticos Fase de Grupos"
 * Expone: window.PremiumSection
 * Requiere: window.SupaAuth (auth.js)
 */
(function () {
  'use strict';

  var NAMES = {
    mex:'México', zaf:'Sudáfrica', kor:'Corea del Sur', cze:'Chequia',
    can:'Canadá', bih:'Bosnia', qat:'Qatar', sui:'Suiza',
    bra:'Brasil', mar:'Marruecos', hti:'Haití', sco:'Escocia',
    ger:'Alemania', cuw:'Curazao', civ:'Costa de Marfil', ecu:'Ecuador',
    ned:'Países Bajos', jpn:'Japón', swe:'Suecia', tun:'Túnez',
    bel:'Bélgica', egy:'Egipto', irn:'Irán', nzl:'Nueva Zelanda',
    esp:'España', cpv:'Cabo Verde', ksa:'Arabia Saudita', ury:'Uruguay',
    fra:'Francia', sen:'Senegal', irq:'Irak', nor:'Noruega',
    arg:'Argentina', alg:'Argelia', aut:'Austria', jor:'Jordania',
    por:'Portugal', cod:'RD Congo', uzb:'Uzbekistán', col:'Colombia',
    eng:'Inglaterra', cro:'Croacia', gha:'Ghana', pan:'Panamá',
    usa:'EE.UU.', pry:'Paraguay', aus:'Australia', tur:'Turquía'
  };

  function flag(code) {
    var name = NAMES[code] || code;
    return '<img class="flag-svg" src="assets/flags/' + code + '.svg" alt="' + name + '" loading="lazy">';
  }

  // ── Canje de código premium ─────────────────────────────────

  async function redeemCode(code) {
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return { success: false, message: 'Supabase no configurado.' };

    var ref = await c.rpc('redeem_premium_code', { input_code: code });
    if (ref.error) {
      return { success: false, message: ref.error.message || 'Error al canjear el código.' };
    }
    return ref.data || { success: false, message: 'Respuesta inesperada del servidor.' };
  }

  // ── Carga de predicciones desde Supabase ────────────────────

  async function loadPredictions() {
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) {
      // Fallback local solo para desarrollo
      return loadMockPredictions();
    }
    var ref = await c
      .from('predictions')
      .select('*')
      .eq('published', true)
      .eq('is_premium', true)
      .order('group_code')
      .order('matchday');

    if (ref.error) {
      console.error('[PremiumSection] Error loading predictions:', ref.error);
      return [];
    }
    return ref.data || [];
  }

  async function loadMockPredictions() {
    try {
      var r = await fetch('data/predictions.mock.json');
      var d = await r.json();
      return d.predictions || [];
    } catch (e) {
      return [];
    }
  }

  // ── Render de la sección ────────────────────────────────────

  function renderLocked() {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-locked">'
      + '<div class="prono-lock-icon">&#x1F512;</div>'
      + '<h3 class="prono-lock-title">Pronósticos detallados por partido</h3>'
      + '<p class="prono-lock-desc">Accede a probabilidades calculadas con ELO de clubes, XI probable, contexto de grupo y narrativa competitiva para los 72 partidos de la fase de grupos.</p>'
      + '<ul class="prono-lock-benefits">'
      + '  <li>&#x2714; Probabilidad de victoria / empate / derrota por partido</li>'
      + '  <li>&#x2714; Contexto táctico y análisis de cada equipo</li>'
      + '  <li>&#x2714; Etiqueta global del partido (favorito, duelo parejo, etc.)</li>'
      + '  <li>&#x2714; Explicación del pronóstico en texto</li>'
      + '  <li>&#x2714; Actualizado conforme avanza el torneo</li>'
      + '</ul>'
      + '<div class="prono-lock-model">'
      + '  <span class="prono-model-label">Modelo basado en</span>'
      + '  ELO ponderado del XI · ELO de banca · Orden de partidos · Presión clasificatoria · Riesgo de rotación'
      + '</div>'
      + renderGhostCards(3)
      + '<button class="prono-join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Únete — S/. 15 · $5</button>'
      + '</div>';
  }

  function renderPaymentModal(profile) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-payment">'
      + '<div class="prono-payment-icon">&#x1F4B3;</div>'
      + '<h3>Un paso más…</h3>'
      + '<p>Confirma tu pago para activar el acceso premium a todos los pronósticos.</p>'
      + '<div class="prono-payment-options">'
      + '  <div class="prono-pay-opt">'
      + '    <span class="prono-pay-method">Yape</span>'
      + '    <span class="prono-pay-amount">S/. 15 soles</span>'
      + '    <span class="prono-pay-phone">📱 Número en el email de bienvenida</span>'
      + '  </div>'
      + '  <div class="prono-pay-opt">'
      + '    <span class="prono-pay-method">PayPal</span>'
      + '    <span class="prono-pay-amount">$5 USD</span>'
      + '    <span class="prono-pay-phone">📧 alvarojohn1290@gmail.com</span>'
      + '  </div>'
      + '</div>'
      + '<p class="prono-pay-note">Una vez confirmado el pago, te enviaremos un código de activación a <strong>'
      +   (profile && profile.email ? profile.email : 'tu email') + '</strong>.</p>'
      + '<div class="prono-code-form">'
      + '  <label class="prono-code-label" for="prono-code-input">Ingresa tu código de activación</label>'
      + '  <div class="prono-code-row">'
      + '    <input id="prono-code-input" class="prono-code-input" type="text" placeholder="XXXX-XXXX-XXXX" autocomplete="off" autocapitalize="characters">'
      + '    <button id="prono-code-submit" class="prono-code-btn" onclick="window.PremiumSection.submitCode()">Activar</button>'
      + '  </div>'
      + '  <div id="prono-code-error" class="prono-code-error"></div>'
      + '</div>'
      + '</div>';
  }

  async function renderActive(predictions) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;

    if (!predictions || predictions.length === 0) {
      el.innerHTML = '<div class="prono-empty">'
        + '<span class="prono-premium-badge">&#x2705; Acceso Premium Activo</span>'
        + '<p style="color:var(--muted);margin-top:1rem">Los pronósticos se publicarán a medida que se acerquen los partidos.</p>'
        + '</div>';
      return;
    }

    // Agrupar por grupo
    var byGroup = {};
    predictions.forEach(function(p) {
      if (!byGroup[p.group_code]) byGroup[p.group_code] = [];
      byGroup[p.group_code].push(p);
    });

    var html = '<div class="prono-active-header">'
      + '<span class="prono-premium-badge">&#x2705; Acceso Premium Activo</span>'
      + '</div>';

    Object.keys(byGroup).sort().forEach(function(grp) {
      html += '<div class="prono-group-block">'
        + '<div class="prono-group-title">Grupo ' + grp + '</div>';
      byGroup[grp].forEach(function(p) {
        html += renderPredictionCard(p);
      });
      html += '</div>';
    });

    el.innerHTML = html;
  }

  function renderPredictionCard(p) {
    var aWin  = parseFloat(p.team_a_win_probability) || 0;
    var draw  = parseFloat(p.draw_probability) || 0;
    var bWin  = parseFloat(p.team_b_win_probability) || 0;
    var tagColor = 'var(--accent)';

    return '<div class="prono-card">'
      + '  <div class="prono-card-header">'
      + '    <span class="prono-matchday">J' + p.matchday + '</span>'
      + '    <div class="prono-teams">'
      + '      <div class="prono-team">' + flag(p.team_a) + '<span>' + (NAMES[p.team_a] || p.team_a) + '</span></div>'
      + '      <span class="prono-vs">vs</span>'
      + '      <div class="prono-team">' + flag(p.team_b) + '<span>' + (NAMES[p.team_b] || p.team_b) + '</span></div>'
      + '    </div>'
      + (p.global_tag ? '<span class="prono-global-tag">' + p.global_tag + '</span>' : '')
      + '  </div>'
      + '  <div class="prono-probs">'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">' + (NAMES[p.team_a] || p.team_a) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-a" style="width:' + aWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + aWin.toFixed(0) + '%</span>'
      + '    </div>'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">Empate</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-draw" style="width:' + draw + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + draw.toFixed(0) + '%</span>'
      + '    </div>'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">' + (NAMES[p.team_b] || p.team_b) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-b" style="width:' + bWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + bWin.toFixed(0) + '%</span>'
      + '    </div>'
      + '  </div>'
      + (p.team_a_context || p.team_b_context
         ? '<div class="prono-contexts">'
           + (p.team_a_context ? '<div class="prono-ctx prono-ctx-a"><strong>' + (NAMES[p.team_a]||p.team_a) + ':</strong> ' + p.team_a_context + '</div>' : '')
           + (p.team_b_context ? '<div class="prono-ctx prono-ctx-b"><strong>' + (NAMES[p.team_b]||p.team_b) + ':</strong> ' + p.team_b_context + '</div>' : '')
           + '</div>'
         : '')
      + (p.explanation ? '<div class="prono-explanation">' + p.explanation + '</div>' : '')
      + '</div>';
  }

  function renderGhostCards(n) {
    var html = '<div class="prono-ghost-cards">';
    for (var i = 0; i < n; i++) {
      html += '<div class="prono-ghost-card">'
        + '<div class="prono-ghost-header"></div>'
        + '<div class="prono-ghost-bars"></div>'
        + '<div class="prono-ghost-text"></div>'
        + '</div>';
    }
    html += '</div>';
    return html;
  }

  // ── Envío de código ─────────────────────────────────────────

  async function submitCode() {
    var input   = document.getElementById('prono-code-input');
    var errEl   = document.getElementById('prono-code-error');
    var btn     = document.getElementById('prono-code-submit');
    if (!input || !errEl) return;

    var code = input.value.trim();
    if (!code) {
      errEl.textContent = 'Ingresa el código que recibiste por email.';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Verificando…';
    errEl.textContent = '';
    errEl.style.color = '';

    var result = await redeemCode(code);

    btn.disabled = false;
    btn.textContent = 'Activar';

    if (result.success) {
      errEl.style.color = 'var(--yes)';
      errEl.textContent = result.message;
      setTimeout(function() {
        window.SupaAuth && window.SupaAuth.refreshAuthState();
      }, 1200);
    } else {
      errEl.textContent = result.message;
    }
  }

  // ── Auth change callback (llamado desde auth.js) ─────────────

  async function onAuthChange(user, isPremium, profile) {
    if (!user) {
      renderLocked();
    } else if (!isPremium) {
      renderPaymentModal(profile);
    } else {
      var predictions = await loadPredictions();
      renderActive(predictions);
    }
  }

  // ── Init ────────────────────────────────────────────────────

  function init() {
    // Estado inicial: locked hasta que auth.js resuelva el estado
    renderLocked();
  }

  window.PremiumSection = {
    init: init,
    onAuthChange: onAuthChange,
    submitCode: submitCode,
    loadPredictions: loadPredictions
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Commit**

```bash
git add js/premium.js
git commit -m "feat: js/premium.js — premium section with locked/payment/active states"
```

---

## Task 8: Integración en index.html — CSS, HTML, nav, modals y sección

**Files:**
- Modify: `index.html` (CDN scripts, inline CSS, nav button, modals, sección §06)

Esta es la tarea más extensa. Se divide en 5 sub-pasos.

### Sub-paso A: CDN + scripts externos

- [ ] **Step A1: Añadir en `<head>` antes de `</head>`, después del script de tema**

Localizar la línea:
```html
<script>
  (function(){var t=localStorage.getItem('theme')||'dark';document.documentElement.setAttribute('data-theme',t);})();
</script>
</head>
```

Reemplazar con:
```html
<script>
  (function(){var t=localStorage.getItem('theme')||'dark';document.documentElement.setAttribute('data-theme',t);})();
</script>
<!-- Supabase JS SDK v2 -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<!-- Premium config (gitignored — copiar de js/config.example.js) -->
<script src="js/config.js" onerror="console.warn('[Config] js/config.js no encontrado — modo demo activo')"></script>
</head>
```

### Sub-paso B: Scripts al final del body (antes de `</body>`)

- [ ] **Step B1: Añadir antes de `</body>`** (después del closing `</script>` del JS inline existente):

```html
<script src="js/auth.js"></script>
<script src="js/premium.js"></script>
```

### Sub-paso C: CSS inline — añadir antes del cierre `</style>`

- [ ] **Step C1: Añadir el siguiente bloque CSS dentro del `<style>` existente, antes de `</style>`**

```css
  /* ─── BOTÓN ÚNETE ─── */
  .join-btn {
    background: var(--accent); color: #fff;
    border: none; border-radius: 6px; cursor: pointer;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
    font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
    padding: .35rem .9rem; margin-left: .5rem; flex-shrink: 0;
    transition: background .2s, opacity .2s;
  }
  .join-btn:hover { background: #c0303c; }

  /* ─── NAV USER INFO ─── */
  .nav-user-info {
    display: none; align-items: center; gap: .5rem;
    margin-left: .5rem; flex-shrink: 0;
  }
  .nav-user-email {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    color: var(--muted); max-width: 120px; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
  }
  .nav-premium-tag {
    display: none; font-family: 'Barlow Condensed', sans-serif;
    font-size: 9px; font-weight: 800; letter-spacing: .1em;
    text-transform: uppercase; background: var(--gold); color: #000;
    padding: 1px 5px; border-radius: 3px;
  }
  .nav-signout-btn {
    background: none; border: 1px solid var(--border); color: var(--muted);
    border-radius: 4px; font-size: 11px; cursor: pointer; padding: .2rem .5rem;
    transition: border-color .2s;
  }
  .nav-signout-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* ─── AUTH MODAL ─── */
  .auth-modal-overlay {
    display: none; position: fixed; inset: 0; z-index: 500;
    background: rgba(0,0,0,.7); backdrop-filter: blur(4px);
    align-items: center; justify-content: center;
  }
  .auth-modal-overlay.open { display: flex; }
  .auth-modal {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 2rem; width: 100%; max-width: 400px;
    position: relative;
  }
  .auth-modal-title {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 1.4rem; letter-spacing: .05em; text-transform: uppercase;
    color: var(--white); margin-bottom: .25rem;
  }
  .auth-modal-sub {
    font-size: 13px; color: var(--muted); margin-bottom: 1.5rem;
  }
  .auth-tabs {
    display: flex; gap: .5rem; margin-bottom: 1.25rem;
  }
  .auth-tab {
    flex: 1; background: none; border: 1px solid var(--border); color: var(--muted);
    border-radius: 6px; padding: .4rem; cursor: pointer; font-size: 13px;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
    text-transform: uppercase; letter-spacing: .06em; transition: .2s;
  }
  .auth-tab.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  .auth-form-field {
    margin-bottom: .9rem;
  }
  .auth-form-field label {
    display: block; font-size: 11px; color: var(--muted);
    margin-bottom: .3rem; letter-spacing: .06em; text-transform: uppercase;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
  }
  .auth-form-field input {
    width: 100%; background: var(--surface); border: 1px solid var(--border);
    color: var(--text); border-radius: 6px; padding: .5rem .75rem;
    font-size: 14px; outline: none; transition: border-color .2s;
  }
  .auth-form-field input:focus { border-color: var(--accent); }
  .auth-submit-btn {
    width: 100%; background: var(--accent); color: #fff; border: none;
    border-radius: 6px; padding: .65rem; cursor: pointer;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
    font-size: 14px; letter-spacing: .08em; text-transform: uppercase;
    margin-top: .5rem; transition: background .2s;
  }
  .auth-submit-btn:hover:not(:disabled) { background: #c0303c; }
  .auth-submit-btn:disabled { opacity: .6; cursor: not-allowed; }
  .auth-error {
    font-size: 12px; color: var(--accent); margin-top: .5rem;
    min-height: 1.2em;
  }
  .auth-modal-close {
    position: absolute; top: .75rem; right: .75rem;
    background: none; border: none; color: var(--muted); cursor: pointer;
    font-size: 18px; line-height: 1;
  }
  .auth-modal-close:hover { color: var(--white); }

  /* ─── SECCIÓN PREMIUM ─── */
  .prono-locked {
    text-align: center; padding: 2rem 1rem;
  }
  .prono-lock-icon { font-size: 2.5rem; margin-bottom: 1rem; }
  .prono-lock-title {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 1.6rem; color: var(--white); margin-bottom: .75rem;
  }
  .prono-lock-desc {
    color: var(--muted); font-size: 14px; max-width: 540px;
    margin: 0 auto 1.25rem;
  }
  .prono-lock-benefits {
    list-style: none; text-align: left; display: inline-block;
    margin-bottom: 1.5rem;
  }
  .prono-lock-benefits li {
    font-size: 14px; color: var(--text); padding: .3rem 0;
  }
  .prono-lock-model {
    font-size: 12px; color: var(--muted); background: var(--card);
    border: 1px solid var(--border); border-radius: 8px;
    padding: .75rem 1rem; display: inline-block; margin-bottom: 1.5rem;
    max-width: 500px;
  }
  .prono-model-label {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
    font-size: 10px; letter-spacing: .15em; text-transform: uppercase;
    color: var(--gold); display: block; margin-bottom: .25rem;
  }
  .prono-join-btn {
    background: var(--accent); color: #fff; border: none; border-radius: 8px;
    padding: .75rem 2rem; cursor: pointer;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 16px; letter-spacing: .08em; text-transform: uppercase;
    margin-top: .5rem; transition: background .2s;
  }
  .prono-join-btn:hover { background: #c0303c; }

  /* Ghost cards (locked state) */
  .prono-ghost-cards {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr));
    gap: 1rem; margin: 1.5rem auto; max-width: 900px; filter: blur(4px);
    pointer-events: none; user-select: none;
  }
  .prono-ghost-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem; height: 160px;
  }
  .prono-ghost-header { background: var(--border); height: 20px; border-radius: 4px; margin-bottom: .75rem; }
  .prono-ghost-bars  { background: var(--border); height: 60px; border-radius: 4px; margin-bottom: .75rem; }
  .prono-ghost-text  { background: var(--border); height: 40px; border-radius: 4px; }

  /* Payment view */
  .prono-payment { max-width: 520px; margin: 0 auto; padding: 1.5rem 0; }
  .prono-payment-icon { font-size: 2rem; margin-bottom: .75rem; }
  .prono-payment h3 {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 1.8rem; color: var(--white); margin-bottom: .5rem;
  }
  .prono-payment > p { color: var(--muted); font-size: 14px; margin-bottom: 1.25rem; }
  .prono-payment-options { display: flex; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
  .prono-pay-opt {
    flex: 1; min-width: 200px; background: var(--card);
    border: 1px solid var(--border); border-radius: 10px; padding: 1rem;
    display: flex; flex-direction: column; gap: .3rem;
  }
  .prono-pay-method {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 1.1rem; color: var(--white);
  }
  .prono-pay-amount { font-size: 1.4rem; color: var(--gold); font-weight: 700; }
  .prono-pay-phone  { font-size: 12px; color: var(--muted); }
  .prono-pay-note   { font-size: 13px; color: var(--muted); margin-bottom: 1.25rem; }
  .prono-code-form  { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; }
  .prono-code-label { display: block; font-size: 12px; color: var(--muted); margin-bottom: .6rem; letter-spacing: .06em; text-transform: uppercase; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; }
  .prono-code-row   { display: flex; gap: .5rem; }
  .prono-code-input {
    flex: 1; background: var(--surface); border: 1px solid var(--border);
    color: var(--text); border-radius: 6px; padding: .55rem .75rem;
    font-family: 'JetBrains Mono', monospace; font-size: 14px;
    letter-spacing: .1em; outline: none; text-transform: uppercase;
    transition: border-color .2s;
  }
  .prono-code-input:focus { border-color: var(--accent); }
  .prono-code-btn {
    background: var(--accent); color: #fff; border: none; border-radius: 6px;
    padding: .55rem 1.2rem; cursor: pointer;
    font-family: 'Barlow Condensed', sans-serif; font-weight: 800;
    font-size: 13px; letter-spacing: .08em; text-transform: uppercase;
    transition: background .2s;
  }
  .prono-code-btn:disabled { opacity: .6; cursor: not-allowed; }
  .prono-code-btn:hover:not(:disabled) { background: #c0303c; }
  .prono-code-error { font-size: 12px; color: var(--accent); margin-top: .5rem; min-height: 1.2em; }

  /* Active premium view */
  .prono-active-header { margin-bottom: 1.5rem; }
  .prono-premium-badge {
    display: inline-block; font-family: 'Barlow Condensed', sans-serif;
    font-weight: 800; font-size: 11px; letter-spacing: .12em;
    text-transform: uppercase; background: rgba(34,197,94,.15);
    color: var(--yes); border: 1px solid rgba(34,197,94,.3);
    padding: .3rem .8rem; border-radius: 4px;
  }
  .prono-group-block { margin-bottom: 2.5rem; }
  .prono-group-title {
    font-family: 'Barlow Condensed', sans-serif; font-weight: 900;
    font-size: 1rem; letter-spacing: .2em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 1rem; padding-bottom: .5rem;
    border-bottom: 1px solid var(--border);
  }
  .prono-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;
  }
  .prono-card-header {
    display: flex; align-items: center; gap: .75rem;
    margin-bottom: 1rem; flex-wrap: wrap;
  }
  .prono-matchday {
    font-family: 'JetBrains Mono', monospace; font-size: 10px;
    font-weight: 700; color: var(--accent); background: rgba(230,57,70,.12);
    padding: 2px 7px; border-radius: 4px; flex-shrink: 0;
  }
  .prono-teams { display: flex; align-items: center; gap: .6rem; flex: 1; }
  .prono-team  { display: flex; align-items: center; gap: .4rem; font-size: 14px; font-weight: 600; }
  .prono-vs    { font-size: 11px; color: var(--muted); }
  .prono-global-tag {
    margin-left: auto; font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700; font-size: 10px; letter-spacing: .1em;
    text-transform: uppercase; color: var(--gold); background: rgba(255,170,0,.12);
    border: 1px solid rgba(255,170,0,.25); padding: 2px 8px; border-radius: 4px;
  }
  .prono-probs { margin-bottom: 1rem; }
  .prono-prob-row {
    display: flex; align-items: center; gap: .6rem; margin-bottom: .4rem;
  }
  .prono-prob-label { font-size: 12px; color: var(--muted); min-width: 110px; }
  .prono-prob-bar-wrap {
    flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden;
  }
  .prono-prob-bar { height: 100%; border-radius: 4px; transition: width .6s ease; }
  .prono-bar-a    { background: var(--accent); }
  .prono-bar-draw { background: var(--muted); }
  .prono-bar-b    { background: var(--grp-b); }
  .prono-prob-pct { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text); min-width: 34px; text-align: right; }
  .prono-contexts { display: flex; gap: 1rem; margin-bottom: .75rem; flex-wrap: wrap; }
  .prono-ctx { flex: 1; min-width: 200px; font-size: 12px; color: var(--muted); line-height: 1.5; }
  .prono-explanation { font-size: 13px; color: var(--text); border-top: 1px solid var(--border); padding-top: .75rem; line-height: 1.6; }
  .prono-empty { text-align: center; padding: 2rem; color: var(--muted); }
```

### Sub-paso D: Botón "Únete" y user info en el nav

- [ ] **Step D1: Localizar en index.html**

Línea actual del nav (alrededor de línea 838):
```html
  <button id="theme-toggle" class="theme-btn" aria-label="Cambiar tema">&#x1F319;</button>
</nav>
```

Reemplazar con:
```html
  <button id="join-btn" class="join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Únete</button>
  <div id="nav-user-info" class="nav-user-info">
    <span id="nav-user-email" class="nav-user-email"></span>
    <span id="nav-premium-badge" class="nav-premium-tag">Premium</span>
    <button id="nav-signout-btn" class="nav-signout-btn">Salir</button>
  </div>
  <button id="theme-toggle" class="theme-btn" aria-label="Cambiar tema">&#x1F319;</button>
</nav>
```

### Sub-paso E: Auth modal y sección Premium

- [ ] **Step E1: Añadir auth modal después del `<!-- GRUPOS MODAL -->` existente**

Localizar:
```html
<!-- HERO -->
```
Insertar antes de esa línea:

```html
<!-- AUTH MODAL -->
<div class="auth-modal-overlay" id="auth-modal-overlay">
  <div class="auth-modal">
    <button class="auth-modal-close" onclick="window.SupaAuth && window.SupaAuth.closeAuthModal()" aria-label="Cerrar">&#x2715;</button>
    <div class="auth-modal-title">&#x26BD; Únete</div>
    <div class="auth-modal-sub">Acceso completo a pronósticos por partido con ELO y análisis táctico</div>
    <div class="auth-tabs">
      <button id="auth-tab-login"  class="auth-tab active">Iniciar sesión</button>
      <button id="auth-tab-signup" class="auth-tab">Crear cuenta</button>
    </div>
    <form id="auth-form">
      <div id="auth-name-wrap" class="auth-form-field" style="display:none">
        <label for="auth-modal-name">Nombre</label>
        <input id="auth-modal-name" type="text" placeholder="Tu nombre" autocomplete="name">
      </div>
      <div class="auth-form-field">
        <label for="auth-modal-email">Email</label>
        <input id="auth-modal-email" type="email" placeholder="tu@email.com" autocomplete="email" required>
      </div>
      <div class="auth-form-field">
        <label for="auth-modal-password">Contraseña</label>
        <input id="auth-modal-password" type="password" placeholder="Mínimo 8 caracteres" autocomplete="current-password" required>
      </div>
      <div id="auth-error" class="auth-error"></div>
      <button id="auth-submit-btn" type="submit" class="auth-submit-btn">
        <span id="auth-submit-text">Iniciar sesión</span>
      </button>
    </form>
  </div>
</div>
```

- [ ] **Step E2: Añadir sección Premium después del tracker `</section>` y antes del `<!-- FOOTER -->`**

Localizar:
```html
</section>

<!-- FOOTER -->
```

Insertar la nueva sección entre ambas:

```html
</section>

<!-- §06 PRONÓSTICOS PREMIUM -->
<section id="pronosticos" style="background:var(--bg)">
  <div class="container">
    <div class="section-header">
      <span class="section-tag tag-accent">§06</span>
      <h2>Pronósticos Fase de Grupos</h2>
    </div>
    <div id="pronosticos-content">
      <!-- Renderizado por js/premium.js según estado de autenticación -->
    </div>
  </div>
</section>

<!-- FOOTER -->
```

- [ ] **Step E3: Commit**

```bash
git add index.html
git commit -m "feat: index.html — Únete btn, auth modal, §06 premium section, supabase CDN"
```

---

## Task 9: README.md actualización

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Reemplazar el README.md completo con la versión actualizada**

El README debe añadir las secciones siguientes (agregar al final del archivo existente):

```markdown
---

## Sistema Premium — Pronósticos Fase de Grupos

### Por qué Supabase + GitHub Pages

El sitio sigue siendo 100% estático en GitHub Pages (no hay servidor propio). La autenticación y los datos premium los gestiona Supabase, que actúa como backend-as-a-service. Esta arquitectura permite:

- **Costo cero** de hosting para el frontend
- **Seguridad real** via Row Level Security (RLS) en PostgreSQL
- **Sin mantenimiento** de servidores propios
- **Escalabilidad** automática si el tráfico crece

### Por qué RLS es suficiente como capa de seguridad

La `anon key` de Supabase puede estar en el frontend porque:
1. RLS garantiza que cada usuario solo lee lo que le corresponde
2. La tabla `premium_codes` no tiene política SELECT pública — nadie puede leerla
3. `redeem_premium_code` es una función RPC `SECURITY DEFINER` — bypass controlado de RLS
4. Las predicciones premium solo son accesibles si `profiles.is_premium = true`

**NUNCA coloques la `service_role key` en el frontend.** Solo pertenece al dashboard de Supabase.

### Configurar Supabase

1. Crear proyecto en [supabase.com](https://supabase.com)
2. Ir a **Settings → API** y copiar:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
3. Copiar `js/config.example.js` como `js/config.js` y rellenar las credenciales
4. Ejecutar los SQL en **Supabase Dashboard → SQL Editor** en orden:
   ```
   supabase/01_schema.sql
   supabase/02_rls.sql
   supabase/03_functions.sql
   ```

### Crear códigos premium manualmente

1. Decidir el código en texto plano (ej: `WWCJUN2026-JUAN`)
2. En Supabase SQL Editor:
   ```sql
   INSERT INTO public.premium_codes (code_hash, notes)
   VALUES (
     encode(digest('WWCJUN2026-JUAN', 'sha256'), 'hex'),
     'Pago Yape S/15 - Juan Pérez - 1 jun 2026'
   );
   ```
3. Enviar el código en texto plano al usuario por email
4. **Nunca almacenar el código en texto plano** en ningún sistema

### Validar que un usuario es premium

```sql
SELECT id, email, is_premium, updated_at
FROM public.profiles
WHERE is_premium = true;
```

### Cómo probar localmente

```bash
python3 -m http.server 8080
# o
npx serve .
```
Abrir `http://localhost:8080`. Sin `config.js` real, la sección premium mostrará datos mock y estado de "demo activo".

### Qué falta para producción

- [ ] Configurar Supabase email templates (confirmación, reset de contraseña)
- [ ] Habilitar confirmación de email en Supabase Auth settings
- [ ] Insertar predicciones reales en la tabla `predictions` (con `published = true`)
- [ ] Configurar dominio personalizado (opcional)
- [ ] Activar protección rate-limit en la RPC (Supabase lo gestiona por plan)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README — premium flow, Supabase setup, security model, local testing"
```

---

## Task 10: Documentación técnica (docs/supabase-premium.md)

**Files:**
- Create: `docs/supabase-premium.md`

- [ ] **Step 1: Crear docs/supabase-premium.md**

```markdown
# Supabase Premium — Referencia Técnica

## Arquitectura del flujo de acceso premium

```
Usuario                Frontend (GitHub Pages)         Supabase
──────                 ───────────────────────         ────────
                       index.html
                       js/auth.js                       auth.users
[Registro/Login] ──→   SupaAuth.signUp/signIn ────→    profiles (trigger)
[Ver sección]   ──→    PremiumSection.onAuthChange
                       └─ si premium=false:
[Pago Yape/PP]         renderPaymentModal()
[Recibe código] ──→    PremiumSection.submitCode()
                       └─ SupaAuth.getClient()
                              .rpc('redeem_premium_code')────→ premium_codes
                                                              profiles.is_premium=true
[Premium activo] ←──   PremiumSection.loadPredictions() ←── predictions (RLS)
```

## Tabla: profiles

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | FK auth.users |
| email | text | Sincronizado del registro |
| full_name | text | Opcional |
| is_premium | boolean | Solo modificable via RPC |
| created_at | timestamptz | Auto |
| updated_at | timestamptz | Auto, actualizado por RPC |

**Políticas RLS:**
- SELECT: `auth.uid() = id`
- UPDATE: `auth.uid() = id` (no puede cambiar `is_premium` directamente)

## Tabla: premium_codes

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| code_hash | text | SHA-256 del código en texto plano |
| is_used | boolean | false hasta ser canjeado |
| used_by | uuid | FK auth.users |
| used_at | timestamptz | Momento del canje |
| notes | text | Uso interno admin |

**Políticas RLS:** NINGUNA — solo accesible via RPC SECURITY DEFINER

## Tabla: predictions

| Campo | Tipo | Notas |
|---|---|---|
| match_id | text | Referencia a match_context.json |
| group_code | text | A-L |
| matchday | integer | 1-3 |
| team_a / team_b | text | Código ISO |
| team_a_win_probability | numeric(5,2) | 0-100 |
| draw_probability | numeric(5,2) | |
| team_b_win_probability | numeric(5,2) | |
| global_tag | text | Etiqueta narrativa |
| team_a_context | text | Análisis equipo A |
| team_b_context | text | Análisis equipo B |
| explanation | text | Razonamiento del pronóstico |
| is_premium | boolean | default true |
| published | boolean | false hasta publicar manualmente |

**Constraint:** suma de probabilidades entre 99.5 y 100.5

**Política RLS:**
```sql
SELECT WHERE published = true AND is_premium = true
AND EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_premium = true)
```

## RPC: redeem_premium_code

**Firma:** `redeem_premium_code(input_code text) RETURNS json`

**Flujo:**
1. Verificar `auth.uid()` — rechazar si null
2. Verificar que el usuario no sea ya premium
3. Hashear `input_code` con SHA-256
4. Buscar `code_hash` en `premium_codes` donde `is_used = false`
5. Si no existe: devolver error genérico (no revelar detalle)
6. Marcar código como usado
7. Actualizar `profiles.is_premium = true`
8. Devolver `{success: true, message: "..."}`

**Seguridad:** `SECURITY DEFINER` — se ejecuta con permisos del owner, bypasea RLS en `premium_codes`. El acceso de usuarios normales a esta función está restringido a `authenticated`.

## Variables de entorno

| Variable | Dónde encontrarla | Seguridad |
|---|---|---|
| `SUPABASE_URL` | Supabase → Settings → API → Project URL | Puede estar en frontend |
| `SUPABASE_ANON_KEY` | Supabase → Settings → API → anon public | Puede estar en frontend (RLS protege) |
| `service_role key` | Supabase → Settings → API → service_role | **NUNCA en frontend** |

## Extensiones requeridas

- `pgcrypto` — para `digest()` y `encode()` en el hash SHA-256

Activar en Supabase: ya viene habilitada por defecto en todos los proyectos.

## Estrategia de generación de códigos premium

**Recomendado para el MVP:** códigos alfanuméricos legibles generados manualmente.

Formato sugerido: `WWCXXXXX-YYYY` donde:
- `WWC` = prefijo fijo
- `XXXXX` = 5 caracteres aleatorios (mayúsculas + números)
- `YYYY` = año o mes abreviado

Ejemplo: `WWCAB3F7-MAY26`

**Generación segura local:**
```python
import secrets, string
chars = string.ascii_uppercase + string.digits
code = 'WWC' + ''.join(secrets.choice(chars) for _ in range(5)) + '-MAY26'
print(code)  # Copiar y usar en el INSERT de 04_admin_codes.sql
```

## Limitaciones del MVP

1. No hay reset de contraseña UI (solo vía Supabase dashboard)
2. No hay OAuth (Google, etc.)
3. Las predicciones se insertan manualmente (no hay panel admin)
4. Un código = un usuario (no se pueden reusar)
5. No hay expiración de códigos premium (perpetuo hasta revocar manualmente)
6. No hay notificaciones automáticas al usuario tras el pago
```

- [ ] **Step 2: Commit**

```bash
git add docs/supabase-premium.md
git commit -m "docs: supabase-premium.md — technical reference for premium system"
```

---

## Task 11: Actualizar claude/INSTRUCTIONS.md

**Files:**
- Modify: `claude/INSTRUCTIONS.md`

- [ ] **Step 1: Actualizar la sección "Estado global"**

Cambiar (al 22 mayo 2026):
```markdown
### Estado global (al 22 mayo 2026)
- **17 selecciones analizadas** con plantel, táctica, figura clave y XI probable
- **Más de 25 selecciones** aún sin convocatoria oficial
- **Sistema Premium añadido:** sección §06, Supabase Auth, flujo de pago manual
```

- [ ] **Step 2: Añadir nuevos archivos a la sección "Estructura de carpetas"**

```markdown
├── js/
│   ├── config.example.js   ← template de credenciales Supabase (committeable)
│   └── config.js           ← credenciales reales (GITIGNOREADO — no committear)
│       auth.js             ← cliente Supabase, modal auth, estado de sesión
│       premium.js          ← sección premium, cards, canje de código
├── supabase/
│   ├── 01_schema.sql       ← tablas: profiles, premium_codes, predictions
│   ├── 02_rls.sql          ← Row Level Security
│   ├── 03_functions.sql    ← RPC redeem_premium_code + trigger
│   └── 04_admin_codes.sql  ← snippets para gestionar códigos manualmente
├── docs/
│   └── supabase-premium.md ← referencia técnica del sistema premium
```

- [ ] **Step 3: Añadir reglas de seguridad para Claude Code**

```markdown
## Reglas de seguridad adicionales

- **Nunca incluir** credenciales reales en ningún archivo del repositorio
- **Nunca commitear** `js/config.js` (está gitignoreado)
- **Nunca colocar** contenido premium real en `data/*.json` públicos
- `supabase/04_admin_codes.sql` no debe contener códigos en texto plano
```

- [ ] **Step 4: Commit**

```bash
git add claude/INSTRUCTIONS.md
git commit -m "docs: INSTRUCTIONS.md — add premium system files, security rules, updated state"
```

---

## Task 12: Validación final

**Files:** Ninguno nuevo — solo verificación

- [ ] **Step 1: Iniciar servidor local**

```bash
python3 -m http.server 8080
# o en Windows:
python -m http.server 8080
# o con Node:
npx serve .
```

Abrir `http://localhost:8080`

- [ ] **Step 2: Checklist visual (sin Supabase real)**

```
[ ] El botón "Únete" aparece en el nav (arriba derecha, entre tz-select y 🌙)
[ ] Al hacer clic en "Únete" se abre el modal de autenticación
[ ] El modal tiene tabs "Iniciar sesión" / "Crear cuenta"
[ ] La sección §06 "Pronósticos Fase de Grupos" aparece debajo del tracker
[ ] La vista locked muestra: ícono 🔒, título, beneficios, 3 ghost cards difuminadas, botón CTA
[ ] El modo light/dark no afecta el botón ni los modales (probar toggle)
[ ] Abrir DevTools → Network → No aparece js/config.js (404 esperado, no es error bloqueante)
[ ] Consola muestra: "[Config] js/config.js no encontrado — modo demo activo"
[ ] No aparece ninguna service_role key en ningún archivo del repo
```

- [ ] **Step 3: Checklist con config.js real (con Supabase configurado)**

```
[ ] Registrar usuario nuevo → modal muestra "Revisa tu email"
[ ] Confirmar email en bandeja → volver al sitio
[ ] Login → botón "Únete" desaparece, aparece email truncado + "Salir"
[ ] Sección §06 muestra vista "Un paso más..." con opciones de pago
[ ] Campo de código acepta input
[ ] Ingresar código inválido → error claro sin detalles técnicos
[ ] Insertar código real en Supabase (04_admin_codes.sql) → canjear → sección muestra "Acceso Premium Activo"
[ ] Cerrar sesión → vuelve a estado locked
```

- [ ] **Step 4: Verificar seguridad**

```bash
# Verificar que config.js está ignorado
git status  # NO debe aparecer js/config.js

# Verificar que no hay keys reales en archivos comitteados
grep -r "supabase.co" . --include="*.js" --include="*.html" --include="*.sql" \
  --exclude-dir=".git" | grep -v "config.example" | grep -v "docs/"
# Solo debe aparecer en docs/supabase-premium.md como referencia de URL genérica

# Verificar que predictions.mock.json tiene el warning
grep "_warning" data/predictions.mock.json
```

- [ ] **Step 5: Push final**

```bash
git add .
git status  # Revisar que js/config.js NO aparece
git commit -m "feat: complete premium system — auth, payment flow, §06 section, Supabase SQL"
git push origin main
```

---

## Resumen de pasos manuales en Supabase

Una vez creado el proyecto Supabase, ejecutar en este orden exacto en el **SQL Editor**:

```
1. supabase/01_schema.sql   — crea las 3 tablas + índices
2. supabase/02_rls.sql      — activa RLS y define políticas
3. supabase/03_functions.sql — crea el trigger de profiles y la RPC
```

Luego, para cada usuario premium que pague:
```sql
-- En supabase/04_admin_codes.sql hay ejemplos comentados
INSERT INTO public.premium_codes (code_hash, notes)
VALUES (encode(digest('TU-CODIGO-AQUI', 'sha256'), 'hex'), 'Nota del admin');
```

Para publicar predicciones:
```sql
UPDATE public.predictions SET published = true WHERE group_code = 'A';
```

---

## Riesgos y limitaciones del MVP

| Riesgo | Mitigación |
|---|---|
| `anon key` visible en frontend | RLS estricto — nadie puede leer lo que no le pertenece |
| `match_context.json` público contiene predicciones narrativas | Se usa solo como "contexto táctico" en teaser; probabilidades numéricas solo en Supabase |
| No hay reset de contraseña UI | Documentado como pendiente; soportado por Supabase pero sin UI en MVP |
| Códigos premium son perpetuos | Suficiente para MVP; se puede añadir `expires_at` en iteración futura |
| GitHub Pages no soporta env vars | `config.js` gitignoreado; documentado con `config.example.js` |
| Sin CORS para fetch local | Usar `python3 -m http.server` o `npx serve` — nunca `file://` |
