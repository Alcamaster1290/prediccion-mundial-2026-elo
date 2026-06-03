-- 06_national_elo_schema.sql
-- ELO ratings for all 48 FIFA World Cup 2026 participants.
-- Source: https://www.international-football.net/elo-ratings-table
-- Seeded with June 2, 2026 snapshot via scripts/seed_international_elo.py

CREATE TABLE IF NOT EXISTS national_elo_ratings (
  id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  team_code    TEXT        NOT NULL,
  country_name TEXT        NOT NULL,
  rank         INTEGER     NOT NULL,
  elo          INTEGER     NOT NULL,
  rating_date  DATE        NOT NULL,
  source       TEXT        NOT NULL DEFAULT 'international-football.net',
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (team_code, rating_date)
);

ALTER TABLE national_elo_ratings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read elo ratings"
  ON national_elo_ratings FOR SELECT USING (true);

-- Verify:
-- SELECT team_code, country_name, rank, elo
-- FROM national_elo_ratings
-- WHERE rating_date = '2026-06-02'
-- ORDER BY rank;
