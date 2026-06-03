# Spec: Fixture CTA + País en registro

## 1. Fixture cards clickables

Cada `.cal-match` en `.team-fixtures` abre el modal "Únete" al hacer clic.

**Comportamiento por estado:**
- No autenticado → `SupaAuth.openAuthModal()` en pestaña Crear cuenta
- Autenticado, no premium → scroll a `#pronosticos`
- Premium → scroll a `#pronosticos`

**Implementación:**
- `window.__authState = { user: null, isPremium: false }` actualizado en `refreshAuthState()` (auth.js)
- Función `handleFixtureClick()` en script inline de index.html
- `renderTeamFixtures()` añade `onclick="handleFixtureClick()"` y clase `fixture-cta` a cada `.cal-match`
- CSS: `.team-fixtures .fixture-cta { cursor:pointer }` + hover con `border-left-color: var(--accent)` y badge `⚽ Ver pronóstico →`

## 2. Campo País en registro

**HTML:** `<select id="auth-modal-country">` debajo de Nombre, visible solo en tab signup.

**Lista plana alfabética (sin optgroup):** 48 WC2026 + CONMEBOL no clasificados (Bolivia, Chile, Perú, Venezuela) + CONCACAF no clasificados (Costa Rica, El Salvador, Guatemala, Honduras, Jamaica, Trinidad y Tobago) + "Otro".

**Supabase:**
- Migración: `ALTER TABLE public.profiles ADD COLUMN country text;`
- `handle_new_user` trigger lee `raw_user_meta_data->>'country'`
- `signUp()` en auth.js pasa `country` en `options.data`

**Campo:** opcional (no required), `setAuthTab()` lo muestra/oculta junto a Nombre.
