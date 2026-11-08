-- Schéma initial : territoires, indicateurs, valeurs, historique des exécutions.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE territory (
    code        text PRIMARY KEY,
    name        text NOT NULL DEFAULT '',
    department  text NOT NULL DEFAULT '',
    geometry    geometry(Geometry, 4326)
);
CREATE INDEX territory_geometry_idx ON territory USING gist (geometry);

CREATE TABLE indicator (
    name text PRIMARY KEY
);

-- Une ligne par (indicateur, période, territoire). `period` est le premier jour du mois.
CREATE TABLE indicator_value (
    indicator       text NOT NULL REFERENCES indicator (name),
    period          date NOT NULL CHECK (period = date_trunc('month', period)::date),
    territory_code  text NOT NULL REFERENCES territory (code),
    value           double precision,
    level           smallint CHECK (level BETWEEN 0 AND 4),
    PRIMARY KEY (indicator, period, territory_code),
    CHECK ((value IS NULL) = (level IS NULL))
);
CREATE INDEX indicator_value_territory_idx ON indicator_value (territory_code);

-- Valeurs avec géométrie, prêtes pour la cartographie.
CREATE VIEW indicator_map AS
SELECT v.indicator, v.period, v.territory_code, t.name AS territory_name,
       t.department, v.value, v.level, t.geometry
FROM indicator_value v JOIN territory t ON t.code = v.territory_code;

CREATE TABLE chain_run (
    id           text PRIMARY KEY,
    chain        text NOT NULL,
    period       date NOT NULL,
    trigger      text NOT NULL,
    status       text NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
    created_at   timestamptz NOT NULL,
    started_at   timestamptz,
    finished_at  timestamptz,
    error        text
);
CREATE INDEX chain_run_chain_idx ON chain_run (chain, created_at DESC);

CREATE TABLE step_run (
    run_id          text NOT NULL REFERENCES chain_run (id) ON DELETE CASCADE,
    step            text NOT NULL,
    position        smallint NOT NULL,
    implementation  text NOT NULL,
    status          text NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')),
    started_at      timestamptz,
    finished_at     timestamptz,
    error           text,
    PRIMARY KEY (run_id, step)
);
