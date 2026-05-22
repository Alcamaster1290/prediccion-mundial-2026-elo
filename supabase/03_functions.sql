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
