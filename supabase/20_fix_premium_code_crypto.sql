-- 20_fix_premium_code_crypto.sql
-- Qualify pgcrypto calls in SECURITY DEFINER RPCs and remove one dev fixture.
-- Apply after 19_fix_staff_role_lookup.sql.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

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

DROP FUNCTION IF EXISTS public.admin_list_premium_codes();

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

CREATE OR REPLACE FUNCTION public.redeem_premium_code(input_code text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_code_hash text;
  v_code_id uuid;
  v_user_id uuid;
BEGIN
  v_user_id := (select auth.uid());
  IF v_user_id IS NULL THEN
    RETURN json_build_object('success', false, 'message', 'Debes iniciar sesion primero.');
  END IF;

  IF EXISTS (SELECT 1 FROM public.profiles WHERE id = v_user_id AND is_premium = true) THEN
    RETURN json_build_object('success', false, 'message', 'Tu cuenta ya tiene acceso activo.');
  END IF;

  v_code_hash := encode(extensions.digest(trim(input_code), 'sha256'), 'hex');

  SELECT id INTO v_code_id
  FROM public.premium_codes
  WHERE code_hash = v_code_hash
    AND is_used = false
  LIMIT 1;

  IF v_code_id IS NULL THEN
    INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
    VALUES (v_user_id, 'redeem_code_failed', v_user_id, jsonb_build_object('reason', 'invalid_or_used'));
    RETURN json_build_object('success', false, 'message', 'Codigo invalido o ya utilizado. Verifica el email que recibiste.');
  END IF;

  UPDATE public.premium_codes
  SET is_used = true,
      used_by = v_user_id,
      used_at = now()
  WHERE id = v_code_id;

  INSERT INTO public.premium_grants (user_id, source, granted_by, notes)
  VALUES (v_user_id, 'code', v_user_id, 'Redeemed access code');

  UPDATE public.profiles
  SET is_premium = true,
      updated_at = now()
  WHERE id = v_user_id;

  INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
  VALUES (v_user_id, 'redeem_code_success', v_user_id, jsonb_build_object('premium_code_id', v_code_id));

  RETURN json_build_object('success', true, 'message', 'Acceso activado. Ya puedes ver todos los pronosticos.');
END;
$$;

DELETE FROM public.premium_audit_log
WHERE metadata->>'premium_code_id' = '01e3ee6d-6f96-4e44-8737-470a64c2f113';

DELETE FROM public.premium_codes
WHERE id = '01e3ee6d-6f96-4e44-8737-470a64c2f113'
  AND used_by = 'ddfff230-a424-45d2-b474-e0411f7f2404'
  AND notes ILIKE '%desarrollo local%';

REVOKE ALL ON FUNCTION public.admin_create_premium_code(text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.admin_list_premium_codes() FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.admin_create_premium_code(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.admin_list_premium_codes() TO authenticated;
GRANT EXECUTE ON FUNCTION public.redeem_premium_code(text) TO authenticated;
