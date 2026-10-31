"""Truth-preserving device behavior model boundary.

This module deliberately distinguishes validated device models from the current
VirtualCampus engineering fallback. The fallback is useful for the simulator,
but it is not a claim of real-world device learning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

@dataclass(frozen=True)
class DevicePrediction:
    """A device demand prediction with explicit source semantics."""

    device_id: str
    predicted_power_mw: float
    unit: str
    provenance: str
    model_status: str
    model_id: str
    source: str
    fallback_used: bool
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["predicted_power"] = self.predicted_power_mw
        result["model_used"] = self.model_id
        result["model_version"] = self.model_id
        result["target_type"] = self.metadata.get("target_type")
        result["dataset"] = self.metadata.get("dataset")
        result["limitations"] = self.metadata.get("limitations", [])
        result["prediction_quality"] = self.metadata.get("prediction_quality", "LOW")
        result["approved_for_prediction"] = self.metadata.get("approved_for_prediction", False)
        result["approved_for_control"] = self.metadata.get("approved_for_control", False)
        result["predicted_power_kw"] = self.predicted_power_mw * 1000.0
        result["predicted_energy_kwh"] = (
            result["predicted_power_kw"] * float(self.metadata.get("interval_hours", 1.0))
        )
        result["target_unit"] = self.metadata.get("target_units", "MW")
        result["fallback_reason"] = self.metadata.get("reason")
        return result


Fallback = Callable[[], float]


class DeviceModelRegistry:
    """Registry for validated models with explicit simulated fallbacks."""

    def __init__(self) -> None:
        self._models: dict[str, Callable[[Mapping[str, object]], float]] = {}
        self._model_ids: dict[str, str] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(
        self,
        device_id: str,
        predictor: Callable[[Mapping[str, object]], float],
        *,
        model_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not device_id or not model_id:
            raise ValueError("device_id and model_id are required")
        if not callable(predictor):
            raise TypeError("predictor must be callable")
        self._models[device_id] = predictor
        self._model_ids[device_id] = model_id
        self._metadata[device_id] = dict(metadata or {})

    def predict(
        self,
        device_id: str,
        context: Mapping[str, object],
        *,
        fallback: Fallback,
    ) -> DevicePrediction:
        if not device_id:
            raise ValueError("device_id is required")
        if not callable(fallback):
            raise TypeError("fallback must be callable")

        predictor = self._models.get(device_id)
        if predictor is None:
            value = fallback()
            return DevicePrediction(
                device_id=device_id,
                predicted_power_mw=_validate_power(value),
                unit="MW",
                provenance="SIMULATED",
                model_status="SIMULATED_FALLBACK",
                model_id="virtualcampus-engineering-formula",
                source="VirtualCampus deterministic fallback",
                fallback_used=True,
                metadata={
                    "reason": "No approved model registered for the available runtime context.",
                    "target_type": "SIMULATED",
                    "dataset": None,
                    "limitations": ["Deterministic VirtualCampus engineering formula."],
                    "prediction_quality": "LOW",
                    "approved_for_prediction": False,
                    "approved_for_control": False,
                },
            )

        try:
            value = predictor(context)
        except (
            KeyError,
            TypeError,
            ValueError,
            OSError,
            RuntimeError,
            AttributeError,
            ImportError,
        ) as exc:
            value = fallback()
            return DevicePrediction(
                device_id=device_id,
                predicted_power_mw=_validate_power(value),
                unit="MW",
                provenance="SIMULATED",
                model_status="SIMULATED_FALLBACK",
                model_id="virtualcampus-engineering-formula",
                source="VirtualCampus deterministic fallback",
                fallback_used=True,
                metadata={
                    "reason": f"Registered model unavailable for runtime context: {exc}",
                    "target_type": "SIMULATED",
                    "dataset": None,
                    "limitations": ["Model inference failed; fallback preserved safe behavior."],
                    "prediction_quality": "LOW",
                    "approved_for_prediction": False,
                    "approved_for_control": False,
                },
            )
        return DevicePrediction(
            device_id=device_id,
            predicted_power_mw=_validate_power(value),
            unit="MW",
            provenance="DERIVED",
            model_status="VALIDATED_MODEL",
            model_id=self._model_ids[device_id],
            source="Registered device behavior model",
            fallback_used=False,
            metadata={
                **self._metadata[device_id],
                "interval_hours": float(context.get("interval_hours", 1.0)),
            },
        )


def _validate_power(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("device prediction must be numeric")
    if value < 0:
        raise ValueError("device prediction cannot be negative")
    return float(value)


DEFAULT_DEVICE_MODEL_REGISTRY = DeviceModelRegistry()


def _load_lighting_predictor() -> Callable[[Mapping[str, object]], float]:
    import joblib
    import numpy as np
    import pandas as pd

    artifact = Path(__file__).resolve().parent / "saved/device/cubems_lighting_power.joblib"
    model = joblib.load(artifact)

    def predict(context: Mapping[str, object]) -> float:
        states = context["states"]
        parameters = context["parameters"]
        if states["Lighting"] != "ON":
            return 0.0
        timestamp = pd.Timestamp(context["timestamp"])
        hour = timestamp.hour + timestamp.minute / 60
        weekday = timestamp.dayofweek
        features = pd.DataFrame([{
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "weekday_sin": np.sin(2 * np.pi * weekday / 7),
            "weekday_cos": np.cos(2 * np.pi * weekday / 7),
            "day_of_year": timestamp.dayofyear,
            "minute_of_day": timestamp.hour * 60 + timestamp.minute,
        }])
        predicted_kw = max(float(model.predict(features)[0]), 0.0)
        brightness = float(parameters["lighting"]["brightness_pct"]) / 100.0
        return predicted_kw * brightness / 1000.0

    return predict


def _calibrated_hvac_predictor(context: Mapping[str, object]) -> float:
    states = context["states"]
    if states["HVAC"] == "OFF" or not context["environment"]["main_power"]:
        return 0.0
    environment = context["environment"]
    parameters = context["parameters"]["hvac"]
    cooling_delta = max(
        float(environment["outdoor_temperature_c"]) - float(parameters["setpoint_c"]),
        0.0,
    )
    occupancy_factor = min(max(0.7 + 0.3 * float(environment["occupancy_pct"]) / 40.0, 0.7), 1.0)
    ambient_factor = min(max(0.5 + cooling_delta / 12.0, 0.5), 1.0)
    humidity_factor = min(
        max(1.0 + (float(environment["outdoor_humidity_pct"]) - 50.0) / 1000.0, 0.9),
        1.1,
    )
    power_kw = 800.0 * occupancy_factor * ambient_factor * humidity_factor
    power_kw *= float(context["environment"]["device_factors"]["hvac"])
    if states["HVAC"] == "ECO":
        power_kw = min(power_kw, 400.0)
    return max(power_kw, 0.0) / 1000.0


def _calibrated_pump_predictor(context: Mapping[str, object]) -> float:
    states = context["states"]
    if states["Water Pump"] == "OFF" or not context["environment"]["main_power"]:
        return 0.0
    parameters = context["parameters"]["water_pump"]
    demand_factor = 0.7 + (float(parameters["moisture_pct"]) / 100.0) * 0.3
    pressure_factor = float(parameters["pressure_factor"])
    schedule_factor = 1.0 if bool(parameters["schedule_active"]) else 0.85
    power_kw = 500.0 * demand_factor * pressure_factor * schedule_factor
    power_kw *= float(context["environment"]["device_factors"]["water_pump"])
    return max(power_kw, 0.0) / 1000.0


def register_approved_models(registry: DeviceModelRegistry) -> None:
    """Register only evidence-approved models; unsupported devices stay fallback."""

    registry.register(
        "lighting",
        _load_lighting_predictor(),
        model_id="cubems-lighting-power-v1",
        metadata={
            "model_version": "v1",
            "target_type": "DIRECT",
            "dataset": "CU-BEMS Floor 2",
            "target": "sum of z1_Light(kW) through z4_Light(kW)",
            "target_units": "kW",
            "provenance": "REAL_EXTERNAL",
            "limitations": [
                "Generalized building-floor model, not campus telemetry.",
                "Runtime uses timestamp and brightness only; no occupancy/daylight inputs.",
            ],
            "prediction_quality": "HIGH",
            "approved_for_prediction": True,
            "approved_for_control": True,
        },
    )
    registry.register(
        "hvac",
        _calibrated_hvac_predictor,
        model_id="virtualcampus-hvac-calibrated-v1",
        metadata={
            "model_version": "v1",
            "approval_status": "APPROVED_FOR_SIMULATED_CONTROL",
            "target_type": "SIMULATED_CALIBRATED",
            "target": "instantaneous HVAC electrical power",
            "target_units": "kW",
            "dataset": "VirtualCampus engineering calibration; no physical campus telemetry",
            "dataset_type": "SIMULATED_CALIBRATED",
            "provenance": "SIMULATED_CALIBRATED",
            "features": [
                "HVAC state", "outdoor_temperature_c", "outdoor_humidity_pct",
                "occupancy_pct", "setpoint_c",
            ],
            "prediction_quality": "ENGINEERING_CALIBRATED",
            "approved_for_prediction": True,
            "approved_for_control": True,
            "limitations": [
                "Simulation calibration only; not trained on campus HVAC telemetry.",
                "No physical-campus calibration or statistical confidence interval.",
            ],
        },
    )
    registry.register(
        "water_pump",
        _calibrated_pump_predictor,
        model_id="virtualcampus-water-pump-calibrated-v1",
        metadata={
            "model_version": "v1",
            "approval_status": "APPROVED_FOR_SIMULATED_CONTROL",
            "target_type": "SIMULATED_CALIBRATED",
            "target": "instantaneous pump electrical power",
            "target_units": "kW",
            "dataset": "VirtualCampus engineering calibration; UK-DALE remains domain-mismatched evidence",
            "dataset_type": "SIMULATED_CALIBRATED",
            "provenance": "SIMULATED_CALIBRATED",
            "features": ["Water Pump state", "moisture_pct", "pressure_factor", "schedule_active"],
            "prediction_quality": "ENGINEERING_CALIBRATED",
            "approved_for_prediction": True,
            "approved_for_control": True,
            "limitations": [
                "Simulation calibration only; not a campus water-pump telemetry model.",
                "UK-DALE solar-thermal pump and UCI hydraulic artifacts are not used as direct campus targets.",
            ],
        },
    )


try:
    register_approved_models(DEFAULT_DEVICE_MODEL_REGISTRY)
except (FileNotFoundError, OSError, ValueError, ImportError):
    # A missing optional artifact must not prevent the simulator fallback path.
    pass
