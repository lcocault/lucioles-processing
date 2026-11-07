"""Étape 2 : lecture des données et mapping vers le modèle interne."""

from __future__ import annotations

import math
from pathlib import Path

import shapely

from ..config import SourceConfig
from ..constants import ADMIN_CODE_COLUMN, ADMIN_DEPT_COLUMN, ADMIN_NAME_COLUMN
from ..domain.model import Dataset, Observation, Territory
from ..domain.ports import DataReader, RawData, StepContext
from .admin import load_admin
from .spatial import SpatialExtractor


class CommuneAggregationReader(DataReader):
    """Agrège chaque source par commune du fond ADMIN_EXPRESS et produit un `Dataset`."""

    def __init__(self, sources: dict[str, SourceConfig], admin: Path, departments: list[str]):
        self.sources = sources
        self.admin = admin
        self.departments = departments

    def read(self, ctx: StepContext, raw: RawData) -> Dataset:
        communes = load_admin(self.admin, self.departments)
        territories = tuple(self._territory(index, row) for index, row in communes.iterrows())
        codes = [t.code for t in territories]

        extractor = SpatialExtractor(communes)
        observations = []
        for name, source in self.sources.items():
            series = extractor.extract(source, raw[name])
            observations.extend(
                Observation(name, code, None if math.isnan(value) else float(value))
                for code, value in zip(codes, series, strict=True)
            )
        return Dataset(ctx.period, territories, tuple(self.sources), tuple(observations))

    @staticmethod
    def _territory(index, row) -> Territory:
        return Territory(
            code=str(row.get(ADMIN_CODE_COLUMN, index)),
            name=str(row.get(ADMIN_NAME_COLUMN, "")),
            department=str(row.get(ADMIN_DEPT_COLUMN, "")),
            # précision maximale : la géométrie doit survivre au passage par le WKT
            geometry_wkt=shapely.to_wkt(row.geometry, rounding_precision=-1),
        )
