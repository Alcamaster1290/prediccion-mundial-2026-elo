-- 30_resolve_knockout_best_thirds.sql
-- Resolve manual best-third labels and previous-match winners/losers in
-- public.resolve_knockout_bracket().
-- Apply after 10_standings_views.sql and 11_knockout_rules.sql.

WITH current_best_third_slots(match_number, side, source_group) AS (
  VALUES
    (74, 'away', 'D'),
    (77, 'away', 'F'),
    (79, 'away', 'E'),
    (80, 'away', 'K'),
    (81, 'away', 'B'),
    (82, 'away', 'I'),
    (85, 'away', 'J'),
    (87, 'away', 'L')
)
UPDATE public.knockout_slot_rules ksr
SET source_type = 'best_third',
    source_group = current_best_third_slots.source_group,
    source_rank = 3,
    source_match_number = NULL,
    source_winner = true,
    label = 'Mejor 3. Grupo ' || current_best_third_slots.source_group
FROM current_best_third_slots
WHERE ksr.match_number = current_best_third_slots.match_number
  AND ksr.side = current_best_third_slots.side;

CREATE OR REPLACE FUNCTION public.resolve_knockout_slot_team(
  p_match_number integer,
  p_side text
)
RETURNS text
LANGUAGE plpgsql
STABLE
SET search_path = public
AS $$
DECLARE
  slot_rule public.knockout_slot_rules%ROWTYPE;
  resolved_team text;
  source_home text;
  source_away text;
  source_winner text;
BEGIN
  SELECT *
    INTO slot_rule
  FROM public.knockout_slot_rules
  WHERE match_number = p_match_number
    AND side = p_side;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  IF slot_rule.source_type = 'group_rank' THEN
    SELECT vgs.team_code
      INTO resolved_team
    FROM public.v_group_standings vgs
    WHERE vgs.group_id = slot_rule.source_group
      AND vgs.group_rank = slot_rule.source_rank
    LIMIT 1;
    RETURN resolved_team;
  END IF;

  IF slot_rule.source_type = 'best_third' THEN
    SELECT vbt.team_code
      INTO resolved_team
    FROM public.v_best_thirds vbt
    WHERE vbt.group_id = slot_rule.source_group
      AND vbt.classified = true
    LIMIT 1;
    RETURN resolved_team;
  END IF;

  IF slot_rule.source_type = 'manual_label'
     AND regexp_match(replace(coalesce(slot_rule.label, ''), 'Grupo ', ''), '^3[^A-L]*([A-L](?:/[A-L])*)$') IS NOT NULL
  THEN
    WITH RECURSIVE parsed_manual_slots AS (
      SELECT
        ksr.match_number,
        ksr.side,
        regexp_match(
          replace(coalesce(ksr.label, ''), 'Grupo ', ''),
          '^3[^A-L]*([A-L](?:/[A-L])*)$'
        ) AS parsed
      FROM public.knockout_slot_rules ksr
      WHERE ksr.source_type = 'manual_label'
    ),
    best_third_slots AS (
      SELECT
        row_number() OVER (ORDER BY match_number, side)::integer AS slot_index,
        match_number,
        side,
        match_number::text || ':' || side AS slot_key,
        string_to_array(parsed[1], '/') AS candidate_groups
      FROM parsed_manual_slots
      WHERE parsed IS NOT NULL
    ),
    best_third_candidates AS (
      SELECT
        s.slot_index,
        s.slot_key,
        vbt.group_id,
        vbt.team_code,
        vbt.third_rank,
        vbt.classified,
        (CASE WHEN vbt.classified THEN 10000 ELSE 0 END) + (100 - vbt.third_rank) AS score
      FROM best_third_slots s
      JOIN public.v_best_thirds vbt
        ON vbt.group_id = ANY (s.candidate_groups)
    ),
    assignment_paths AS (
      SELECT
        0::integer AS slot_index,
        ARRAY[]::text[] AS used_groups,
        0::integer AS score,
        '{}'::jsonb AS assignments
      UNION ALL
      SELECT
        ap.slot_index + 1,
        ap.used_groups || c.group_id,
        ap.score + c.score,
        ap.assignments || jsonb_build_object(
          c.slot_key,
          jsonb_build_object('group_id', c.group_id, 'team_code', c.team_code)
        )
      FROM assignment_paths ap
      JOIN best_third_candidates c
        ON c.slot_index = ap.slot_index + 1
      WHERE NOT c.group_id = ANY (ap.used_groups)
    ),
    best_assignment AS (
      SELECT assignments
      FROM assignment_paths
      WHERE slot_index = (SELECT count(*) FROM best_third_slots)
      ORDER BY score DESC
      LIMIT 1
    )
    SELECT ba.assignments -> (slot_rule.match_number::text || ':' || slot_rule.side) ->> 'team_code'
      INTO resolved_team
    FROM best_assignment ba;

    RETURN resolved_team;
  END IF;

  IF slot_rule.source_type = 'match_winner' THEN
    RETURN public.resolve_knockout_match_winner(slot_rule.source_match_number);
  END IF;

  IF slot_rule.source_type = 'match_loser' THEN
    source_winner := public.resolve_knockout_match_winner(slot_rule.source_match_number);
    IF source_winner IS NULL THEN
      RETURN NULL;
    END IF;

    SELECT mr.home_team, mr.away_team
      INTO source_home, source_away
    FROM public.match_results mr
    WHERE mr.match_number = slot_rule.source_match_number;

    source_home := coalesce(source_home, public.resolve_knockout_slot_team(slot_rule.source_match_number, 'home'));
    source_away := coalesce(source_away, public.resolve_knockout_slot_team(slot_rule.source_match_number, 'away'));

    IF source_winner = source_home THEN
      RETURN source_away;
    END IF;
    IF source_winner = source_away THEN
      RETURN source_home;
    END IF;
    RETURN NULL;
  END IF;

  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.resolve_knockout_match_winner(
  p_match_number integer
)
RETURNS text
LANGUAGE plpgsql
STABLE
SET search_path = public
AS $$
DECLARE
  source_match public.match_results%ROWTYPE;
  source_home text;
  source_away text;
BEGIN
  SELECT *
    INTO source_match
  FROM public.match_results
  WHERE match_number = p_match_number;

  IF NOT FOUND OR source_match.status <> 'finished' THEN
    RETURN NULL;
  END IF;

  IF source_match.winner_team IS NOT NULL THEN
    RETURN source_match.winner_team;
  END IF;

  source_home := coalesce(source_match.home_team, public.resolve_knockout_slot_team(p_match_number, 'home'));
  source_away := coalesce(source_match.away_team, public.resolve_knockout_slot_team(p_match_number, 'away'));

  IF source_match.home_goals > source_match.away_goals THEN
    RETURN source_home;
  END IF;
  IF source_match.away_goals > source_match.home_goals THEN
    RETURN source_away;
  END IF;
  IF source_match.home_penalties > source_match.away_penalties THEN
    RETURN source_home;
  END IF;
  IF source_match.away_penalties > source_match.home_penalties THEN
    RETURN source_away;
  END IF;

  RETURN NULL;
END;
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
SET search_path = public
AS $$
  SELECT
    mr.match_number,
    mr.phase,
    mr.kickoff_utc,
    mr.stadium,
    mr.city,
    public.resolve_knockout_slot_team(mr.match_number, 'home') AS home_team,
    public.resolve_knockout_slot_team(mr.match_number, 'away') AS away_team,
    coalesce(ksr_home.label, mr.home_label) AS home_label,
    coalesce(ksr_away.label, mr.away_label) AS away_label
  FROM public.match_results mr
  LEFT JOIN public.knockout_slot_rules ksr_home
    ON ksr_home.match_number = mr.match_number
   AND ksr_home.side = 'home'
  LEFT JOIN public.knockout_slot_rules ksr_away
    ON ksr_away.match_number = mr.match_number
   AND ksr_away.side = 'away'
  WHERE mr.phase <> 'group'
  ORDER BY mr.match_number;
$$;

GRANT EXECUTE ON FUNCTION public.resolve_knockout_slot_team(integer, text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_knockout_match_winner(integer) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.resolve_knockout_bracket() TO anon, authenticated;
