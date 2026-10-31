from __future__ import annotations

import datetime
from typing import Dict, Any

from adapters.control_adapter import ControlAdapter, ExecResult, ExecutionStatus
from data.provenance import make_provenance


class SimulationAdapter(ControlAdapter):
    """Adapter that delegates execution to the existing VirtualCampus simulation.

    Execution is always SIMULATED. Verification reads back the simulated
    device state after performing the action.
    """

    def __init__(self, campus):
        self.campus = campus

    def execute(self, action: Dict[str, Any], mode: str = "simulated") -> ExecResult:

        assert mode == "simulated", "SimulationAdapter only supports simulated mode"

        load_before = float(self.campus.get_total_load())

        action_name = action.get("action")

        raw_response = None
        control_origin = action.get("control_origin", "AGENT_SIMULATED_EXECUTION")

        if action_name == "USER_SIMULATED_CONTROL":
            device_id = action.get("device_id")
            requested_state = action.get("state")
            if device_id == "hvac":
                raw_response = (
                    self.campus.hvac.turn_on()
                    if requested_state == "ON"
                    else self.campus.hvac.turn_off()
                    if requested_state == "OFF"
                    else self.campus.hvac.set_eco()
                )
            elif device_id == "lighting":
                raw_response = (
                    self.campus.lighting.turn_on()
                    if requested_state == "ON"
                    else self.campus.lighting.turn_off()
                )
            elif device_id == "ev_charging":
                raw_response = (
                    self.campus.ev_charger.start_charging()
                    if requested_state == "ON"
                    else self.campus.ev_charger.stop_charging()
                    if requested_state == "OFF"
                    else self.campus.ev_charger.shift_charging(resume_hour=22)
                )
            elif device_id == "water_pump":
                raw_response = (
                    self.campus.water_pump.turn_on()
                    if requested_state == "ON"
                    else self.campus.water_pump.turn_off()
                )
            else:
                raw_response = "Unknown simulated device"
            load_after = float(self.campus.get_total_load())
            exec_result = ExecResult(
                action=action_name,
                status=ExecutionStatus.SIMULATED,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                load_before_MW=load_before,
                load_after_MW=load_after,
                simulated_impact_MW=load_before - load_after,
                raw_response={
                    "message": raw_response,
                    "device_id": device_id,
                    "state": requested_state,
                    "control_origin": control_origin,
                },
                verification={},
                provenance_metadata=make_provenance(
                    "SIMULATED",
                    "SimulationAdapter",
                    "VirtualCampus",
                    units={"load_before_MW": "MW", "load_after_MW": "MW"},
                    geographic_scope="virtual campus; not live telemetry",
                    semantic_description="User-requested simulated device state change.",
                    transformation="validated simulated control through the control adapter",
                    metadata={"control_origin": control_origin},
                ),
            )
            exec_result.verification = self.verify(exec_result)
            if not exec_result.verification.get("matched", False):
                exec_result.status = ExecutionStatus.NOT_EXECUTED
                exec_result.verification["status"] = "FAILED_UNVERIFIED"
            return exec_result

        if action_name == "USER_SIMULATED_PARAMETER_CONTROL":
            device_id = action.get("device_id")
            parameters = action.get("parameters", {})
            if device_id == "hvac":
                raw_response = self.campus.hvac.configure(**parameters)
            elif device_id == "lighting":
                raw_response = self.campus.lighting.configure(**parameters)
            elif device_id == "ev_charging":
                if "current_charge_pct" in parameters:
                    self.campus.ev_charger.current_charge_pct = float(parameters["current_charge_pct"])
                if "target_charge_pct" in parameters:
                    self.campus.ev_charger.target_charge_pct = float(parameters["target_charge_pct"])
                if "departure_hour" in parameters:
                    self.campus.ev_charger.departure_hour = int(parameters["departure_hour"])
                if "departure_is_day" in parameters:
                    self.campus.ev_charger.departure_is_day = bool(parameters["departure_is_day"])
                if "charging_mode" in parameters:
                    self.campus.ev_charger.charging_mode = str(parameters["charging_mode"])
                raw_response = "EV charging parameters updated."
            elif device_id == "water_pump":
                if "schedule_active" in parameters:
                    self.campus.water_pump.schedule_active = bool(parameters["schedule_active"])
                if "moisture_pct" in parameters:
                    self.campus.water_pump.moisture_pct = float(parameters["moisture_pct"])
                if "pressure_factor" in parameters:
                    self.campus.water_pump.pressure_factor = float(parameters["pressure_factor"])
                raw_response = "Water pump parameters updated."
            else:
                raw_response = "Unknown simulated device"
            load_after = float(self.campus.get_total_load())
            exec_result = ExecResult(
                action=action_name,
                status=ExecutionStatus.SIMULATED,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                load_before_MW=load_before,
                load_after_MW=load_after,
                simulated_impact_MW=load_before - load_after,
                raw_response={"message": raw_response, "device_id": device_id, "parameters": parameters},
                verification={},
                provenance_metadata=make_provenance(
                    "SIMULATED",
                    "SimulationAdapter",
                    "VirtualCampus",
                    units={"load_before_MW": "MW", "load_after_MW": "MW"},
                    geographic_scope="virtual campus; not live telemetry",
                    semantic_description="User-requested simulated device parameter change.",
                    transformation="validated simulated parameter control through the control adapter",
                ),
            )
            exec_result.verification = self.verify(exec_result)
            if not exec_result.verification.get("matched", False):
                exec_result.status = ExecutionStatus.NOT_EXECUTED
                exec_result.verification["status"] = "FAILED_UNVERIFIED"
            return exec_result

        # Map to existing agent.execute behaviors
        if action_name == "Reduce Academic HVAC":
            raw_response = self.campus.hvac.set_eco()
        elif action_name == "Turn Academic HVAC OFF":
            raw_response = self.campus.hvac.turn_off()
        elif action_name == "Turn Academic Lighting OFF":
            raw_response = self.campus.lighting.turn_off()
        elif action_name == "Shift EV Charging":
            raw_response = self.campus.ev_charger.shift_charging(resume_hour=22)
        elif action_name == "Turn Water Pump OFF":
            raw_response = self.campus.water_pump.turn_off()
        elif action_name == "Do Nothing":
            raw_response = "No action"
            load_after = load_before
            exec_result = ExecResult(
                action=action_name,
                status=ExecutionStatus.NOT_EXECUTED,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                load_before_MW=load_before,
                load_after_MW=load_after,
                simulated_impact_MW=0.0,
                raw_response={"message": "No action required."},
                verification={"matched": True, "reason": "no action required", "status": "NOT_REQUIRED"},
                provenance_metadata=make_provenance(
                    "SIMULATED",
                    "SimulationAdapter",
                    "VirtualCampus",
                    units={"load_before_MW": "MW", "load_after_MW": "MW"},
                    geographic_scope="virtual campus; not live telemetry",
                    semantic_description="No-op action recorded in the virtual campus simulation.",
                    transformation="simulated execution boundary; no real control",
                ),
            )
            return exec_result
        else:
            return ExecResult(
                action=action_name,
                status=ExecutionStatus.NOT_EXECUTED,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                load_before_MW=load_before,
                load_after_MW=load_before,
                simulated_impact_MW=0.0,
                raw_response={"message": "Unknown action"},
                verification={"matched": False, "reason": "unknown action", "status": "FAILED_UNVERIFIED"},
                provenance_metadata=make_provenance(
                    "SIMULATED",
                    "SimulationAdapter",
                    "VirtualCampus",
                    units={"load_before_MW": "MW", "load_after_MW": "MW"},
                    geographic_scope="virtual campus; not live telemetry",
                    semantic_description="Rejected action recorded by the virtual campus simulation.",
                    transformation="simulated execution boundary; no real control",
                ),
            )

        load_after = float(self.campus.get_total_load())

        impact = max(load_before - load_after, 0.0)

        exec_result = ExecResult(
            action=action_name,
            status=ExecutionStatus.SIMULATED,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            load_before_MW=load_before,
            load_after_MW=load_after,
            simulated_impact_MW=impact,
            raw_response=raw_response,
            verification={},
            provenance_metadata=make_provenance(
                "SIMULATED",
                "SimulationAdapter",
                "VirtualCampus",
                units={
                    "load_before_MW": "MW",
                    "load_after_MW": "MW",
                    "simulated_impact_MW": "MW",
                },
                geographic_scope="virtual campus; not live telemetry",
                semantic_description="Simulated device action and readback result.",
                transformation="virtual device mutation followed by simulated verification",
                metadata={"execution_mode": "SIMULATED", "read_only_external_data": True},
            ),
        )

        # perform verification readback
        exec_result.verification = self.verify(exec_result)

        # A simulated execution is only considered successful when the readback
        # matches the expected post-action state. Verification mismatches are
        # treated as failed/unverified and must not be reported as successful.
        if not exec_result.verification.get("matched", False):
            exec_result.status = ExecutionStatus.NOT_EXECUTED
            exec_result.verification["status"] = "FAILED_UNVERIFIED"

        return exec_result

    def verify(self, exec_result: ExecResult, timeout: int = 5) -> Dict[str, Any]:

        # Read simulated device state and compute observed load
        state = self.campus.get_state()
        observed_load = float(self.campus.get_total_load())

        matched = abs(observed_load - exec_result.load_after_MW) < 1e-6

        return {
            "matched": matched,
            "observed_load_MW": observed_load,
            "state": state,
        }
