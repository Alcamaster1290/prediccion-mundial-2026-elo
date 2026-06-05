-- 22_elo_model_explainer.sql
-- Full-access RPC for explaining the ELO model and per-team data coverage.
-- Apply after 21_admin_team_content_monitor.sql.

CREATE OR REPLACE FUNCTION public.get_elo_model_explainer()
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor uuid := (select auth.uid());
  has_full_access boolean := false;
BEGIN
  IF actor IS NULL THEN
    RETURN jsonb_build_object('success', false, 'message', 'Inicia sesion para ver este apartado.');
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM public.profiles p
    WHERE p.id = actor
      AND p.is_premium = true
  ) OR public.has_staff_role('admin')
  INTO has_full_access;

  IF NOT has_full_access THEN
    RETURN jsonb_build_object('success', false, 'message', 'Completa tu acceso para ver este apartado.');
  END IF;

  RETURN (
    WITH player_counts AS (
      SELECT
        p.team_code,
        count(*)::integer AS player_rows,
        count(*) FILTER (WHERE p.titular)::integer AS starter_rows,
        count(*) FILTER (WHERE coalesce(p.elo_club, p.elo_player) IS NOT NULL)::integer AS player_elo_rows,
        count(*) FILTER (
          WHERE p.titular
            AND coalesce(p.elo_club, p.elo_player) IS NOT NULL
        )::integer AS starter_elo_rows
      FROM public.players p
      GROUP BY p.team_code
    ),
    latest_strength AS (
      SELECT DISTINCT ON (tss.team_code)
        tss.team_code,
        tss.version,
        tss.elo_intl,
        tss.elo_club_avg,
        tss.strength_score,
        tss.method,
        tss.created_at
      FROM public.team_strength_snapshots tss
      ORDER BY tss.team_code, tss.created_at DESC, tss.version DESC
    ),
    team_rows AS (
      SELECT
        t.team_code,
        t.name,
        t.group_id,
        t.flag_url,
        coalesce(pc.player_rows, 0) AS player_rows,
        coalesce(pc.starter_rows, 0) AS starter_rows,
        coalesce(pc.player_elo_rows, 0) AS player_elo_rows,
        coalesce(pc.starter_elo_rows, 0) AS starter_elo_rows,
        sl.version,
        sl.elo_intl,
        sl.elo_club_avg,
        sl.strength_score,
        coalesce(sl.method, 'elo_intl_only') AS strength_method,
        CASE
          WHEN coalesce(sl.method, 'elo_intl_only') = 'xi_blend_adj'
           AND coalesce(pc.starter_elo_rows, 0) >= 8
          THEN 'xi_blend_ready'
          WHEN coalesce(pc.player_rows, 0) > 0
            OR coalesce(sl.method, 'elo_intl_only') = 'xi_blend_adj'
          THEN 'needs_player_elo'
          ELSE 'elo_intl_only'
        END AS coverage_tier
      FROM public.teams t
      LEFT JOIN player_counts pc ON pc.team_code = t.team_code
      LEFT JOIN latest_strength sl ON sl.team_code = t.team_code
    )
    SELECT jsonb_build_object(
      'success', true,
      'model', jsonb_build_object(
        'name', 'Modelo ELO hibrido',
        'rating_date', '2026-06-02',
        'elo_source', 'international-football.net',
        'formula', 'elo_intl + (xi_blend - avg_xi_blend) * club_adj_weight',
        'club_adj_weight', 0.35,
        'avg_xi_blend', 1675.3,
        'base_goals_per_team', 1.3,
        'elo_scale', 400,
        'minimum_starter_elo_for_xi_blend_ready', 8,
        'notes', jsonb_build_array(
          'El ELO internacional es la base para las 48 selecciones.',
          'Cuando hay suficientes titulares con ELO de club, el XI ajusta la fuerza del equipo.',
          'Los equipos sin muestra suficiente siguen activos con base internacional mientras se completa la data.'
        )
      ),
      'summary', (
        SELECT jsonb_build_object(
          'total_teams', count(*),
          'xi_blend_ready', count(*) FILTER (WHERE coverage_tier = 'xi_blend_ready'),
          'needs_player_elo', count(*) FILTER (WHERE coverage_tier = 'needs_player_elo'),
          'elo_intl_only', count(*) FILTER (WHERE coverage_tier = 'elo_intl_only')
        )
        FROM team_rows
      ),
      'teams', coalesce((
        SELECT jsonb_agg(
          jsonb_build_object(
            'team_code', team_code,
            'name', name,
            'group_id', group_id,
            'flag_url', flag_url,
            'version', version,
            'elo_intl', elo_intl,
            'xi_blend', elo_club_avg,
            'strength_score', strength_score,
            'strength_method', strength_method,
            'player_rows', player_rows,
            'starter_rows', starter_rows,
            'player_elo_rows', player_elo_rows,
            'starter_elo_rows', starter_elo_rows,
            'starter_elo_missing', greatest(11 - starter_elo_rows, 0),
            'coverage_tier', coverage_tier,
            'coverage_label', CASE coverage_tier
              WHEN 'xi_blend_ready' THEN 'Listo para XI'
              WHEN 'needs_player_elo' THEN 'Faltan ELOs'
              ELSE 'Base internacional'
            END
          )
          ORDER BY
            CASE coverage_tier
              WHEN 'xi_blend_ready' THEN 1
              WHEN 'needs_player_elo' THEN 2
              ELSE 3
            END,
            strength_score DESC NULLS LAST,
            group_id,
            team_code
        )
        FROM team_rows
      ), '[]'::jsonb)
    )
  );
END;
$$;

REVOKE ALL ON FUNCTION public.get_elo_model_explainer() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_elo_model_explainer() TO authenticated;
