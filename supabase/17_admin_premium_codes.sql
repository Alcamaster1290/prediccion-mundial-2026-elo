-- 17_admin_premium_codes.sql
-- Internal admin RPCs for creating and listing premium activation codes.
-- Apply after 16_advisor_hardening.sql.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

DROP POLICY IF EXISTS "premium codes: admin read" ON public.premium_codes;
DROP POLICY IF EXISTS "premium codes: admin insert" ON public.premium_codes;
DROP POLICY IF EXISTS "premium codes: admin update" ON public.premium_codes;

REVOKE ALL ON TABLE public.premium_codes FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.premium_codes TO service_role;

CREATE OR REPLACE FUNCTION public.admin_create_premium_code(input_notes text DEFAULT NULL)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor uuid := (select auth.uid());
  v_code text;
  v_code_id uuid;
  v_created_at timestamptz;
  v_hash text;
  v_notes text := nullif(trim(coalesce(input_notes, '')), '');
  v_raw text;
  attempt integer;
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
    VALUES (NULL, 'admin_create_premium_code_denied', actor, '{}'::jsonb);

    RETURN jsonb_build_object('success', false, 'message', 'No autorizado.');
  END IF;

  IF v_notes IS NOT NULL AND length(v_notes) > 500 THEN
    RETURN jsonb_build_object('success', false, 'message', 'Notas demasiado largas.');
  END IF;

  FOR attempt IN 1..5 LOOP
    v_raw := upper(encode(extensions.gen_random_bytes(9), 'hex'));
    v_code := substr(v_raw, 1, 4) || '-' || substr(v_raw, 5, 4) || '-' || substr(v_raw, 9, 4);
    v_hash := encode(extensions.digest(trim(v_code), 'sha256'), 'hex');

    BEGIN
      INSERT INTO public.premium_codes (code_hash, notes)
      VALUES (v_hash, v_notes)
      RETURNING id, created_at INTO v_code_id, v_created_at;
      EXIT;
    EXCEPTION WHEN unique_violation THEN
      v_code_id := NULL;
    END;
  END LOOP;

  IF v_code_id IS NULL THEN
    INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
    VALUES (NULL, 'admin_create_premium_code_failed', actor, jsonb_build_object('reason', 'code_collision'));

    RETURN jsonb_build_object('success', false, 'message', 'No se pudo generar un codigo unico.');
  END IF;

  INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
  VALUES (
    NULL,
    'admin_create_premium_code',
    actor,
    jsonb_build_object('premium_code_id', v_code_id, 'notes', v_notes)
  );

  RETURN jsonb_build_object(
    'success', true,
    'message', 'Codigo generado.',
    'code', v_code,
    'code_id', v_code_id,
    'created_at', v_created_at,
    'notes', v_notes
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.admin_list_premium_codes()
RETURNS TABLE (
  id uuid,
  is_used boolean,
  used_by uuid,
  used_by_email text,
  used_by_name text,
  used_at timestamptz,
  created_at timestamptz,
  notes text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor uuid := (select auth.uid());
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    RETURN;
  END IF;

  RETURN QUERY
  SELECT
    pc.id,
    pc.is_used,
    pc.used_by,
    COALESCE(p.email, au.email) AS used_by_email,
    NULLIF(p.full_name, '') AS used_by_name,
    pc.used_at,
    pc.created_at,
    pc.notes
  FROM public.premium_codes pc
  LEFT JOIN auth.users au ON au.id = pc.used_by
  LEFT JOIN public.profiles p ON p.id = pc.used_by
  ORDER BY pc.created_at DESC
  LIMIT 100;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_create_premium_code(text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.admin_list_premium_codes() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.admin_create_premium_code(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_list_premium_codes() TO authenticated;
