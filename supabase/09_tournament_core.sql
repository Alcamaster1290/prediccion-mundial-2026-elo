-- 09_tournament_core.sql
-- Canonical public tournament data and live match results.
-- Apply after 08_security_advisors_hardening.sql.

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.groups (
  group_id    text PRIMARY KEY CHECK (group_id ~ '^[A-L]$'),
  name        text NOT NULL,
  draw_order  integer NOT NULL UNIQUE CHECK (draw_order BETWEEN 1 AND 12),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.teams (
  team_code      text PRIMARY KEY CHECK (team_code ~ '^[a-z0-9]{3}$'),
  name           text NOT NULL,
  fifa_code      text,
  group_id       text REFERENCES public.groups(group_id) ON UPDATE CASCADE,
  flag_url       text,
  confederation  text,
  coach          text,
  profile_status text NOT NULL DEFAULT 'seeded'
    CHECK (profile_status IN ('seeded','partial','complete')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.group_memberships (
  group_id       text NOT NULL REFERENCES public.groups(group_id) ON DELETE CASCADE,
  team_code      text NOT NULL REFERENCES public.teams(team_code) ON DELETE CASCADE,
  draw_position  integer NOT NULL CHECK (draw_position BETWEEN 1 AND 4),
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (group_id, team_code),
  UNIQUE (group_id, draw_position),
  UNIQUE (team_code)
);

CREATE TABLE IF NOT EXISTS public.match_results (
  match_number   integer PRIMARY KEY,
  phase          text NOT NULL CHECK (phase IN ('group','r32','r16','qf','sf','tp','final')),
  group_id       text REFERENCES public.groups(group_id) ON UPDATE CASCADE,
  home_team      text REFERENCES public.teams(team_code) ON UPDATE CASCADE,
  away_team      text REFERENCES public.teams(team_code) ON UPDATE CASCADE,
  home_label     text,
  away_label     text,
  kickoff_utc    timestamptz NOT NULL,
  stadium        text,
  city           text,
  status         text NOT NULL DEFAULT 'scheduled'
    CHECK (status IN ('scheduled','live','finished','postponed','cancelled')),
  home_goals     integer CHECK (home_goals IS NULL OR home_goals >= 0),
  away_goals     integer CHECK (away_goals IS NULL OR away_goals >= 0),
  home_penalties integer CHECK (home_penalties IS NULL OR home_penalties >= 0),
  away_penalties integer CHECK (away_penalties IS NULL OR away_penalties >= 0),
  winner_team    text REFERENCES public.teams(team_code) ON UPDATE CASCADE,
  updated_by     uuid REFERENCES auth.users(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT group_matches_have_group CHECK (phase <> 'group' OR group_id IS NOT NULL),
  CONSTRAINT finished_scores_complete CHECK (
    status <> 'finished'
    OR (home_goals IS NOT NULL AND away_goals IS NOT NULL)
  )
);

ALTER TABLE public.match_results
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'scheduled',
  ADD COLUMN IF NOT EXISTS home_penalties integer,
  ADD COLUMN IF NOT EXISTS away_penalties integer,
  ADD COLUMN IF NOT EXISTS winner_team text,
  ADD COLUMN IF NOT EXISTS updated_by uuid REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'match_results_status_check'
      AND conrelid = 'public.match_results'::regclass
  ) THEN
    ALTER TABLE public.match_results
      ADD CONSTRAINT match_results_status_check
      CHECK (status IN ('scheduled','live','finished','postponed','cancelled'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_teams_group_id ON public.teams(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_team ON public.group_memberships(team_code);
CREATE INDEX IF NOT EXISTS idx_match_results_phase ON public.match_results(phase);
CREATE INDEX IF NOT EXISTS idx_match_results_group ON public.match_results(group_id) WHERE phase = 'group';
CREATE INDEX IF NOT EXISTS idx_match_results_kickoff ON public.match_results(kickoff_utc);

DROP TRIGGER IF EXISTS set_groups_updated_at ON public.groups;
CREATE TRIGGER set_groups_updated_at
  BEFORE UPDATE ON public.groups
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_teams_updated_at ON public.teams;
CREATE TRIGGER set_teams_updated_at
  BEFORE UPDATE ON public.teams
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_match_results_updated_at ON public.match_results;
CREATE TRIGGER set_match_results_updated_at
  BEFORE UPDATE ON public.match_results
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.group_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.match_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "groups: public read" ON public.groups;
CREATE POLICY "groups: public read"
  ON public.groups FOR SELECT
  TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS "teams: public read" ON public.teams;
CREATE POLICY "teams: public read"
  ON public.teams FOR SELECT
  TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS "group memberships: public read" ON public.group_memberships;
CREATE POLICY "group memberships: public read"
  ON public.group_memberships FOR SELECT
  TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS "match results: public read" ON public.match_results;
CREATE POLICY "match results: public read"
  ON public.match_results FOR SELECT
  TO anon, authenticated
  USING (true);

GRANT SELECT ON TABLE
  public.groups,
  public.teams,
  public.group_memberships,
  public.match_results
TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.groups,
  public.teams,
  public.group_memberships,
  public.match_results
TO service_role;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime')
     AND NOT EXISTS (
       SELECT 1
       FROM pg_publication_tables
       WHERE pubname = 'supabase_realtime'
         AND schemaname = 'public'
         AND tablename = 'match_results'
     ) THEN
    EXECUTE 'ALTER PUBLICATION supabase_realtime ADD TABLE public.match_results';
  END IF;
END $$;
