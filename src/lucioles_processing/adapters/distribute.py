"""Étape 6 : distribution des fichiers produits."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from ..domain.model import ProductFile
from ..domain.ports import ProductDistributor, StepContext


class NullDistributor(ProductDistributor):
    """Ne distribue rien : les produits restent dans l'espace de travail."""

    def distribute(self, ctx: StepContext, products: Sequence[ProductFile]) -> None:
        return None


class LocalFolderDistributor(ProductDistributor):
    """Copie les produits dans `<dossier>/<chaîne>/<période>/` (écrase les fichiers existants)."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def distribute(self, ctx: StepContext, products: Sequence[ProductFile]) -> None:
        target = self.directory / ctx.chain / str(ctx.period)
        target.mkdir(parents=True, exist_ok=True)
        for product in products:
            shutil.copy2(product.path, target / product.path.name)
