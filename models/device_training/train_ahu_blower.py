"""Train a generalized AHU blower energy model from the acquired raw files.

This is an external real-data model, not campus telemetry.  The source has
only timestamp fields plus interval energy, so no occupancy or weather
features are invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data/external/device_candidates/hvac"
MODEL_FILE = ROOT / "models/saved/device/ahu_blower_energy.joblib"
MANIFEST_FILE = ROOT / "models/saved/device/ahu_blower_energy.manifest.json"
FILES = (
    "KwhConsumptionBlower78_1.csv",
    "KwhConsumptionBlower78_2.csv",
    "KwhConsumptionBlower78_3.csv",
)
FEATURES = [
    "interval_minutes",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "day_of_year",
]


def build_dataset() -> tuple[pd.DataFrame, pd.Series, dict[str, object]]:
    frames = []
    for filename in FILES:
        frame = pd.read_csv(DATA_DIR / filename)
        required = {"TxnDate", "TxnTime", "Consumption"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{filename} is missing {sorted(required - set(frame.columns))}")
        frame["timestamp"] = pd.to_datetime(
            frame["TxnDate"].astype(str) + " " + frame["TxnTime"].astype(str),
            dayfirst=True,
            errors="raise",
        )
        frame["source_file"] = filename
        frames.append(frame[["timestamp", "Consumption", "source_file"]])

    combined = pd.concat(frames, ignore_index=True).sort_values("timestamp")
    duplicate_count = int(combined["timestamp"].duplicated(keep=False).sum())
    combined = combined.drop_duplicates("timestamp", keep="last")
    combined["interval_minutes"] = (
        combined["timestamp"].diff().dt.total_seconds().div(60).fillna(0)
    )
    hour = combined["timestamp"].dt.hour + combined["timestamp"].dt.minute / 60
    weekday = combined["timestamp"].dt.dayofweek
    combined["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    combined["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    combined["day_of_week_sin"] = np.sin(2 * np.pi * weekday / 7)
    combined["day_of_week_cos"] = np.cos(2 * np.pi * weekday / 7)
    combined["day_of_year"] = combined["timestamp"].dt.dayofyear
    x = combined[FEATURES].astype(float)
    y = combined["Consumption"].astype(float)
    if x.isna().any().any() or y.isna().any():
        raise ValueError("HVAC source contains missing training values")
    intervals = combined["timestamp"].diff().dt.total_seconds().dropna() / 60
    profile = {
        "raw_rows": int(sum(len(frame) for frame in frames)),
        "rows_after_duplicate_resolution": int(len(combined)),
        "duplicate_timestamp_rows_removed": duplicate_count,
        "timestamp_start": combined["timestamp"].min().isoformat(),
        "timestamp_end": combined["timestamp"].max().isoformat(),
        "median_interval_minutes": float(intervals.median()),
        "target_min_kwh": float(y.min()),
        "target_max_kwh": float(y.max()),
        "target": "Consumption",
        "target_units": "kWh per irregular source interval",
    }
    return x, y, profile


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }


def train() -> dict[str, object]:
    x, y, profile = build_dataset()
    split = int(len(x) * 0.8)
    x_train, x_test = x.iloc[:split], x.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    baselines = {
        "median": DummyRegressor(strategy="median").fit(x_train, y_train),
        "mean": DummyRegressor(strategy="mean").fit(x_train, y_train),
        "ridge": Ridge(alpha=10.0).fit(x_train, y_train),
    }
    candidates = {
        "random_forest": RandomForestRegressor(
            n_estimators=240, min_samples_leaf=4, max_depth=18,
            random_state=42, n_jobs=-1
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.04, max_leaf_nodes=15,
            l2_regularization=1.0, random_state=42
        ),
    }
    fitted = {name: estimator.fit(x_train, y_train) for name, estimator in candidates.items()}
    baseline_metrics = {
        name: _metrics(y_test, estimator.predict(x_test))
        for name, estimator in baselines.items()
    }
    candidate_metrics = {
        name: _metrics(y_test, estimator.predict(x_test))
        for name, estimator in fitted.items()
    }
    best_baseline_name = min(baseline_metrics, key=lambda name: (
        baseline_metrics[name]["mae"], baseline_metrics[name]["rmse"]
    ))
    best_model_name = min(candidate_metrics, key=lambda name: (
        candidate_metrics[name]["mae"], candidate_metrics[name]["rmse"]
    ))
    model = fitted[best_model_name]
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    manifest = {
        "device": "hvac",
        "model_id": "ahu-blower-energy-v1",
        "model_type": "RandomForestRegressor",
        "dataset": "HVAC AHU Blower Energy Consumption",
        "source": "https://www.kaggle.com/datasets/vitthalmadane/energy-consumption-time-series-dataset",
        "provenance": "REAL_EXTERNAL",
        "target_type": "DIRECT",
        "features": FEATURES,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "split": "chronological 80/20; no shuffle",
        "test_metrics": candidate_metrics[best_model_name],
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "best_baseline": best_baseline_name,
        "best_candidate": best_model_name,
        "beats_best_baseline": (
            candidate_metrics[best_model_name]["mae"] < baseline_metrics[best_baseline_name]["mae"]
            and candidate_metrics[best_model_name]["rmse"] <= baseline_metrics[best_baseline_name]["rmse"]
        ),
        "approved_for_integration": False,
        "approved_for_prediction": False,
        "approved_for_control": False,
        "prediction_quality": "LOW",
        "profile": profile,
        "limitations": [
            "Generalized AHU blower model, not campus HVAC telemetry.",
            "Source contains timestamp and energy only; no weather, occupancy, or setpoint.",
            "Source intervals are irregular and duplicate timestamps were resolved by keeping the last row.",
            "The artifact is not approved for VirtualCampus integration unless it beats the recorded baseline on both MAE and RMSE.",
        ],
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
