from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


MANIFEST = Path("models/saved/device/hydraulic_motor_power_proxy.manifest.json")
MODEL = Path("models/saved/device/hydraulic_motor_power_proxy.joblib")


def test_hydraulic_proxy_artifact_loads_with_recorded_schema() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = joblib.load(MODEL)
    feature_count = len(manifest["features"])
    prediction = model.predict(
        pd.DataFrame([[0.0] * feature_count], columns=manifest["features"])
    )

    assert manifest["profile"]["rows"] == 2205
    assert manifest["target_units"] == "W"
    assert manifest["target_type"] == "PROXY"
    assert prediction.shape == (1,)
    assert float(prediction[0]) >= 0.0
