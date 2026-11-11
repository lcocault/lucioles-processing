"""Enregistrement des adaptateurs fournis avec l'application."""

from __future__ import annotations

from pathlib import Path

from ..application.registry import BuildContext, Registry
from ..domain.run import Step
from .build import FORMATS, MapFilesBuilder
from .calculate import WeightedSumCalculator
from .distribute import LocalFolderDistributor, NullDistributor
from .fetch import ConfiguredSourcesFetcher
from .postgres.database import ENV_VAR, Database
from .postgres.repository import PostgresIndicatorRepository
from .read import CommuneAggregationReader
from .repository import InMemoryRepository, NullRepository


def default_registry() -> Registry:
    reg = Registry()
    reg.register(
        Step.FETCH,
        "configured_sources",
        lambda c: ConfiguredSourcesFetcher(
            c.definition.sources,
            c.definition.boundaries,
            Path(c.params["cache_dir"]) if c.params.get("cache_dir") else Path("cache"),
        ),
    )
    reg.register(
        Step.READ,
        "commune_aggregation",
        lambda c: CommuneAggregationReader(c.definition.sources, c.definition.boundaries),
    )
    reg.register(Step.CALCULATE, "weighted_sum", lambda c: WeightedSumCalculator(c.definition.indicator))
    reg.register(Step.SAVE, "none", lambda c: NullRepository())
    reg.register(
        Step.SAVE,
        "postgres",
        # l'URL de connexion vient de l'environnement (variable nommée par `url_env`), jamais du YAML
        lambda c: PostgresIndicatorRepository(
            Database.from_env(env_var=c.params.get("url_env", ENV_VAR))
        ),
    )
    reg.register(Step.SAVE, "memory", lambda c: InMemoryRepository())
    reg.register(
        Step.BUILD,
        "map_files",
        lambda c: MapFilesBuilder(c.definition, c.params.get("formats", FORMATS)),
    )
    reg.register(Step.DISTRIBUTE, "none", lambda c: NullDistributor())
    reg.register(Step.DISTRIBUTE, "local_folder", lambda c: LocalFolderDistributor(Path(c.require("directory"))))
    return reg


__all__ = ["BuildContext", "default_registry"]
