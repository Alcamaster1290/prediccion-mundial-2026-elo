-- 08_security_advisors_hardening.sql
-- Fixes security advisor warnings without changing function bodies.
-- Apply AFTER 03_functions.sql. Optional later functions are handled
-- conditionally so this file can be applied before the full app migrations.

DO $$
BEGIN
  -- Trigger helper: no untrusted role needs to call this RPC directly.
  IF to_regprocedure('public.handle_new_user()') IS NOT NULL THEN
    REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
    REVOKE ALL ON FUNCTION public.handle_new_user() FROM anon;
    REVOKE ALL ON FUNCTION public.handle_new_user() FROM authenticated;
  END IF;

  -- Premium code redemption stays callable only by signed-in users.
  IF to_regprocedure('public.redeem_premium_code(text)') IS NOT NULL THEN
    REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM PUBLIC;
    REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM anon;
    GRANT EXECUTE ON FUNCTION public.redeem_premium_code(text) TO authenticated;
  END IF;

  -- Optional event trigger helper: not part of the public API surface.
  IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL THEN
    REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC;
    REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM anon;
    REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM authenticated;
  END IF;

  -- Optional trigger helper created by later tournament-core migrations.
  IF to_regprocedure('public.set_updated_at()') IS NOT NULL THEN
    ALTER FUNCTION public.set_updated_at() SET search_path = public, pg_temp;
  END IF;
END $$;
