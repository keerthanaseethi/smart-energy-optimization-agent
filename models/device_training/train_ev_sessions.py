"""Train a session-level EV charging energy model from measured sessions."""

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
DATA_FILE = ROOT / "data/external/device_candidates/ev/archive (34)/Dataset 1_EV charging reports.csv"
MODEL_FILE = ROOT / "models/saved/device/ev_session_energy.joblib"
MANIFEST_FILE = ROOT / "models/saved/device/ev_session_energy.manifest.json"
FEATURES = [
    "duration_hours",
    "start_hour_sin",
    "start_hour_cos",
    "weekday_sin",
    "weekday_cos",
    "month_sin",
    "month_cos",
    "garage_code",
]


def build_dataset() -> tuple[pd.DataFrame, pd.Series, dict[str, object]]:
    frame = pd.read_csv(DATA_FILE, sep=";", decimal=",")
    required = {"Start_plugin", "Duration_hours", "El_kWh", "User_type"}
    if not required.issubset(frame.columns):
        raise ValueError(f"EV source is missing {sorted(required - set(frame.columns))}")
    timestamp = pd.to_datetime(frame["Start_plugin"], dayfirst=True, errors="raise")
    duration = pd.to_numeric(frame["Duration_hours"], errors="coerce")
    target = pd.to_numeric(frame["El_kWh"], errors="raise")
    valid = duration.notna() & target.notna()
    frame = frame.loc[valid].copy()
    timestamp = timestamp.loc[valid]
    duration = duration.loc[valid]
    target = target.loc[valid]
    order = timestamp.argsort()
    frame = frame.iloc[order].reset_index(drop=True)
    timestamp = timestamp.iloc[order].reset_index(drop=True)
    duration = duration.iloc[order].reset_index(drop=True)
    target = target.iloc[order].reset_index(drop=True)
    hour = timestamp.dt.hour + timestamp.dt.minute / 60
    weekday = timestamp.dt.dayofweek
    month = timestamp.dt.month
    x = pd.DataFrame(
        {
            "duration_hours": duration,
            "start_hour_sin": np.sin(2 * np.pi * hour / 24),
            "start_hour_cos": np.cos(2 * np.pi * hour / 24),
            "weekday_sin": np.sin(2 * np.pi * weekday / 7),
            "weekday_cos": np.cos(2 * np.pi * weekday / 7),
            "month_sin": np.sin(2 * np.pi * month / 12),
            "month_cos": np.cos(2 * np.pi * month / 12),
            "garage_code": frame["Garage_ID"].astype("category").cat.codes,
        }
    ).astype(float)
    if (target < 0).any() or x.isna().any().any() or target.isna().any():
        raise ValueError("EV source contains invalid training values")
    profile = {
        "raw_rows": int(len(valid)),
        "rows": int(len(frame)),
        "rows_dropped_missing_duration": int((~valid).sum()),
        "target": "El_kWh",
        "target_units": "kWh per charging session",
        "timestamp": "Start_plugin",
        "session_id": "session_ID",
        "unique_sessions": int(frame["session_ID"].nunique()),
        "source": str(DATA_FILE),
    }
    return x, target, profile


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
            n_estimators=240, min_samples_leaf=4, random_state=42, n_jobs=-1
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
        "device": "ev_charging",
        "model_id": "ev-session-energy-v1",
        "model_type": "RandomForestRegressor",
        "dataset": "Residential EV charging from apartment buildings",
        "source": "https://www.kaggle.com/datasets/anshtanwar/residential-ev-chargingfrom-apartment-buildings",
        "provenance": "REAL_EXTERNAL",
        "target_type": "DIRECT",
        "features": FEATURES,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "split": "chronological source order 80/20; no shuffle",
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
        "approved_for_prediction": True,
        "approved_for_control": False,
        "prediction_quality": "MEDIUM",
        "profile": profile,
        "limitations": [
            "Session-energy model, not a charger waveform or instantaneous-power model.",
            "Runtime integration requires real session inputs and must not fabricate departure or duration.",
            "Synthetic hourly scenario files from the archive were not used.",
            "The artifact is not approved for VirtualCampus integration unless it beats the recorded baseline on both MAE and RMSE.",
        ],
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
