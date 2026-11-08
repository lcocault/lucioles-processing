"""Historique des exécutions dans PostgreSQL."""

from __future__ import annotations

from ...domain.ports import RunListener
from ...domain.run import ChainRun, Status, Step, StepRun
from .database import Database
from .repository import date_to_period, period_to_date

INTERRUPTED = "Interrompue : le service s'est arrêté pendant l'exécution"
_ORDER = {step: i for i, step in enumerate(Step)}


class PostgresRunListener(RunListener):
    """Enregistre chaque changement d'état d'une exécution (upsert de la ligne et de ses étapes)."""

    def __init__(self, database: Database):
        self.db = database

    def run_updated(self, run: ChainRun) -> None:
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chain_run (id, chain, period, trigger, status, created_at, started_at, finished_at, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status, started_at = EXCLUDED.started_at,
                    finished_at = EXCLUDED.finished_at, error = EXCLUDED.error
                """,
                (run.id, run.chain, period_to_date(run.period), run.trigger, run.status.value,
                 run.created_at, run.started_at, run.finished_at, run.error),
            )
            cur.executemany(
                """
                INSERT INTO step_run (run_id, step, position, implementation, status, started_at, finished_at, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, step) DO UPDATE SET status = EXCLUDED.status,
                    started_at = EXCLUDED.started_at, finished_at = EXCLUDED.finished_at, error = EXCLUDED.error
                """,
                [(run.id, s.step.value, _ORDER[s.step], s.implementation, s.status.value,
                  s.started_at, s.finished_at, s.error) for s in run.steps],
            )


class PostgresRunStore:
    """Lecture de l'historique et reprise après arrêt du service."""

    def __init__(self, database: Database):
        self.db = database

    def get(self, run_id: str) -> ChainRun | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT id, chain, period, trigger, status, created_at, started_at, finished_at "
                "FROM chain_run WHERE id = %s",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            steps = conn.execute(
                "SELECT step, implementation, status, started_at, finished_at, error "
                "FROM step_run WHERE run_id = %s ORDER BY position",
                (run_id,),
            ).fetchall()
        return ChainRun(
            id=row[0], chain=row[1], period=date_to_period(row[2]), trigger=row[3], status=Status(row[4]),
            created_at=row[5], started_at=row[6], finished_at=row[7],
            steps=[StepRun(Step(s[0]), s[1], Status(s[2]), s[3], s[4], s[5]) for s in steps],
        )

    def recover_interrupted(self) -> int:
        """Marque en échec les exécutions restées `pending`/`running` (arrêt brutal du service).

        À appeler au démarrage du service, avant toute nouvelle exécution. Retourne leur nombre.
        """
        live = "(SELECT id FROM chain_run WHERE status IN ('pending', 'running'))"
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE step_run SET status = 'failed', error = %s, finished_at = now() "
                f"WHERE status = 'running' AND run_id IN {live}",
                (INTERRUPTED,),
            )
            conn.execute(f"UPDATE step_run SET status = 'skipped' WHERE status = 'pending' AND run_id IN {live}")
            cur = conn.execute(
                "UPDATE chain_run SET status = 'failed', error = %s, finished_at = now() "
                "WHERE status IN ('pending', 'running')",
                (INTERRUPTED,),
            )
            return cur.rowcount
