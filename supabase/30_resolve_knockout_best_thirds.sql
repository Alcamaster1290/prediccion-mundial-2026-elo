-- 30_resolve_knockout_best_thirds.sql
-- Resolve manual best-third labels in public.resolve_knockout_bracket().
-- Apply after 10_standings_views.sql and 11_knockout_rules.sql.

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
  WITH RECURSIVE parsed_manual_slots AS (
    SELECT
      ksr.match_number,
      ksr.side,
      ksr.label,
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
  ),
  slot_resolution AS (
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
        WHEN ksr.source_type = 'manual_label'
          AND regexp_match(replace(coalesce(ksr.label, ''), 'Grupo ', ''), '^3[^A-L]*([A-L](?:/[A-L])*)$') IS NOT NULL
        THEN (
          SELECT ba.assignments -> (ksr.match_number::text || ':' || ksr.side) ->> 'team_code'
          FROM best_assignment ba
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

GRANT EXECUTE ON FUNCTION public.resolve_knockout_bracket() TO anon, authenticated;
