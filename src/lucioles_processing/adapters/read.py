"""Étape 2 : lecture des données et mapping vers le modèle interne."""

from __future__ import annotations

import math

import shapely

from ..config import BoundariesConfig, SourceConfig
from ..domain.model import Dataset, Observation, Territory
from ..domain.ports import BOUNDARIES_KEY, DataReader, RawData, StepContext
from .admin import load_admin
from .spatial import SpatialExtractor


class CommuneAggregationReader(DataReader):
    """Agrège chaque source par commune du fond administratif et produit un `Dataset`."""

    def __init__(self, sources: dict[str, SourceConfig], boundaries: BoundariesConfig):
        self.sources = sources
        self.boundaries = boundaries

    def read(self, ctx: StepContext, raw: RawData) -> Dataset:
        communes = load_admin(raw[BOUNDARIES_KEY].path, self.boundaries)
        territories = tuple(
            Territory(
                code=row.code,
                name=str(row.name or ""),
                department=str(row.department or ""),
                # précision maximale : la géométrie doit survivre au passage par le WKT
                geometry_wkt=shapely.to_wkt(row.geometry, rounding_precision=-1),
            )
            for row in communes.itertuples(index=False)
        )
        extractor = SpatialExtractor(communes)
        observations = []
        for name, source in self.sources.items():
            series = extractor.extract(source, raw[name].path)
            observations.extend(
                Observation(name, t.code, None if math.isnan(value) else float(value))
                for t, value in zip(territories, series, strict=True)
            )
        return Dataset(ctx.period, territories, tuple(self.sources), tuple(observations), inputs=dict(raw))
