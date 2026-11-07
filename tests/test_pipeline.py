import json

import pandas as pd

from lucioles_processing.pipeline import run


def test_end_to_end(communes, tmp_path):
    admin = tmp_path / "admin.gpkg"
    communes.to_file(admin, driver="GPKG")
    pd.DataFrame(
        {"lon": [1.05, 1.25], "lat": [43.05, 43.25], "pm10": [5.0, 45.0]}
    ).to_csv(tmp_path / "pm10_2026-10.csv", sep=";", index=False)
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        f"""
indicator: {{name: air, weights: {{pm10: 1.0}}, thresholds: [10, 20, 30, 40]}}
departments: ["31"]
sources:
  pm10:
    method: nearest_station
    path: {tmp_path}/pm10_{{period}}.csv
    field: pm10
    dims: [lon, lat]
"""
    )
    out = run(cfg, "2026-10", admin, tmp_path / "out", tmp_path / "cache", ("gpkg", "geojson", "kml"))
    assert out == tmp_path / "out" / "air" / "2026-10"
    for f in ("air.gpkg", "air.geojson", "air.kml", "manifest.json"):
        assert (out / f).exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["communes"] == 2 and manifest["missing"] == 0
