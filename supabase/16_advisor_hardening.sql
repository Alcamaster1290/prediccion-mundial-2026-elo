-- 16_advisor_hardening.sql
-- Follow-up hardening for Supabase security/performance advisors.
-- Apply after 15_premium_ops.sql.

ALTER FUNCTION public.set_updated_at() SET search_path = public, pg_temp;
ALTER FUNCTION public.get_group_standings() SET search_path = public, pg_temp;
ALTER FUNCTION public.get_best_thirds() SET search_path = public, pg_temp;
ALTER FUNCTION public.get_live_results() SET search_path = public, pg_temp;
ALTER FUNCTION public.resolve_group_qualifiers() SET search_path = public, pg_temp;
ALTER FUNCTION public.resolve_best_third_rule() SET search_path = public, pg_temp;
ALTER FUNCTION public.resolve_knockout_bracket() SET search_path = public, pg_temp;
ALTER FUNCTION public.get_team_profile(text) SET search_path = public, pg_temp;
ALTER FUNCTION public.get_active_simulation_snapshot() SET search_path = public, pg_temp;

ALTER TABLE public.simulation_runs
  ALTER COLUMN scenario_name SET DEFAULT 'baseline';

CREATE INDEX IF NOT EXISTS idx_knockout_slot_rules_source_group
  ON public.knockout_slot_rules(source_group)
  WHERE source_group IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knockout_slot_rules_source_match_number
  ON public.knockout_slot_rules(source_match_number)
  WHERE source_match_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_match_results_updated_by
  ON public.match_results(updated_by)
  WHERE updated_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_premium_codes_used_by
  ON public.premium_codes(used_by)
  WHERE used_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_premium_grants_granted_by
  ON public.premium_grants(granted_by)
  WHERE granted_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_premium_audit_log_actor_id
  ON public.premium_audit_log(actor_id)
  WHERE actor_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_simulation_group_standings_run
  ON public.simulation_group_standings(simulation_run);

CREATE INDEX IF NOT EXISTS idx_simulation_terceros_run
  ON public.simulation_terceros_table(simulation_run);

DROP POLICY IF EXISTS "staff roles: service role all" ON app_private.staff_roles;
CREATE POLICY "staff roles: service role all"
  ON app_private.staff_roles FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS "profiles: self read" ON public.profiles;
CREATE POLICY "profiles: self read"
  ON public.profiles FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = id);

DROP POLICY IF EXISTS "predictions: premium users read published" ON public.predictions;
CREATE POLICY "predictions: premium users read published"
  ON public.predictions FOR SELECT
  TO authenticated
  USING (
    published = true
    AND is_premium = true
    AND EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "premium read strengths" ON public.team_strength_snapshots;
CREATE POLICY "premium read strengths"
  ON public.team_strength_snapshots FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "premium read simulation runs" ON public.simulation_runs;
CREATE POLICY "premium read simulation runs"
  ON public.simulation_runs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "premium read simulation standings" ON public.simulation_group_standings;
CREATE POLICY "premium read simulation standings"
  ON public.simulation_group_standings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "premium read players" ON public.players;
CREATE POLICY "premium read players"
  ON public.players FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "premium read terceros" ON public.simulation_terceros_table;
CREATE POLICY "premium read terceros"
  ON public.simulation_terceros_table FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "public read" ON public.match_results;

DO $$
DECLARE
  item record;
BEGIN
  FOR item IN
    SELECT *
    FROM (VALUES
      ('public.groups'::regclass, 'groups: admin'),
      ('public.teams'::regclass, 'teams: admin'),
      ('public.group_memberships'::regclass, 'group memberships: admin'),
      ('public.knockout_slot_rules'::regclass, 'knockout slot rules: admin'),
      ('public.best_third_pairing_rules'::regclass, 'best third pairing rules: admin')
    ) AS v(target_table, policy_prefix)
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %s', item.policy_prefix || ' write', item.target_table);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %s', item.policy_prefix || ' insert', item.target_table);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %s', item.policy_prefix || ' update', item.target_table);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %s', item.policy_prefix || ' delete', item.target_table);

    EXECUTE format(
      'CREATE POLICY %I ON %s FOR INSERT TO authenticated WITH CHECK ((select public.has_staff_role(''admin'')))',
      item.policy_prefix || ' insert',
      item.target_table
    );
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR UPDATE TO authenticated USING ((select public.has_staff_role(''admin''))) WITH CHECK ((select public.has_staff_role(''admin'')))',
      item.policy_prefix || ' update',
      item.target_table
    );
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR DELETE TO authenticated USING ((select public.has_staff_role(''admin'')))',
      item.policy_prefix || ' delete',
      item.target_table
    );
  END LOOP;
END $$;

DROP POLICY IF EXISTS "team profiles: public read published" ON public.team_profiles;
DROP POLICY IF EXISTS "team profiles: authenticated read published or admin" ON public.team_profiles;
CREATE POLICY "team profiles: public read published"
  ON public.team_profiles FOR SELECT
  TO anon
  USING (published = true);
CREATE POLICY "team profiles: authenticated read published or admin"
  ON public.team_profiles FOR SELECT
  TO authenticated
  USING (published = true OR (select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "team profiles: admin write" ON public.team_profiles;
DROP POLICY IF EXISTS "team profiles: admin insert" ON public.team_profiles;
CREATE POLICY "team profiles: admin insert"
  ON public.team_profiles FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "team profiles: admin update" ON public.team_profiles;
CREATE POLICY "team profiles: admin update"
  ON public.team_profiles FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "team profiles: admin delete" ON public.team_profiles;
CREATE POLICY "team profiles: admin delete"
  ON public.team_profiles FOR DELETE
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "team profile premium: premium read" ON public.team_profile_premium;
DROP POLICY IF EXISTS "team profile premium: premium or admin read" ON public.team_profile_premium;
CREATE POLICY "team profile premium: premium or admin read"
  ON public.team_profile_premium FOR SELECT
  TO authenticated
  USING (
    (select public.has_staff_role('admin'))
    OR EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

DROP POLICY IF EXISTS "team profile premium: admin write" ON public.team_profile_premium;
DROP POLICY IF EXISTS "team profile premium: admin insert" ON public.team_profile_premium;
CREATE POLICY "team profile premium: admin insert"
  ON public.team_profile_premium FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "team profile premium: admin update" ON public.team_profile_premium;
CREATE POLICY "team profile premium: admin update"
  ON public.team_profile_premium FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "team profile premium: admin delete" ON public.team_profile_premium;
CREATE POLICY "team profile premium: admin delete"
  ON public.team_profile_premium FOR DELETE
  TO authenticated
  USING ((select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium grants: self read" ON public.premium_grants;
DROP POLICY IF EXISTS "premium grants: admin all" ON public.premium_grants;
DROP POLICY IF EXISTS "premium grants: self or admin read" ON public.premium_grants;
CREATE POLICY "premium grants: self or admin read"
  ON public.premium_grants FOR SELECT
  TO authenticated
  USING (user_id = (select auth.uid()) OR (select public.has_staff_role('admin')));

DROP POLICY IF EXISTS "premium grants: admin insert" ON public.premium_grants;
CREATE POLICY "premium grants: admin insert"
  ON public.premium_grants FOR INSERT
  TO authenticated
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "premium grants: admin update" ON public.premium_grants;
CREATE POLICY "premium grants: admin update"
  ON public.premium_grants FOR UPDATE
  TO authenticated
  USING ((select public.has_staff_role('admin')))
  WITH CHECK ((select public.has_staff_role('admin')));
DROP POLICY IF EXISTS "premium grants: admin delete" ON public.premium_grants;
CREATE POLICY "premium grants: admin delete"
  ON public.premium_grants FOR DELETE
  TO authenticated
  USING ((select public.has_staff_role('admin')));
