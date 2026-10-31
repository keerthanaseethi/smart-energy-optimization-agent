"""Train a hydraulic motor-power proxy from the UCI hydraulic test rig.

The target is the measured EPS1 motor power (W), summarized per 60-second
cycle. This is a real measured target, but it is not campus water-pump
telemetry; the saved manifest therefore marks it as a PROXY and it is not
registered as the active VirtualCampus water-pump model.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


DATA_DIR = Path("data/external/uci_hydraulic")
MODEL_FILE = Path("models/saved/device/hydraulic_motor_power_proxy.joblib")
MANIFEST_FILE = Path("models/saved/device/hydraulic_motor_power_proxy.manifest.json")

CHANNELS = {
    "PS1": 6000,
    "PS2": 6000,
    "PS3": 6000,
    "PS4": 6000,
    "PS5": 6000,
    "PS6": 6000,
    "FS1": 600,
    "FS2": 600,
    "TS1": 60,
    "TS2": 60,
    "TS3": 60,
    "TS4": 60,
    "VS1": 60,
    "SE": 60,
    "CE": 60,
    "CP": 60,
}


def _read_channel(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.txt"
    return pd.read_csv(path, sep="\t", header=None, dtype="float32")


def _summary_features(channel: pd.DataFrame, name: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            f"{name}_mean": channel.mean(axis=1),
            f"{name}_std": channel.std(axis=1, ddof=0),
            f"{name}_min": channel.min(axis=1),
            f"{name}_max": channel.max(axis=1),
        }
    )


def build_dataset() -> tuple[pd.DataFrame, pd.Series, dict[str, object]]:
    target_frame = _read_channel("EPS1")
    if target_frame.shape[1] != 6000:
        raise ValueError(f"EPS1 must contain 6000 samples per cycle, got {target_frame.shape[1]}")

    features = pd.concat(
        [_summary_features(_read_channel(name), name) for name in CHANNELS],
        axis=1,
    )
    target = target_frame.mean(axis=1).rename("motor_power_w")
    if len(features) != len(target):
        raise ValueError("Feature and target cycle counts do not match")
    if features.isna().any().any() or target.isna().any():
        raise ValueError("Hydraulic dataset unexpectedly contains missing values")
    if features.duplicated().any():
        raise ValueError("Hydraulic feature rows contain duplicates")
    return features, target, {
        "rows": int(len(target)),
        "feature_count": int(features.shape[1]),
        "target": "EPS1 cycle mean",
        "target_units": "W",
        "sampling": "100 Hz sensor summarized over 60-second cycles",
        "missing_values": 0,
        "duplicate_feature_rows": int(features.duplicated().sum()),
    }


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae_w": float(mean_absolute_error(actual, predicted)),
        "rmse_w": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }


def train() -> dict[str, object]:
    features, target, profile = build_dataset()
    split = int(len(features) * 0.8)
    x_train, x_test = features.iloc[:split], features.iloc[split:]
    y_train, y_test = target.iloc[:split], target.iloc[split:]

    baseline = DummyRegressor(strategy="median").fit(x_train, y_train)
    baseline_metrics = _metrics(y_test, baseline.predict(x_test))

    model = RandomForestRegressor(
        n_estimators=160,
        max_depth=18,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)
    model_metrics = _metrics(y_test, model.predict(x_test))

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    manifest = {
        "device": "water_pump",
        "model_id": "hydraulic-motor-power-proxy-v1",
        "model_type": "RandomForestRegressor",
        "dataset": "UCI Condition Monitoring of Hydraulic Systems",
        "source": "https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems",
        "target": "EPS1 cycle mean motor power",
        "target_units": "W",
        "target_type": "PROXY",
        "provenance": "REAL_HISTORICAL",
        "features": list(features.columns),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "split": "chronological 80/20; no shuffle",
        "baseline_metrics": baseline_metrics,
        "test_metrics": model_metrics,
        "profile": profile,
        "limitations": [
            "Measured on an oil-based hydraulic test rig, not a campus water pump.",
            "EPS1 is motor power for the rig; it is not a direct KAIRA pump-meter channel.",
            "Runtime VirtualCampus does not expose the 64 engineered hydraulic sensor features.",
            "Not registered as the active VirtualCampus water-pump model.",
        ],
        "model_file": str(MODEL_FILE),
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
