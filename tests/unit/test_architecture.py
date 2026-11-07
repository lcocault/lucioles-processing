"""Règle de l'architecture hexagonale : le domaine ne dépend d'aucune bibliothèque d'E/S."""

import ast
from pathlib import Path

import lucioles_processing

SRC = Path(lucioles_processing.__file__).parent
FORBIDDEN = {
    "geopandas", "shapely", "pandas", "numpy", "scipy", "rasterio", "xarray", "netCDF4",
    "simplekml", "matplotlib", "yaml", "psycopg", "psycopg2", "sqlalchemy", "fastapi",
    "flask", "requests", "urllib", "subprocess", "shutil",
}


def imported_roots(path: Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def relative_imports(path: Path) -> set[str]:
    return {
        (node.module or "").split(".")[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom) and node.level >= 2
    }


def test_domain_has_no_io_dependency():
    files = list((SRC / "domain").glob("*.py"))
    assert files
    for f in files:
        assert not imported_roots(f) & FORBIDDEN, f"{f.name} importe une dépendance d'E/S"


def test_domain_does_not_import_other_layers():
    for f in (SRC / "domain").glob("*.py"):
        assert not imported_roots(f) & {"lucioles_processing"}
        assert not relative_imports(f), f"{f.name} remonte hors du domaine"
