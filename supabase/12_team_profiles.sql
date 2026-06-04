-- 12_team_profiles.sql
-- Public and premium team profile metadata.
-- Apply after 09_tournament_core.sql.

CREATE UNIQUE INDEX IF NOT EXISTS idx_players_team_name_club_version
  ON public.players(team_code, name, club, version);

CREATE TABLE IF NOT EXISTS public.team_profiles (
  team_code      text PRIMARY KEY REFERENCES public.teams(team_code) ON DELETE CASCADE,
  summary        text,
  tactical_style text,
  strengths      text[] NOT NULL DEFAULT '{}'::text[],
  weaknesses     text[] NOT NULL DEFAULT '{}'::text[],
  version        text NOT NULL DEFAULT '1.0',
  published      boolean NOT NULL DEFAULT false,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.team_profile_premium (
  team_code     text PRIMARY KEY REFERENCES public.teams(team_code) ON DELETE CASCADE,
  key_players   jsonb NOT NULL DEFAULT '[]'::jsonb,
  premium_notes text,
  version       text NOT NULL DEFAULT '1.0',
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS set_team_profiles_updated_at ON public.team_profiles;
CREATE TRIGGER set_team_profiles_updated_at
  BEFORE UPDATE ON public.team_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_team_profile_premium_updated_at ON public.team_profile_premium;
CREATE TRIGGER set_team_profile_premium_updated_at
  BEFORE UPDATE ON public.team_profile_premium
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.team_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_profile_premium ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "team profiles: public read published" ON public.team_profiles;
CREATE POLICY "team profiles: public read published"
  ON public.team_profiles FOR SELECT
  TO anon, authenticated
  USING (published = true);

DROP POLICY IF EXISTS "team profile premium: premium read" ON public.team_profile_premium;
CREATE POLICY "team profile premium: premium read"
  ON public.team_profile_premium FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.profiles p
      WHERE p.id = (select auth.uid())
        AND p.is_premium = true
    )
  );

CREATE OR REPLACE VIEW public.v_public_team_profiles
WITH (security_invoker = true)
AS
SELECT
  tp.team_code,
  t.name,
  t.group_id,
  t.flag_url,
  tp.summary,
  tp.tactical_style,
  tp.strengths,
  tp.weaknesses,
  tp.version,
  tp.updated_at
FROM public.team_profiles tp
JOIN public.teams t ON t.team_code = tp.team_code
WHERE tp.published = true;

CREATE OR REPLACE FUNCTION public.get_team_profile(input_team_code text)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
  SELECT jsonb_strip_nulls(
    jsonb_build_object(
      'team_code', tp.team_code,
      'name', t.name,
      'group_id', t.group_id,
      'flag_url', t.flag_url,
      'summary', tp.summary,
      'tactical_style', tp.tactical_style,
      'strengths', tp.strengths,
      'weaknesses', tp.weaknesses,
      'version', tp.version,
      'key_players', tpp.key_players,
      'premium_notes', tpp.premium_notes
    )
  )
  FROM public.team_profiles tp
  JOIN public.teams t ON t.team_code = tp.team_code
  LEFT JOIN public.team_profile_premium tpp ON tpp.team_code = tp.team_code
  WHERE tp.team_code = lower(input_team_code)
    AND tp.published = true
  LIMIT 1;
$$;

GRANT SELECT ON TABLE public.team_profiles TO anon, authenticated;
GRANT SELECT ON TABLE public.team_profile_premium TO authenticated;
GRANT SELECT ON TABLE public.v_public_team_profiles TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.team_profiles,
  public.team_profile_premium
TO service_role;
GRANT EXECUTE ON FUNCTION public.get_team_profile(text) TO anon, authenticated;
