-- Une période annuelle et le mois de janvier partagent la même date, mais restent distincts.
ALTER TABLE indicator_value DROP CONSTRAINT indicator_value_pkey;
ALTER TABLE indicator_value ADD CONSTRAINT indicator_value_pkey
    PRIMARY KEY (indicator, period, period_kind, territory_code);
