-- 08_security_advisors_hardening.sql
-- Fixes security advisor warnings without changing function bodies.
-- Apply AFTER 03_functions.sql and AFTER any SQL that recreates these functions.

-- Trigger helper: no untrusted role needs to call this RPC directly.
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.handle_new_user() FROM anon;
REVOKE ALL ON FUNCTION public.handle_new_user() FROM authenticated;

-- Premium code redemption stays callable only by signed-in users.
REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM anon;
GRANT EXECUTE ON FUNCTION public.redeem_premium_code(text) TO authenticated;

-- Event trigger helper: not part of the public API surface.
REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM anon;
REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM authenticated;

-- Trigger helper has no table references, but set search_path explicitly for linting.
ALTER FUNCTION public.set_updated_at() SET search_path = public;
