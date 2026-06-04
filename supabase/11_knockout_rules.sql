-- 11_knockout_rules.sql
-- Bracket slot rules and resolution helpers.
-- Apply after 10_standings_views.sql.

CREATE TABLE IF NOT EXISTS public.knockout_slot_rules (
  match_number        integer NOT NULL REFERENCES public.match_results(match_number) ON DELETE CASCADE,
  side                text NOT NULL CHECK (side IN ('home','away')),
  source_type         text NOT NULL CHECK (source_type IN ('group_rank','best_third','match_winner','match_loser','manual_label')),
  source_group        text REFERENCES public.groups(group_id) ON UPDATE CASCADE,
  source_rank         integer CHECK (source_rank BETWEEN 1 AND 4),
  source_match_number integer REFERENCES public.match_results(match_number) ON DELETE SET NULL,
  source_winner       boolean NOT NULL DEFAULT true,
  label               text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (match_number, side)
);

CREATE TABLE IF NOT EXISTS public.best_third_pairing_rules (
  rule_key          text PRIMARY KEY,
  qualified_groups text[] NOT NULL,
  slot_assignments jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS set_knockout_slot_rules_updated_at ON public.knockout_slot_rules;
CREATE TRIGGER set_knockout_slot_rules_updated_at
  BEFORE UPDATE ON public.knockout_slot_rules
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_best_third_pairing_rules_updated_at ON public.best_third_pairing_rules;
CREATE TRIGGER set_best_third_pairing_rules_updated_at
  BEFORE UPDATE ON public.best_third_pairing_rules
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.knockout_slot_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.best_third_pairing_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "knockout slot rules: public read" ON public.knockout_slot_rules;
CREATE POLICY "knockout slot rules: public read"
  ON public.knockout_slot_rules FOR SELECT
  TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS "best third pairing rules: public read" ON public.best_third_pairing_rules;
CREATE POLICY "best third pairing rules: public read"
  ON public.best_third_pairing_rules FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE OR REPLACE FUNCTION public.resolve_group_qualifiers()
RETURNS TABLE (
  group_id text,
  first_team text,
  second_team text,
  third_team text
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    group_id,
    max(team_code) FILTER (WHERE group_rank = 1) AS first_team,
    max(team_code) FILTER (WHERE group_rank = 2) AS second_team,
    max(team_code) FILTER (WHERE group_rank = 3) AS third_team
  FROM public.v_group_standings
  GROUP BY group_id
  ORDER BY group_id;
$$;

CREATE OR REPLACE FUNCTION public.resolve_best_third_rule()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
  WITH qualified AS (
    SELECT array_agg(group_id ORDER BY group_id) AS groups
    FROM public.v_best_thirds
    WHERE classified = true
  )
  SELECT jsonb_build_object(
    'qualified_groups', coalesce(to_jsonb(groups), '[]'::jsonb),
    'rule_key', array_to_string(groups, '')
  )
  FROM qualified;
$$;

CREATE OR REPLACE FUNCTION public.resolve_knockout_bracket()
RETURNS TABLE (
  match_number integer,
  phase text,
  kickoff_utc timestamptz,
  stadium text,
  city text,
  home_team text,
  away_team text,
  home_label text,
  away_label text
)
LANGUAGE sql
STABLE
AS $$
  WITH slot_resolution AS (
    SELECT
      ksr.match_number,
      ksr.side,
      CASE
        WHEN ksr.source_type = 'group_rank' THEN (
          SELECT vgs.team_code
          FROM public.v_group_standings vgs
          WHERE vgs.group_id = ksr.source_group
            AND vgs.group_rank = ksr.source_rank
          LIMIT 1
        )
        WHEN ksr.source_type = 'best_third' THEN (
          SELECT vbt.team_code
          FROM public.v_best_thirds vbt
          WHERE vbt.group_id = ksr.source_group
            AND vbt.classified = true
          LIMIT 1
        )
        ELSE NULL
      END AS team_code,
      ksr.label
    FROM public.knockout_slot_rules ksr
  )
  SELECT
    mr.match_number,
    mr.phase,
    mr.kickoff_utc,
    mr.stadium,
    mr.city,
    max(sr.team_code) FILTER (WHERE sr.side = 'home') AS home_team,
    max(sr.team_code) FILTER (WHERE sr.side = 'away') AS away_team,
    coalesce(max(sr.label) FILTER (WHERE sr.side = 'home'), mr.home_label) AS home_label,
    coalesce(max(sr.label) FILTER (WHERE sr.side = 'away'), mr.away_label) AS away_label
  FROM public.match_results mr
  LEFT JOIN slot_resolution sr ON sr.match_number = mr.match_number
  WHERE mr.phase <> 'group'
  GROUP BY mr.match_number, mr.phase, mr.kickoff_utc, mr.stadium, mr.city, mr.home_label, mr.away_label
  ORDER BY mr.match_number;
$$;

GRANT SELECT ON TABLE
  public.knockout_slot_rules,
  public.best_third_pairing_rules
TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.knockout_slot_rules,
  public.best_third_pairing_rules
TO service_role;

GRANT EXECUTE ON FUNCTION public.resolve_group_qualifiers() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_best_third_rule() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_knockout_bracket() TO anon, authenticated;
