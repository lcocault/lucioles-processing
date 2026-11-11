import os
import uuid

import geopandas as gpd
import psycopg
import pytest
from psycopg import sql
from shapely.geometry import Polygon

from lucioles_processing.adapters.postgres.database import Database
from tests.http_server import FakeServer


@pytest.fixture
def communes():
    return gpd.GeoDataFrame(
        {
            "code_insee": ["31001", "31002"],
            "code_insee_du_departement": ["31", "31"],
            "nom_officiel": ["Commune A", "Commune B"],
            "geometry": [
                Polygon([(1.0, 43.0), (1.1, 43.0), (1.1, 43.1), (1.0, 43.1)]),
                Polygon([(1.2, 43.2), (1.3, 43.2), (1.3, 43.3), (1.2, 43.3)]),
            ],
        },
        crs="EPSG:4326",
    )


# --- Base PostgreSQL/PostGIS jetable (tests d'intégration et e2e marqués `integration`) ---------
# Nécessite `LUCIOLES_TEST_DATABASE_URL` (serveur avec PostGIS, droit CREATE DATABASE), par exemple
# `postgresql://postgres:postgres@localhost:5432/postgres` (voir docker-compose.yml).
# Les tests sont ignorés si la variable est absente ou si PostGIS n'est pas disponible.

ADMIN_URL = os.environ.get("LUCIOLES_TEST_DATABASE_URL")


def _with_dbname(url: str, name: str) -> str:
    return psycopg.conninfo.make_conninfo(url, dbname=name)


@pytest.fixture(scope="session")
def admin_url():
    if not ADMIN_URL:
        pytest.skip("LUCIOLES_TEST_DATABASE_URL non définie : tests d'intégration PostgreSQL ignorés")
    try:
        with psycopg.connect(ADMIN_URL) as conn:
            available = conn.execute(
                "SELECT count(*) FROM pg_available_extensions WHERE name = 'postgis'"
            ).fetchone()[0]
    except psycopg.OperationalError as exc:
        pytest.skip(f"Serveur PostgreSQL inaccessible : {exc}")
    if not available:
        pytest.skip("Extension PostGIS indisponible sur le serveur de test")
    return ADMIN_URL


@pytest.fixture
def empty_db_factory(admin_url):
    """Crée des bases vides distinctes, supprimées après le test."""
    names = []

    def create():
        name = f"lucioles_test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C'").format(
                    sql.Identifier(name)
                )
            )
        names.append(name)
        return Database(_with_dbname(admin_url, name))

    try:
        yield create
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            for name in names:
                conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def empty_db(empty_db_factory):
    """Base vide (sans schéma), supprimée après le test."""
    return empty_db_factory()


@pytest.fixture
def db(empty_db):
    """Base avec le schéma à jour."""
    empty_db.migrate()
    return empty_db


@pytest.fixture
def http_server():
    """Serveur HTTP local (ETag, Last-Modified, requêtes conditionnelles) : aucun accès réseau réel."""
    server = FakeServer()
    yield server
    server.close()
