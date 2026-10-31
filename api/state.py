from __future__ import annotations

import ast
import datetime
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from adapters.simulation_adapter import SimulationAdapter
from agent.agent import EnergyAgent
from agent.llm import GroundedEnergyAssistant, build_groq_assistant
from data.provenance import make_provenance
from simulation.decision_log import DecisionLogger


INPUT_FILE = Path("data/simulated/campus_context.csv")
UI_STATE_FILE = Path("data/simulated/ui_state.json")
RUNTIME_STATE_FILE = Path("data/simulated/runtime_state.json")
TIME_INTERVAL_HOURS = 1.0
EV_RESUME_HOUR = 22


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def _parse_dict(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value
    return parsed if isinstance(parsed, dict) else value


@dataclass
class PersistedUiState:
    alert_resolutions: dict[str, bool]
    device_ai_control: dict[str, bool]
    agent_control_enabled: bool = True


class SmartEnergyRuntime:
    """Stateful API facade over the deterministic replay/agent pipeline."""

    def __init__(self) -> None:
        self.logger = DecisionLogger()
        self.full_data = self._read_data()
        self.data = self._load_data()
        self.ui_state = self._load_ui_state()
        self.explainer: GroundedEnergyAssistant | None = None
        self.reset(clear_log=False)

    def _read_data(self) -> pd.DataFrame:
        df = pd.read_csv(INPUT_FILE)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values("Datetime").reset_index(drop=True)
        return df

    def _load_data(self, selected_date: str | None = None) -> pd.DataFrame:
        df = self.full_data
        if selected_date:
            day = pd.Timestamp(selected_date).normalize()
            window = df[(df["Datetime"] >= day) & (df["Datetime"] < day + pd.Timedelta(days=1))].copy()
            if not window.empty:
                return window.reset_index(drop=True)
        window = df[
            (df["Datetime"] >= pd.Timestamp("2017-03-15 17:00"))
            & (df["Datetime"] <= pd.Timestamp("2017-03-15 23:00"))
        ].copy()
        return (window if not window.empty else df.head(24)).reset_index(drop=True)

    def replay_options(self) -> dict[str, Any]:
        dates = self.full_data["Datetime"].dt.normalize().drop_duplicates()
        return {
            "years": sorted(dates.dt.year.unique().tolist()),
            "months": sorted(dates.dt.month.unique().tolist()),
            "dates": [value.date().isoformat() for value in dates],
            "selected_date": self.data["Datetime"].iloc[0].date().isoformat(),
        }

    def select_replay_date(self, value: str) -> dict[str, Any]:
        try:
            selected = pd.Timestamp(value).normalize()
        except Exception as exc:
            raise ValueError("Replay date must be YYYY-MM-DD") from exc
        if selected not in set(self.full_data["Datetime"].dt.normalize()):
            raise ValueError("Selected date is not available in the historical dataset")
        self.data = self._load_data(selected.date().isoformat())
        self.reset(clear_log=False)
        return self.get_state()

    def _load_ui_state(self) -> PersistedUiState:
        if UI_STATE_FILE.exists():
            payload = json.loads(UI_STATE_FILE.read_text(encoding="utf-8"))
        else:
            payload = {}
        return PersistedUiState(
            alert_resolutions=dict(payload.get("alert_resolutions", {})),
            device_ai_control=dict(payload.get("device_ai_control", {})),
            agent_control_enabled=bool(payload.get("agent_control_enabled", True)),
        )

    def _save_ui_state(self) -> None:
        UI_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        UI_STATE_FILE.write_text(json.dumps(asdict(self.ui_state), indent=2), encoding="utf-8")

    def _reset_ui_defaults(self) -> None:
        self.ui_state.alert_resolutions = {}
        self.ui_state.device_ai_control = {
            "hvac": True,
            "lighting": True,
            "ev_charging": True,
            "water_pump": True,
        }
        self.ui_state.agent_control_enabled = True
        self._save_ui_state()

    def reset(self, clear_log: bool = True) -> dict[str, Any]:
        self.data = self._load_data("2017-03-15")
        self.agent = EnergyAgent()
        self.agent.control_adapter = SimulationAdapter(self.agent.campus)
        self.index = 0
        self.overrides = {"HVAC": False, "Lighting": False, "EV": False, "Water Pump": False}
        self.environment_overrides: set[str] = set()
        self.ev_shifted = False
        self.latest_record: dict[str, Any] | None = None
        self._restore_runtime_state()
        if clear_log:
            self.logger.clear()
        self._reset_ui_defaults()
        return self.get_state()

    def _restore_runtime_state(self) -> None:
        if not RUNTIME_STATE_FILE.exists():
            return
        try:
            payload = json.loads(RUNTIME_STATE_FILE.read_text(encoding="utf-8"))
            states = payload.get("device_states", {})
            allowed_states = {
                "HVAC": {"ON", "OFF", "ECO"},
                "Lighting": {"ON", "OFF"},
                "EV Charging": {"ON", "OFF", "SHIFTED"},
                "Water Pump": {"ON", "OFF"},
            }

            if not isinstance(states, dict) or any(
                states.get(device) not in valid
                for device, valid in allowed_states.items()
            ):
                return
            self._set_device_state_directly(states)
            self._restore_device_parameters(payload.get("device_parameters", {}))
            environment = payload.get("environment")
            if isinstance(environment, dict):
                self.agent.campus.configure_environment(**environment)
            persisted_overrides = payload.get("overrides", {})
            if isinstance(persisted_overrides, dict):
                for key in self.overrides:
                    if isinstance(persisted_overrides.get(key), bool):
                        self.overrides[key] = persisted_overrides[key]
            self.ev_shifted = bool(payload.get("ev_shifted", False))
            persisted_environment_overrides = payload.get("environment_overrides", [])
            if isinstance(persisted_environment_overrides, list):
                self.environment_overrides = set(persisted_environment_overrides)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return

    def _save_runtime_state(self) -> None:
        RUNTIME_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_STATE_FILE.write_text(
            json.dumps(
                {
                    "device_states": self.agent.campus.get_state(),
                    "device_parameters": self.agent.campus.get_parameters(),
                    "environment": self.agent.campus.get_environment(),
                    "environment_overrides": sorted(self.environment_overrides),
                    "overrides": self.overrides,
                    "ev_shifted": self.ev_shifted,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _set_device_state_directly(self, states: dict[str, Any]) -> None:
        if states.get("HVAC") == "ON":
            self.agent.campus.hvac.turn_on()
        elif states.get("HVAC") == "ECO":
            self.agent.campus.hvac.set_eco()
        elif states.get("HVAC") == "OFF":
            self.agent.campus.hvac.turn_off()
        if states.get("Lighting") == "ON":
            self.agent.campus.lighting.turn_on()
        elif states.get("Lighting") == "OFF":
            self.agent.campus.lighting.turn_off()
        if states.get("EV Charging") == "ON":
            self.agent.campus.ev_charger.start_charging()
        elif states.get("EV Charging") == "OFF":
            self.agent.campus.ev_charger.stop_charging()
        elif states.get("EV Charging") == "SHIFTED":
            self.agent.campus.ev_charger.shift_charging(resume_hour=EV_RESUME_HOUR)
        if states.get("Water Pump") == "ON":
            self.agent.campus.water_pump.turn_on()
        elif states.get("Water Pump") == "OFF":
            self.agent.campus.water_pump.turn_off()

    def _restore_device_parameters(self, parameters: dict[str, Any]) -> None:
        if not isinstance(parameters, dict):
            return
        hvac = parameters.get("hvac")
        if isinstance(hvac, dict):
            self.agent.campus.hvac.configure(
                setpoint_c=hvac.get("setpoint_c"),
                ambient_c=hvac.get("ambient_c"),
                occupancy_pct=hvac.get("occupancy_pct"),
                schedule_active=hvac.get("schedule_active"),
            )
        lighting = parameters.get("lighting")
        if isinstance(lighting, dict):
            self.agent.campus.lighting.configure(
                brightness_pct=lighting.get("brightness_pct"),
                lighting_type=lighting.get("lighting_type"),
            )
        ev = parameters.get("ev_charging")
        if isinstance(ev, dict):
            if isinstance(ev.get("current_charge_pct"), (int, float)):
                self.agent.campus.ev_charger.current_charge_pct = float(ev["current_charge_pct"])
            if isinstance(ev.get("target_charge_pct"), (int, float)):
                self.agent.campus.ev_charger.target_charge_pct = float(ev["target_charge_pct"])
            if isinstance(ev.get("departure_hour"), (int, float)):
                self.agent.campus.ev_charger.departure_hour = int(ev["departure_hour"])
            if isinstance(ev.get("departure_is_day"), bool):
                self.agent.campus.ev_charger.departure_is_day = ev["departure_is_day"]
            if isinstance(ev.get("charging_mode"), str):
                self.agent.campus.ev_charger.charging_mode = ev["charging_mode"]
        pump = parameters.get("water_pump")
        if isinstance(pump, dict):
            if isinstance(pump.get("availability"), bool):
                self.agent.campus.water_pump.availability = pump["availability"]
            if isinstance(pump.get("schedule_active"), bool):
                self.agent.campus.water_pump.schedule_active = pump["schedule_active"]
            if isinstance(pump.get("moisture_pct"), (int, float)):
                self.agent.campus.water_pump.moisture_pct = float(pump["moisture_pct"])
            if isinstance(pump.get("pressure_factor"), (int, float)):
                self.agent.campus.water_pump.pressure_factor = float(pump["pressure_factor"])

    def apply_context(self, row: pd.Series, campus=None, use_overrides: bool = True) -> None:
        campus = campus or self.agent.campus
        hvac_context = {
            "ambient_c": float(row.get("Temperature", campus.environment.outdoor_temperature_c)),
            "occupancy_pct": float(row.get("Academic_Occupancy", campus.environment.occupancy_pct)),
        }
        campus.hvac.configure(
            **{
                key: value for key, value in hvac_context.items()
                if (
                    (
                        (
                            "outdoor_temperature_c"
                            if key == "ambient_c"
                            else "occupancy_pct"
                        )
                        not in self.environment_overrides
                    )
                    if use_overrides
                    else True
                )
            }
        )
        context_values = {
            "outdoor_humidity_pct": float(row.get("Outdoor_Humidity", campus.environment.outdoor_humidity_pct)),
            "indoor_temperature_c": float(row.get("Indoor_Temperature", campus.environment.indoor_temperature_c)),
            "indoor_humidity_pct": float(row.get("Indoor_Humidity", campus.environment.indoor_humidity_pct)),
        }
        campus.configure_environment(**{
            key: value for key, value in context_values.items()
            if ((key not in self.environment_overrides) if use_overrides else True)
        })
        if not use_overrides or not self.overrides["HVAC"]:
            campus.hvac.turn_on() if row["academic_hvac"] == "ON" else campus.hvac.turn_off()
        if not use_overrides or not self.overrides["Lighting"]:
            campus.lighting.turn_on() if row["academic_lighting"] == "ON" else campus.lighting.turn_off()
        if not use_overrides or not self.overrides["Water Pump"]:
            campus.water_pump.turn_on() if row["pump_state"] == "ON" else campus.water_pump.turn_off()
        if not use_overrides or not self.ev_shifted:
            if not use_overrides or not self.overrides["EV"]:
                campus.ev_charger.start_charging() if row["ev_charging"] == "ON" else campus.ev_charger.stop_charging()

    def process_scheduled_devices(self, row: pd.Series) -> bool:
        current_hour = int(pd.Timestamp(row["Datetime"]).hour)
        if self.ev_shifted and current_hour >= EV_RESUME_HOUR:
            self.agent.campus.ev_charger.start_charging()
            self.ev_shifted = False
            return True
        return False

    def record_override(self, action: dict[str, Any]) -> None:
        action_name = action["action"]
        if action_name in ("Reduce Academic HVAC", "Turn Academic HVAC OFF"):
            self.overrides["HVAC"] = True
        elif action_name == "Turn Academic Lighting OFF":
            self.overrides["Lighting"] = True
        elif action_name == "Shift EV Charging":
            self.ev_shifted = True
        self._save_runtime_state()

    def _action_device_id(self, action_name: str) -> str | None:
        if "HVAC" in action_name:
            return "hvac"
        if "Lighting" in action_name:
            return "lighting"
        if "EV" in action_name:
            return "ev_charging"
        if "Water Pump" in action_name:
            return "water_pump"
        return None

    def execute_current_decision(self) -> dict[str, Any]:
        """Apply the current evidence-backed decision without advancing replay."""
        row = self.current_row()
        self.apply_context(row)
        state = self.agent.observe(row)
        decision = self.agent.decide(state)
        action = decision["action"]
        load_before = self.agent.get_campus_load()
        execution = self._execute_agent_action(action, state)
        load_after = self.agent.get_campus_load()
        record = self._build_record(
            state,
            decision,
            execution,
            load_before,
            load_after,
            False,
        )
        self.logger.log(record)
        self.latest_record = record
        self._save_runtime_state()
        return self._serialize_cycle(state, decision, execution, True)

    def _execute_agent_action(self, action: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        action_name = action.get("action", "Do Nothing")
        device_id = self._action_device_id(action_name)
        if device_id and not self.ui_state.agent_control_enabled:
            validation = self.agent.constraints.check(action, state)
            return {
                "status": "NOT_EXECUTED",
                "message": "Agent Control is OFF; recommendation only.",
                "verification": {"matched": True, "status": "NOT_REQUIRED"},
                "validation": validation,
                "control_origin": "AGENT_RECOMMENDATION_ONLY",
            }
        if device_id and not self.ui_state.device_ai_control.get(device_id, True):
            validation = self.agent.constraints.check(action, state)
            return {
                "status": "NOT_EXECUTED",
                "message": "AI Control is disabled for this device; recommendation only.",
                "verification": {"matched": True, "status": "NOT_REQUIRED"},
                "validation": validation,
                "control_origin": "AGENT_RECOMMENDATION_ONLY",
            }
        return self.agent.execute(action)

    DEVICE_DEFINITIONS = {
        "hvac": {"state_key": "HVAC", "states": {"ON", "OFF", "ECO"}},
        "lighting": {"state_key": "Lighting", "states": {"ON", "OFF"}},
        "ev_charging": {"state_key": "EV", "states": {"ON", "OFF", "SHIFTED"}},
        "water_pump": {"state_key": "Water Pump", "states": {"ON", "OFF"}},
    }
    PARAMETER_DEFINITIONS = {
        "hvac": {"setpoint_c": (16.0, 20.0), "ambient_c": (-40.0, 60.0), "occupancy_pct": (0.0, 100.0)},
        "lighting": {"brightness_pct": (0.0, 100.0), "lighting_type": ("warm", "cool", "standard")},
        "ev_charging": {"current_charge_pct": (0.0, 100.0), "target_charge_pct": (0.0, 100.0), "departure_hour": (0.0, 23.0), "departure_is_day": (False, True), "charging_mode": ("standard", "eco", "fast")},
        "water_pump": {"moisture_pct": (0.0, 100.0), "pressure_factor": (0.1, 3.0), "schedule_active": (False, True)},
    }

    def set_device_parameters(self, device_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if device_id not in self.PARAMETER_DEFINITIONS:
            raise KeyError(device_id)
        if not isinstance(parameters, dict) or not parameters:
            raise ValueError("At least one device parameter is required")
        allowed = self.PARAMETER_DEFINITIONS[device_id]
        unknown = set(parameters) - set(allowed)
        if unknown:
            raise ValueError(f"Unsupported parameter(s): {', '.join(sorted(unknown))}")
        normalized: dict[str, Any] = {}
        for name, value in parameters.items():
            lower, upper = allowed[name]
            if isinstance(lower, str):
                if not isinstance(value, str) or value not in allowed[name]:
                    raise ValueError(f"{name} must be one of {', '.join(allowed[name])}")
                normalized[name] = value
            elif isinstance(lower, bool):
                if not isinstance(value, bool):
                    raise ValueError(f"{name} must be a boolean")
                normalized[name] = value
            else:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"{name} must be numeric")
                if not lower <= float(value) <= upper:
                    raise ValueError(f"{name} must be between {lower} and {upper}")
                normalized[name] = float(value)
        action = {"action": "USER_SIMULATED_PARAMETER_CONTROL", "device_id": device_id, "parameters": normalized}
        execution = self.agent.control_adapter.execute(action, mode="simulated")
        if execution.status.value != "SIMULATED" or not execution.verification.get("matched", False):
            raise RuntimeError("Simulated parameter control failed verification")
        self._save_runtime_state()
        timestamp = execution.timestamp.isoformat()
        self.logger.log({
            "Datetime": timestamp,
            "Decision_Timestamp": timestamp,
            "Decision_State": "user_simulated_parameter_control",
            "Candidate_Action": "USER_SIMULATED_PARAMETER_CONTROL",
            "Selected_Action": f"{device_id}:parameters",
            "Action": f"{device_id}:parameters",
            "Control_Origin": "USER_SIMULATED_CONTROL",
            "Execution_Status": "SIMULATED",
            "Verification_Status": "VERIFIED",
            "Validation_Status": "PASSED",
            "Safety_Status": "SIMULATED_CONTROL_VALIDATED",
            "Execution_Provenance": "SIMULATED",
            "Execution_Mode": "SIMULATED",
            "Load_Before_MW": execution.load_before_MW,
            "Load_After_MW": execution.load_after_MW,
            "Provenance": "SIMULATED",
            "Impact_Semantics": "user-requested simulated parameter change; not real control",
            "Audit_Logged_At": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        device = next(item for item in self.devices() if item["id"] == device_id)
        device.update({
            "controlOrigin": "USER_SIMULATED_CONTROL",
            "executionStatus": "SIMULATED",
            "provenance": "SIMULATED",
            "parameters": self.agent.campus.get_parameters()[device_id],
        })
        return {
            "mode": "SIMULATED",
            "device": device,
            "execution": {
                "status": "SIMULATED",
                "control_origin": "USER_SIMULATED_CONTROL",
                "verification": execution.verification,
                "timestamp": timestamp,
                "provenance": "SIMULATED",
                "message": "No physical device command was sent.",
            },
        }

    def set_device_state(self, device_id: str, requested_state: str) -> dict[str, Any]:
        definition = self.DEVICE_DEFINITIONS.get(device_id)
        if definition is None:
            raise KeyError(device_id)
        if requested_state not in definition["states"]:
            raise ValueError(f"Invalid state '{requested_state}' for {device_id}")

        action = {
            "action": "USER_SIMULATED_CONTROL",
            "device_id": device_id,
            "state": requested_state,
            "control_origin": "USER_SIMULATED_CONTROL",
        }
        execution = self.agent.control_adapter.execute(action, mode="simulated")
        execution_status = execution.status.value
        if execution_status != "SIMULATED" or not execution.verification.get("matched", False):
            raise RuntimeError("Simulated device control failed verification")

        self.overrides[definition["state_key"]] = True
        if device_id == "ev_charging":
            self.ev_shifted = requested_state == "SHIFTED"
        self._save_runtime_state()
        timestamp = execution.timestamp.isoformat()
        record = {
            "Datetime": timestamp,
            "Decision_Timestamp": timestamp,
            "Decision_State": "user_simulated_control",
            "Candidate_Action": "USER_SIMULATED_CONTROL",
            "Selected_Action": f"{device_id}:{requested_state}",
            "Action": f"{device_id}:{requested_state}",
            "Control_Origin": "USER_SIMULATED_CONTROL",
            "Execution_Status": execution_status,
            "Verification_Status": "VERIFIED",
            "Validation_Status": "PASSED",
            "Safety_Status": "SIMULATED_CONTROL_VALIDATED",
            "Execution_Mode": "SIMULATED",
            "Execution_Provenance": "SIMULATED",
            "Load_Before_MW": execution.load_before_MW,
            "Load_After_MW": execution.load_after_MW,
            "Peak_Reduction_MW": max(execution.load_before_MW - execution.load_after_MW, 0.0),
            "Interval_Energy_Impact_MWh": max(execution.load_before_MW - execution.load_after_MW, 0.0),
            "Provenance": "SIMULATED",
            "Impact_Semantics": "user-requested simulated device state change; not real control",
            "Audit_Logged_At": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.logger.log(record)
        device = next(item for item in self.devices() if item["id"] == device_id)
        device.update(
            {
                "state": device["rawState"],
                "timestamp": timestamp,
                "executionStatus": execution_status,
                "execution_status": execution_status,
                "executionTimestamp": timestamp,
                "controlOrigin": "USER_SIMULATED_CONTROL",
                "provenance": "SIMULATED",
            }
        )
        return {
            "mode": "SIMULATED",
            "device": device,
            "execution": {
                "status": execution_status,
                "control_origin": "USER_SIMULATED_CONTROL",
                "verification": execution.verification,
                "timestamp": timestamp,
                "provenance": "SIMULATED",
                "message": "No physical device command was sent.",
            },
        }

    def current_row(self) -> pd.Series:
        return self.data.iloc[self.index]

    def preview_decision(self) -> dict[str, Any]:
        row = self.current_row()
        replay_agent = EnergyAgent()
        replay_agent.control_adapter = SimulationAdapter(replay_agent.campus)
        self.apply_context(row, replay_agent.campus, use_overrides=False)
        state = replay_agent.observe(row)
        decision = replay_agent.decide(state)
        return self._serialize_cycle(state, decision, None, False)

    def step(self) -> dict[str, Any]:
        virtual_snapshot = {
            "states": self.agent.campus.get_state(),
            "parameters": self.agent.campus.get_parameters(),
            "environment": self.agent.campus.get_environment(),
        }
        row = self.current_row()
        try:
            self.apply_context(row)
            resumed = self.process_scheduled_devices(row)
            state = self.agent.observe(row)
            load_before = self.agent.get_campus_load()
            decision = self.agent.decide(state)
            action = decision["action"]
            execution = self._execute_agent_action(action, state)
            if execution.get("status") == "SUCCESS":
                self.record_override(action)
            load_after = self.agent.get_campus_load()
            record = self._build_record(state, decision, execution, load_before, load_after, resumed)
            self.logger.log(record)
            self.latest_record = record
            self.index = min(self.index + 1, len(self.data) - 1)
        finally:
            self._set_device_state_directly(virtual_snapshot["states"])
            self._restore_device_parameters(virtual_snapshot["parameters"])
            self.agent.campus.configure_environment(**virtual_snapshot["environment"])
            self._save_runtime_state()
        return self.get_state()

    def _build_record(
        self,
        state: dict[str, Any],
        decision: dict[str, Any],
        execution: dict[str, Any],
        load_before: float,
        load_after: float,
        resumed: bool,
    ) -> dict[str, Any]:
        action = decision["action"]
        action_name = action["action"]
        validation = execution.get("validation") or self.agent.constraints.check(action, state)
        verification = execution.get("verification", {}) or {}
        execution_status = execution.get("status", "FAILED")
        verification_status = verification.get("status") or (
            "VERIFIED" if verification.get("matched") else "FAILED_UNVERIFIED"
        )
        if action_name == "Do Nothing":
            decision_state = "do_nothing"
            constraint_status = "NOT_APPLICABLE"
            execution_status = "NO_ACTION"
            verification_status = "NOT_REQUIRED"
        elif not validation.get("allowed", True):
            decision_state = "constraint_rejected"
            constraint_status = "REJECTED"
            execution_status = "NOT_EXECUTED"
            verification_status = "NOT_REQUIRED"
        elif execution_status == "SUCCESS":
            decision_state = "verified"
            constraint_status = "PASSED"
        else:
            decision_state = "failed_unverified"
            constraint_status = "PASSED"

        forecast = state.get("Forecast") or {}
        peak_reduction = max(load_before - load_after, 0.0)
        energy_before = load_before * TIME_INTERVAL_HOURS
        energy_after = load_after * TIME_INTERVAL_HOURS
        energy_reduction = max(energy_before - energy_after, 0.0)
        last_exec = getattr(self.agent, "_last_exec_result", None)

        return {
            "Datetime": state["Datetime"],
            "Decision_Timestamp": state["Datetime"],
            "Decision_State": decision_state,
            "Candidate_Action": action_name,
            "Selected_Action": action_name,
            "Constraint_Status": constraint_status,
            "Constraint_Passed": constraint_status == "PASSED",
            "What_If_Estimated_Impact_MW": float(action.get("estimated_saving_MW", 0.0)),
            "Opportunity": decision["opportunity"]["type"],
            "Severity": decision["opportunity"]["severity"],
            "Opportunity_Reason": decision["opportunity"]["reason"],
            "Action": action_name,
            "Control_Origin": execution.get("control_origin", "AGENT_SIMULATED_EXECUTION"),
            "Execution_Status": execution_status,
            "Verification_Status": verification_status,
            "Validation_Status": validation.get("validation_status"),
            "Safety_Status": validation.get("safety_status"),
            "Rejection_Reason": validation.get("reason") if not validation.get("allowed", True) else None,
            "Rule_ID": validation.get("rule_id"),
            "Execution_Provenance": "SIMULATED",
            "Execution_Mode": "SIMULATED",
            "Exec_Timestamp": getattr(last_exec, "timestamp", None),
            "Exec_Load_Before_MW": getattr(last_exec, "load_before_MW", None),
            "Exec_Load_After_MW": getattr(last_exec, "load_after_MW", None),
            "Exec_Simulated_Impact_MW": getattr(last_exec, "simulated_impact_MW", None),
            "Exec_Verification": verification,
            "Execution_Provenance_Metadata": getattr(last_exec, "provenance_metadata", None),
            "Load_Before_MW": load_before,
            "Load_After_MW": load_after,
            "Peak_Reduction_MW": peak_reduction,
            "Interval_Energy_Impact_MWh": energy_reduction,
            "Energy_Before_MWh": energy_before,
            "Energy_After_MWh": energy_after,
            "Energy_Reduction_MWh": energy_reduction,
            "Impact_Semantics": (
                "current-period EV demand shift; not permanent energy savings"
                if action_name == "Shift EV Charging"
                else "simulated interval load impact"
            ),
            "Audit_Logged_At": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Forecast_Datetime": forecast.get("forecast_timestamp"),
            "Forecast_MW": forecast.get("forecast_MW"),
            "Campus_Demand_MW": state["Campus_Demand_MW"],
            "Campus_Baseline_MW": state["Campus_Baseline_MW"],
            "Campus_Deviation_MW": state["Campus_Deviation_MW"],
            "Reference_Demand_MW": state["Reference_Demand_MW"],
            "Occupancy": state["Academic_Occupancy"],
            "Temperature_C": state["Temperature"],
            "Tariff": state["Tariff"],
            "Provenance": "SIMULATED",
            "Feedback_State": self.agent.campus.get_state(),
            "EV_Resumed": resumed,
            "Provenance_Metadata": make_provenance(
                "SIMULATED",
                "SmartEnergyRuntime",
                str(INPUT_FILE),
                data_timestamp_start=pd.Timestamp(state["Datetime"]).isoformat(),
                data_timestamp_end=pd.Timestamp(state["Datetime"]).isoformat(),
                units={
                    "Campus_Demand_MW": "MW",
                    "Reference_Demand_MW": "MW regional reference",
                    "Forecast_MW": "MW derived",
                    "Load_Before_MW": "MW simulated",
                    "Load_After_MW": "MW simulated",
                    "Interval_Energy_Impact_MWh": "MWh simulated",
                },
                geographic_scope="virtual campus replay; AEP reference remains regional/grid-level",
                semantic_description="API replay decision record over deterministic backend outputs.",
                transformation="observe -> decide -> simulated execute -> verify -> log",
                lineage=[state["Provenance_Metadata"]],
                metadata={"execution_mode": "SIMULATED"},
            ),
        }

    def _serialize_cycle(
        self,
        state: dict[str, Any],
        decision: dict[str, Any],
        execution: dict[str, Any] | None,
        include_execution: bool,
    ) -> dict[str, Any]:
        action = decision["action"]
        actual_load = float(state.get("Campus_Demand_MW", 0.0))
        expected_load = float((state.get("Forecast") or {}).get("forecast_MW", actual_load))
        optimal_load = float(action.get("simulated_demand_MW", actual_load))
        return _jsonable(
            {
                "state": state,
                "decision": decision,
                "execution": execution,
                "include_execution": include_execution,
                "selected_action": action["action"],
                "what_if_impact_MW": action.get("estimated_saving_MW", 0.0),
                "comparison": {
                    "actual_simulated_load_MW": actual_load,
                    "expected_forecast_load_MW": expected_load,
                    "expected_device_demand_MW": state.get("Expected_Device_Demand_MW"),
                    "optimal_action_load_MW": optimal_load,
                    "actual_provenance": "SIMULATED",
                    "expected_provenance": "DERIVED",
                    "optimal_provenance": "DERIVED",
                    "optimal_semantics": "deterministic what-if result, not a second forecast",
                },
                "evidence": {
                    "trigger": decision["opportunity"],
                    "observed_state": state.get("Actual_Device_State"),
                    "forecast": state.get("Forecast"),
                    "device_predictions": state.get("Device_Predictions"),
                    "candidate_action": action,
                    "what_if": action,
                    "constraints_checked": decision.get("action_validations"),
                    "constraints_passed": decision.get("selected_validation"),
                    "model_quality": action.get("prediction_quality"),
                    "provenance": "DERIVED",
                    "execution": execution,
                },
                "provenance": "DERIVED",
            }
        )

    def get_state(self) -> dict[str, Any]:
        preview = self.preview_decision()
        history = self.decision_history()
        return {
            "mode": "SIMULATED",
            "replay": {
                "step": self.index,
                "total_steps": len(self.data),
                "timestamp": _jsonable(self.current_row()["Datetime"]),
                "source_timestamp": _jsonable(self.current_row()["Datetime"]),
                "simulated_timestamp": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(hours=self.index)
                ).isoformat(),
                "timeline_label": "Current simulated timeline; replay source timestamps are historical inputs",
                "playing_supported": False,
                "options": self.replay_options(),
            },
            "current": preview,
            "devices": self.devices(),
            "decisions": history,
            "analytics": self.analytics(history),
            "alerts": self.alerts(history),
            "provenance": {
                "campus": "SIMULATED",
                "execution": "SIMULATED",
                "aep": "REAL_HISTORICAL",
                "forecast": "DERIVED",
                "analytics": "DERIVED",
            },
            "agent_control_enabled": self.ui_state.agent_control_enabled,
            "environment": self.agent.campus.get_environment(),
        }

    def devices(self) -> list[dict[str, Any]]:
        state = self.agent.campus.get_state()
        loads = self.agent.campus.get_load_breakdown()
        predictions = self.agent.campus.get_device_predictions()
        definitions = [
            ("hvac", "Academic HVAC", "Climate Control", state["HVAC"], loads["HVAC_MW"], "Fan"),
            ("lighting", "Academic Lighting", "Lighting", state["Lighting"], loads["Lighting_MW"], "Lightbulb"),
            ("ev_charging", "EV Charging", "EV Charging", state["EV Charging"], loads["EV_MW"], "Car"),
            ("water_pump", "Water Pump", "Utility", state["Water Pump"], loads["Water_Pump_MW"], "Droplets"),
        ]
        return [
            {
                "id": device_id,
                "name": name,
                "type": kind,
                "status": "Shifted" if raw_state == "SHIFTED" else ("Active" if raw_state in ("ON", "ECO") else "Idle"),
                "rawState": raw_state,
                "power": load,
                "expectedPower": predictions[device_id]["predicted_power_mw"],
                "expectedPowerUnit": predictions[device_id]["unit"],
                "optimalPower": predictions[device_id]["predicted_power_mw"],
                "optimalPowerUnit": predictions[device_id]["unit"],
                "actualPower": load,
                "actualPowerUnit": "MW",
                "deviceModel": {
                    "id": predictions[device_id]["model_id"],
                    "status": predictions[device_id]["model_status"],
                    "provenance": predictions[device_id]["provenance"],
                    "source": predictions[device_id]["source"],
                    "fallbackUsed": predictions[device_id]["fallback_used"],
                    "metadata": predictions[device_id]["metadata"],
                },
                "unit": "MW",
                "aiControl": self.ui_state.device_ai_control.get(device_id, True),
                "lastUpdated": _jsonable(self.current_row()["Datetime"]),
                "loadFactor": (
                    "outdoor temperature, humidity, indoor setpoint, and occupancy"
                    if device_id == "hvac"
                    else "brightness and occupancy context"
                    if device_id == "lighting"
                    else "charge target and scheduled availability"
                    if device_id == "ev_charging"
                    else "availability and schedule"
                ),
                "description": f"{name} state is read from the SIMULATED VirtualCampus, not a real device API.",
                "provenance": "SIMULATED",
                "icon": icon,
                "parameters": self.agent.campus.get_parameters()[device_id],
                "capabilities": (
                    ["state", "setpoint_c", "occupancy_pct"]
                    if device_id == "hvac"
                    else ["state", "brightness_pct"]
                    if device_id == "lighting"
                    else ["state"]
                ),
            }
            for device_id, name, kind, raw_state, load, icon in definitions
        ]

    def set_device_ai_control(self, device_id: str, enabled: bool) -> dict[str, Any]:
        valid_ids = {device["id"] for device in self.devices()}
        if device_id not in valid_ids:
            raise KeyError(device_id)
        self.ui_state.device_ai_control[device_id] = bool(enabled)
        self._save_ui_state()
        return next(device for device in self.devices() if device["id"] == device_id)

    def set_agent_control(self, enabled: bool) -> dict[str, Any]:
        self.ui_state.agent_control_enabled = bool(enabled)
        self._save_ui_state()
        return {
            "mode": "SIMULATED",
            "agent_control_enabled": self.ui_state.agent_control_enabled,
            "message": (
                "Safe recommendations may execute in the VirtualCampus simulation."
                if enabled
                else "Recommendations remain visible; no agent action will execute."
            ),
        }

    def set_environment(self, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict) or not values:
            raise ValueError("At least one environmental input is required")
        self.agent.campus.configure_environment(**values)
        self.environment_overrides.update(values)
        self._save_runtime_state()
        return {"mode": "SIMULATED", "environment": self.agent.campus.get_environment()}

    def decision_history(self) -> list[dict[str, Any]]:
        log = self.logger.read()
        if log.empty:
            return []
        sort_column = "Audit_Logged_At" if "Audit_Logged_At" in log.columns else "Decision_Timestamp"
        records = log.sort_values(sort_column, ascending=False, na_position="last").to_dict(orient="records")
        for record in records:
            record["Exec_Verification"] = _parse_dict(record.get("Exec_Verification"))
            record["Feedback_State"] = _parse_dict(record.get("Feedback_State"))
            record["Provenance_Metadata"] = _parse_dict(record.get("Provenance_Metadata"))
        return _jsonable(records)

    def analytics(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        current = self.agent.campus.get_load_breakdown()
        total_peak = sum(float(item.get("Peak_Reduction_MW") or 0) for item in history)
        total_energy = sum(float(item.get("Energy_Reduction_MWh") or 0) for item in history)
        selected_day = pd.Timestamp(self.current_row()["Datetime"]).normalize()
        historical_rows = self.full_data[
            (self.full_data["Datetime"] >= selected_day)
            & (self.full_data["Datetime"] < selected_day + pd.Timedelta(days=1))
        ]
        historical_timeline = [
            {
                "time": row["Datetime"],
                "referenceDemandMW": row["reference_system_demand_MW"],
                "forecastMW": None,
                "provenance": "REAL_HISTORICAL",
            }
            for _, row in historical_rows.iterrows()
        ]
        for point in historical_timeline:
            point["time"] = _jsonable(point["time"])
        return {
            "currentLoadMW": current["Total_MW"],
            "deviceContribution": [
                {"name": "Academic HVAC", "value": current["HVAC_MW"], "provenance": "SIMULATED"},
                {"name": "Academic Lighting", "value": current["Lighting_MW"], "provenance": "SIMULATED"},
                {"name": "EV Charging", "value": current["EV_MW"], "provenance": "SIMULATED"},
                {"name": "Water Pump", "value": current["Water_Pump_MW"], "provenance": "SIMULATED"},
            ],
            "totalPeakReductionMW": total_peak,
            "totalEnergyImpactMWh": total_energy,
            "timeline": historical_timeline,
            "decisionTimeline": [
                {
                    "time": item.get("Datetime"),
                    "loadBeforeMW": item.get("Load_Before_MW"),
                    "loadAfterMW": item.get("Load_After_MW"),
                    "forecastMW": item.get("Forecast_MW"),
                    "referenceDemandMW": item.get("Reference_Demand_MW"),
                    "impactMWh": item.get("Interval_Energy_Impact_MWh"),
                }
                for item in reversed(history)
            ],
            "provenance": "DERIVED",
        }

    def alerts(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for item in history:
            timestamp = str(item.get("Decision_Timestamp") or item.get("Datetime"))
            if item.get("Severity") in ("High", "Medium"):
                alert_id = f"opportunity:{timestamp}:{item.get('Opportunity')}"
                alerts.append(
                    {
                        "id": alert_id,
                        "severity": "high" if item.get("Severity") == "High" else "warning",
                        "title": item.get("Opportunity"),
                        "description": item.get("Opportunity_Reason"),
                        "time": timestamp,
                        "resolved": self.ui_state.alert_resolutions.get(alert_id, False),
                        "provenance": "DERIVED",
                    }
                )
            if item.get("Execution_Status") == "SUCCESS":
                alert_id = f"execution:{timestamp}:{item.get('Action')}"
                alerts.append(
                    {
                        "id": alert_id,
                        "severity": "optimized",
                        "title": "Simulated action verified",
                        "description": (
                            f"{item.get('Action')} reduced simulated load by "
                            f"{item.get('Peak_Reduction_MW')} MW."
                        ),
                        "time": timestamp,
                        "resolved": self.ui_state.alert_resolutions.get(alert_id, True),
                        "provenance": "SIMULATED",
                    }
                )
            if item.get("Constraint_Status") == "REJECTED" or item.get("Verification_Status") == "FAILED_UNVERIFIED":
                alert_id = f"safety:{timestamp}:{item.get('Action')}"
                alerts.append(
                    {
                        "id": alert_id,
                        "severity": "high",
                        "title": "Safety or verification issue",
                        "description": item.get("Rejection_Reason") or "Verification did not match expected simulated readback.",
                        "time": timestamp,
                        "resolved": self.ui_state.alert_resolutions.get(alert_id, False),
                        "provenance": "DERIVED",
                    }
                )
        return alerts

    def resolve_alert(self, alert_id: str) -> dict[str, Any]:
        self.ui_state.alert_resolutions[alert_id] = True
        self._save_ui_state()
        return {"id": alert_id, "resolved": True}

    def explain(self, question: str) -> dict[str, Any]:
        execution = None
        what_if = None
        lowered = question.strip().lower()
        if lowered in {"do it", "execute", "apply action", "apply it"}:
            preview = self.preview_decision()
            pending_action = preview.get("decision", {}).get("action", {})
            if pending_action.get("action") in (None, "Do Nothing"):
                context = self.get_state()
                context["execution_intent_unavailable"] = (
                    "There is no immediately actionable recommendation in the current context."
                )
            else:
                result = self.execute_current_decision()
                execution = result.get("execution")
        elif "what if" in lowered or "what happens if" in lowered:
            row = self.current_row()
            self.apply_context(row)
            action_name = None
            if "hvac" in lowered and ("eco" in lowered or "reduce" in lowered):
                action_name = "Reduce Academic HVAC"
            elif "pump" in lowered and ("off" in lowered or "stop" in lowered):
                action_name = "Turn Water Pump OFF"
            if action_name:
                what_if = self.agent.what_if.simulate(
                    self.agent.campus,
                    {"action": action_name},
                    timestamp=pd.Timestamp(row["Datetime"]),
                )
        context = self.get_state()
        if execution is not None:
            context["latest_execution"] = execution
        if what_if is not None:
            context["what_if_result"] = what_if
        if self.explainer is None:
            try:
                self.explainer = build_groq_assistant()
            except Exception:
                self.explainer = GroundedEnergyAssistant()
        answer = self.explainer.answer(question, context)
        if execution is not None:
            answer["execution"] = execution
        return answer


runtime = SmartEnergyRuntime()
