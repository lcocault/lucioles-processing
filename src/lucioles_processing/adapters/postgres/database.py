"""Connexion à PostgreSQL et migrations de schéma versionnées (fichiers SQL numérotés)."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources

import psycopg

#: Variable d'environnement portant l'URL de connexion (aucun secret dans les fichiers du dépôt).
ENV_VAR = "LUCIOLES_DATABASE_URL"

_LOCK_KEY = 7_265_001  # verrou consultatif : une seule migration à la fois


class ConfigurationError(ValueError):
    """Configuration de la base absente ou invalide."""


class SchemaOutdatedError(RuntimeError):
    """Des migrations ne sont pas appliquées : lancer `lucioles db migrate`."""


def database_url(environ: Mapping[str, str] | None = None, env_var: str = ENV_VAR) -> str:
    """URL de connexion lue dans l'environnement ; erreur explicite si elle manque."""
    environ = os.environ if environ is None else environ
    url = environ.get(env_var, "").strip()
    if not url:
        raise ConfigurationError(f"Variable d'environnement {env_var} absente (URL PostgreSQL)")
    return url


@dataclass(frozen=True)
class Migration:
    version: str  # ex. "001"
    name: str
    sql: str


def list_migrations() -> list[Migration]:
    """Migrations fournies avec l'application, triées par version."""
    found = []
    for entry in resources.files(__package__).joinpath("migrations").iterdir():
        match = re.fullmatch(r"(\d{3})_(\w+)\.sql", entry.name)
        if match:
            found.append(Migration(match[1], match[2], entry.read_text(encoding="utf-8")))
    found.sort(key=lambda m: m.version)
    versions = [m.version for m in found]
    if len(set(versions)) != len(versions):
        raise ConfigurationError(f"Versions de migration en double : {versions}")
    return found


class Database:
    def __init__(self, url: str):
        self.url = url

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None, env_var: str = ENV_VAR) -> Database:
        return cls(database_url(environ, env_var))

    def connect(self) -> psycopg.Connection:
        """Nouvelle connexion (à utiliser comme gestionnaire de contexte : valide ou annule)."""
        return psycopg.connect(self.url)

    # --- migrations -------------------------------------------------------

    def applied_versions(self) -> list[str]:
        with self.connect() as conn:
            exists = conn.execute("SELECT to_regclass('schema_migration') IS NOT NULL").fetchone()[0]
            if not exists:
                return []
            return [r[0] for r in conn.execute("SELECT version FROM schema_migration ORDER BY version")]

    def pending(self) -> list[Migration]:
        applied = set(self.applied_versions())
        return [m for m in list_migrations() if m.version not in applied]

    def migrate(self) -> list[str]:
        """Applique les migrations manquantes, dans l'ordre ; retourne les versions appliquées."""
        done = []
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_KEY,))
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migration ("
                "version text PRIMARY KEY, name text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migration")}
            for migration in list_migrations():
                if migration.version in applied:
                    continue
                conn.execute(migration.sql)
                conn.execute(
                    "INSERT INTO schema_migration (version, name) VALUES (%s, %s)",
                    (migration.version, migration.name),
                )
                done.append(migration.version)
        return done

    def ensure_current(self) -> None:
        """Lève `SchemaOutdatedError` si le schéma n'est pas à jour."""
        pending = self.pending()
        if pending:
            raise SchemaOutdatedError(
                f"Schéma de base non à jour (migrations en attente : {[m.version for m in pending]}) ; "
                "exécuter `lucioles db migrate`"
            )
