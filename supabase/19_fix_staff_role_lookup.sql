-- 19_fix_staff_role_lookup.sql
-- Fix staff role lookup by avoiding the reserved SQL current_role identifier.
-- Apply after 13_staff_roles.sql.

CREATE OR REPLACE FUNCTION public.has_staff_role(required_role text DEFAULT 'editor')
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, app_private
AS $$
DECLARE
  actor uuid := (select auth.uid());
  staff_role text;
BEGIN
  IF actor IS NULL THEN
    RETURN false;
  END IF;

  SELECT sr.role INTO staff_role
  FROM app_private.staff_roles sr
  WHERE sr.user_id = actor;

  IF staff_role = 'admin' THEN
    RETURN true;
  END IF;

  IF required_role = 'editor' AND staff_role = 'editor' THEN
    RETURN true;
  END IF;

  RETURN false;
END;
$$;

REVOKE ALL ON FUNCTION public.has_staff_role(text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_staff_role(text) TO authenticated;
