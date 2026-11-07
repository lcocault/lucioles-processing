"""Enregistrement des adaptateurs fournis avec l'application."""

from __future__ import annotations

from pathlib import Path

from ..application.registry import BuildContext, Registry
from ..domain.run import Step
from .build import FORMATS, MapFilesBuilder
from .calculate import WeightedSumCalculator
from .distribute import LocalFolderDistributor, NullDistributor
from .fetch import ConfiguredSourcesFetcher
from .read import CommuneAggregationReader
from .repository import InMemoryRepository, NullRepository


def default_registry() -> Registry:
    reg = Registry()
    reg.register(
        Step.FETCH,
        "configured_sources",
        lambda c: ConfiguredSourcesFetcher(
            c.definition.sources, Path(c.params["cache_dir"]) if c.params.get("cache_dir") else None
        ),
    )
    reg.register(
        Step.READ,
        "commune_aggregation",
        lambda c: CommuneAggregationReader(
            c.definition.sources, Path(c.require("admin")), [str(d) for d in c.params.get("departments", [])]
        ),
    )
    reg.register(Step.CALCULATE, "weighted_sum", lambda c: WeightedSumCalculator(c.definition.indicator))
    reg.register(Step.SAVE, "none", lambda c: NullRepository())
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
