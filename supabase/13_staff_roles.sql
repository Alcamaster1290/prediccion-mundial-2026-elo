-- 13_staff_roles.sql
-- Staff authorization, admin/editor write policies, and profiles hardening.
-- Apply after 12_team_profiles.sql.

CREATE SCHEMA IF NOT EXISTS app_private;

CREATE TABLE IF NOT EXISTS app_private.staff_roles (
  user_id    uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role       text NOT NULL CHECK (role IN ('admin','editor')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS set_staff_roles_updated_at ON app_private.staff_roles;
CREATE TRIGGER set_staff_roles_updated_at
  BEFORE UPDATE ON app_private.staff_roles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE app_private.staff_roles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA app_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE app_private.staff_roles FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA app_private TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE app_private.staff_roles TO service_role;

CREATE OR REPLACE FUNCTION public.has_staff_role(required_role text DEFAULT 'editor')
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, app_private
AS $$
DECLARE
  current_role text;
BEGIN
  IF (select auth.uid()) IS NULL THEN
    RETURN false;
  END IF;

  SELECT sr.role INTO current_role
  FROM app_private.staff_roles sr
  WHERE sr.user_id = (select auth.uid());

  IF current_role = 'admin' THEN
    RETURN true;
  END IF;

  IF required_role = 'editor' AND current_role = 'editor' THEN
    RETURN true;
  END IF;

  RETURN false;
END;
$$;

REVOKE ALL ON FUNCTION public.has_staff_role(text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_staff_role(text) TO authenticated;

-- Harden profiles: users may update ordinary profile fields, not is_premium.
DROP POLICY IF EXISTS "profiles: self update" ON public.profiles;
DROP POLICY IF EXISTS "profiles: self update safe fields" ON public.profiles;

REVOKE UPDATE ON TABLE public.profiles FROM anon, authenticated;
GRANT UPDATE (email, full_name, updated_at) ON TABLE public.profiles TO authenticated;

CREATE POLICY "profiles: self update safe fields"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = id)
  WITH CHECK ((select auth.uid()) = id);

-- Staff write policies for public tournament data.
DROP POLICY IF EXISTS "groups: admin write" ON public.groups;
CREATE POLICY "groups: admin write"
  ON public.groups FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "teams: admin write" ON public.teams;
CREATE POLICY "teams: admin write"
  ON public.teams FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "group memberships: admin write" ON public.group_memberships;
CREATE POLICY "group memberships: admin write"
  ON public.group_memberships FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "match results: staff insert" ON public.match_results;
CREATE POLICY "match results: staff insert"
  ON public.match_results FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('editor')));

DROP POLICY IF EXISTS "match results: staff update" ON public.match_results;
CREATE POLICY "match results: staff update"
  ON public.match_results FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('editor')))
  WITH CHECK ((select public.has_staff_role('editor')));

DROP POLICY IF EXISTS "team profiles: admin write" ON public.team_profiles;
CREATE POLICY "team profiles: admin write"
  ON public.team_profiles FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "team profile premium: admin write" ON public.team_profile_premium;
CREATE POLICY "team profile premium: admin write"
  ON public.team_profile_premium FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "knockout slot rules: admin write" ON public.knockout_slot_rules;
CREATE POLICY "knockout slot rules: admin write"
  ON public.knockout_slot_rules FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "best third pairing rules: admin write" ON public.best_third_pairing_rules;
CREATE POLICY "best third pairing rules: admin write"
  ON public.best_third_pairing_rules FOR ALL
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium codes: admin read" ON public.premium_codes;
CREATE POLICY "premium codes: admin read"
  ON public.premium_codes FOR SELECT
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium codes: admin insert" ON public.premium_codes;
CREATE POLICY "premium codes: admin insert"
  ON public.premium_codes FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium codes: admin update" ON public.premium_codes;
CREATE POLICY "premium codes: admin update"
  ON public.premium_codes FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));

GRANT INSERT, UPDATE, DELETE ON TABLE
  public.groups,
  public.teams,
  public.group_memberships,
  public.match_results,
  public.team_profiles,
  public.team_profile_premium,
  public.knockout_slot_rules,
  public.best_third_pairing_rules
TO authenticated;

GRANT SELECT, INSERT, UPDATE ON TABLE public.premium_codes TO authenticated;
