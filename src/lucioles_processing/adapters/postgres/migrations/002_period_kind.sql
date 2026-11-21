-- Périodes annuelles : `period` reste une date (1er janvier pour une année) ; `period_kind` distingue
-- 'month' (AAAA-MM, défaut) de 'year' (AAAA).
ALTER TABLE indicator_value DROP CONSTRAINT IF EXISTS indicator_value_period_check;
ALTER TABLE indicator_value ADD COLUMN period_kind text NOT NULL DEFAULT 'month' CHECK (period_kind IN ('month', 'year'));
ALTER TABLE indicator_value ADD CONSTRAINT indicator_value_period_check CHECK (
    period = date_trunc('month', period)::date AND (period_kind = 'month' OR EXTRACT(MONTH FROM period) = 1)
);
ALTER TABLE chain_run ADD COLUMN period_kind text NOT NULL DEFAULT 'month' CHECK (period_kind IN ('month', 'year'));
