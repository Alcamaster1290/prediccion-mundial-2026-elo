-- 15_premium_ops.sql
-- Premium grants, audit log, and admin RPCs.
-- Apply after 13_staff_roles.sql.

CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_match_id_unique
  ON public.predictions(match_id)
  WHERE match_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.premium_grants (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  source      text NOT NULL DEFAULT 'manual' CHECK (source IN ('code','manual','payment','promo')),
  granted_by  uuid REFERENCES auth.users(id),
  starts_at   timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz,
  revoked_at  timestamptz,
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.premium_audit_log (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  action     text NOT NULL,
  actor_id   uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_premium_grants_user_active
  ON public.premium_grants(user_id, revoked_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_premium_audit_log_user_created
  ON public.premium_audit_log(user_id, created_at DESC);

DROP TRIGGER IF EXISTS set_premium_grants_updated_at ON public.premium_grants;
CREATE TRIGGER set_premium_grants_updated_at
  BEFORE UPDATE ON public.premium_grants
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.premium_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.premium_audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "premium grants: self read" ON public.premium_grants;
CREATE POLICY "premium grants: self read"
  ON public.premium_grants FOR SELECT
  TO authenticated
  USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS "premium grants: admin all" ON public.premium_grants;
CREATE POLICY "premium grants: admin all"
  ON public.premium_grants FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium audit: admin read" ON public.premium_audit_log;
CREATE POLICY "premium audit: admin read"
  ON public.premium_audit_log FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium audit: admin insert" ON public.premium_audit_log;
CREATE POLICY "premium audit: admin insert"
  ON public.premium_audit_log FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('admin')));

CREATE OR REPLACE FUNCTION public.grant_premium(
  target_user_id uuid,
  grant_expires_at timestamptz DEFAULT NULL,
  grant_notes text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  actor uuid := (select auth.uid());
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    RETURN jsonb_build_object('success', false, 'message', 'No autorizado.');
  END IF;

  INSERT INTO public.premium_grants (user_id, source, granted_by, expires_at, notes)
  VALUES (target_user_id, 'manual', actor, grant_expires_at, grant_notes);

  UPDATE public.profiles
  SET is_premium = true,
      updated_at = now()
  WHERE id = target_user_id;

  INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
  VALUES (
    target_user_id,
    'grant_premium',
    actor,
    jsonb_build_object('expires_at', grant_expires_at, 'notes', grant_notes)
  );

  RETURN jsonb_build_object('success', true, 'message', 'Acceso premium activado.');
END;
$$;

CREATE OR REPLACE FUNCTION public.revoke_premium(
  target_user_id uuid,
  revoke_reason text DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  actor uuid := (select auth.uid());
BEGIN
  IF actor IS NULL OR NOT public.has_staff_role('admin') THEN
    RETURN jsonb_build_object('success', false, 'message', 'No autorizado.');
  END IF;

  UPDATE public.premium_grants
  SET revoked_at = now(),
      updated_at = now()
  WHERE user_id = target_user_id
    AND revoked_at IS NULL;

  UPDATE public.profiles
  SET is_premium = false,
      updated_at = now()
  WHERE id = target_user_id;

  INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
  VALUES (
    target_user_id,
    'revoke_premium',
    actor,
    jsonb_build_object('reason', revoke_reason)
  );

  RETURN jsonb_build_object('success', true, 'message', 'Acceso premium revocado.');
END;
$$;

CREATE OR REPLACE FUNCTION public.redeem_premium_code(input_code text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_code_hash text;
  v_code_id uuid;
  v_user_id uuid;
BEGIN
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RETURN json_build_object('success', false, 'message', 'Debes iniciar sesion primero.');
  END IF;

  IF EXISTS (SELECT 1 FROM public.profiles WHERE id = v_user_id AND is_premium = true) THEN
    RETURN json_build_object('success', false, 'message', 'Tu cuenta ya tiene acceso premium activo.');
  END IF;

  v_code_hash := encode(digest(trim(input_code), 'sha256'), 'hex');

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
  VALUES (v_user_id, 'code', v_user_id, 'Redeemed premium code');

  UPDATE public.profiles
  SET is_premium = true,
      updated_at = now()
  WHERE id = v_user_id;

  INSERT INTO public.premium_audit_log (user_id, action, actor_id, metadata)
  VALUES (v_user_id, 'redeem_code_success', v_user_id, jsonb_build_object('premium_code_id', v_code_id));

  RETURN json_build_object('success', true, 'message', 'Acceso premium activado. Ya puedes ver todos los pronosticos.');
END;
$$;

REVOKE ALL ON FUNCTION public.grant_premium(uuid, timestamptz, text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.revoke_premium(uuid, text) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.redeem_premium_code(text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.grant_premium(uuid, timestamptz, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.revoke_premium(uuid, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.redeem_premium_code(text) TO authenticated;

GRANT SELECT ON TABLE public.premium_grants TO authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.premium_grants TO authenticated;
GRANT SELECT, INSERT ON TABLE public.premium_audit_log TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.premium_grants,
  public.premium_audit_log
TO service_role;
