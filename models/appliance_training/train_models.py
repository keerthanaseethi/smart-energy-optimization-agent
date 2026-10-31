from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
import joblib

from simulation.devices import VirtualCampus


INPUT_FILE = Path("data/simulated/campus_context.csv")
MODEL_FILE = Path("models/saved/appliance_load_models.joblib")
MANIFEST_FILE = Path("models/saved/appliance_load_models.manifest.json")
FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "temperature",
    "academic_occupancy",
    "academic_schedule",
    "hvac_on",
    "lighting_on",
    "ev_on",
    "pump_on",
]
TARGETS = ["HVAC_MW", "Lighting_MW", "EV_MW", "Water_Pump_MW"]


def _training_row(row: pd.Series) -> tuple[list[float], list[float]]:
    campus = VirtualCampus()
    campus.environment.configure(
        occupancy_pct=float(row["academic_occupancy"]),
        outdoor_temperature_c=float(row["temperature"]),
    )
    if row["academic_hvac"] == "ON":
        campus.hvac.turn_on()
    if row["academic_lighting"] == "ON":
        campus.lighting.turn_on()
    if row["ev_charging"] == "ON":
        campus.ev_charger.start_charging()
    if row["pump_state"] == "ON":
        campus.water_pump.turn_on()
    features = [
        float(row["hour"]),
        float(row["day_of_week"]),
        float(row["is_weekend"]),
        float(row["temperature"]),
        float(row["academic_occupancy"]),
        float(row["academic_schedule"]),
        float(row["academic_hvac"] == "ON"),
        float(row["academic_lighting"] == "ON"),
        float(row["ev_charging"] == "ON"),
        float(row["pump_state"] == "ON"),
    ]
    breakdown = campus.get_load_breakdown()
    targets = [float(breakdown[key]) for key in TARGETS]
    return features, targets


def train() -> dict[str, object]:
    data = pd.read_csv(INPUT_FILE)
    rows = [_training_row(row) for _, row in data.iterrows()]
    x = pd.DataFrame([item[0] for item in rows], columns=FEATURES)
    y = pd.DataFrame([item[1] for item in rows], columns=TARGETS)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, shuffle=False
    )
    model = MultiOutputRegressor(
        RandomForestRegressor(
            n_estimators=160,
            max_depth=14,
            random_state=42,
            n_jobs=-1,
        )
    )
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    mae_by_device = {
        target: float(mean_absolute_error(y_test[target], prediction[:, index]))
        for index, target in enumerate(TARGETS)
    }
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    manifest = {
        "model_file": str(MODEL_FILE),
        "model_type": "MultiOutputRegressor(RandomForestRegressor)",
        "targets": TARGETS,
        "features": FEATURES,
        "rows": len(data),
        "test_rows": len(x_test),
        "mae_mw": mae_by_device,
        "provenance": "DERIVED_FROM_SIMULATED_VIRTUALCAMPUS",
        "source": str(INPUT_FILE),
        "warning": "This model learns the current VirtualCampus simulation formulas and is not real device telemetry.",
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
