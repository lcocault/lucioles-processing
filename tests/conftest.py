import geopandas as gpd
import pytest
from shapely.geometry import Polygon


@pytest.fixture
def communes():
    return gpd.GeoDataFrame(
        {
            "code_insee_du_departement": ["31", "31"],
            "nom_officiel": ["Commune A", "Commune B"],
            "geometry": [
                Polygon([(1.0, 43.0), (1.1, 43.0), (1.1, 43.1), (1.0, 43.1)]),
                Polygon([(1.2, 43.2), (1.3, 43.2), (1.3, 43.3), (1.2, 43.3)]),
            ],
        },
        crs="EPSG:4326",
    )
