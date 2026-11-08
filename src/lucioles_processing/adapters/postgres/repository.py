"""Étape 4 : enregistrement des indicateurs dans PostgreSQL / PostGIS."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ...domain.model import IndicatorValue, Period, Territory
from ...domain.ports import IndicatorRepository, StepContext
from .database import Database


def period_to_date(period: Period) -> date:
    return date(period.year, period.month, 1)


def date_to_period(value: date) -> Period:
    return Period(value.year, value.month)


class PostgresIndicatorRepository(IndicatorRepository):
    def __init__(self, database: Database):
        self.db = database

    def save(
        self, ctx: StepContext, territories: Sequence[Territory], values: Sequence[IndicatorValue]
    ) -> None:
        """Enregistre en une transaction : tout ou rien, et remplace les valeurs de (indicateur, période)."""
        self.db.ensure_current()
        with self.db.connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO territory (code, name, department, geometry)
                VALUES (%s, %s, %s, CASE WHEN %s::text IS NULL THEN NULL ELSE ST_GeomFromText(%s, 4326) END)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name, department = EXCLUDED.department, geometry = EXCLUDED.geometry
                """,
                [(t.code, t.name, t.department, t.geometry_wkt, t.geometry_wkt) for t in territories],
            )
            for indicator, period in sorted({(v.indicator, v.period) for v in values}, key=str):
                cur.execute("INSERT INTO indicator (name) VALUES (%s) ON CONFLICT DO NOTHING", (indicator,))
                cur.execute(
                    "DELETE FROM indicator_value WHERE indicator = %s AND period = %s",
                    (indicator, period_to_date(period)),
                )
            cur.executemany(
                "INSERT INTO indicator_value (indicator, period, territory_code, value, level) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (v.indicator, period_to_date(v.period), v.territory_code, v.value, v.level)
                    for v in values
                ],
            )

    def find(
        self, indicator: str, period: Period, territory_code: str | None = None
    ) -> list[IndicatorValue]:
        """Valeurs d'un indicateur pour une période, éventuellement limitées à un territoire."""
        query = (
            "SELECT indicator, period, territory_code, value, level FROM indicator_value "
            "WHERE indicator = %s AND period = %s"
        )
        params: list = [indicator, period_to_date(period)]
        if territory_code is not None:
            query += " AND territory_code = %s"
            params.append(territory_code)
        with self.db.connect() as conn:
            rows = conn.execute(query + " ORDER BY territory_code", params).fetchall()
        return [IndicatorValue(r[0], date_to_period(r[1]), r[2], r[3], r[4]) for r in rows]
