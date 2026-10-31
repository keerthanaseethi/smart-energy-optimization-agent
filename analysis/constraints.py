# ==================================================
# Constraint and Safety Layer
# ==================================================


class ConstraintChecker:

    def __init__(self):
        pass


    # ==================================================
    # CHECK HVAC ACTION
    # ==================================================

    def check_hvac_action(self, action, state):

        occupancy = state["Academic_Occupancy"]
        schedule = state["Academic_Schedule"]

        # Turning HVAC OFF is only allowed when
        # occupancy is very low and the area is unscheduled.

        if action == "Turn Academic HVAC OFF":

            if occupancy > 20:
                return {
                    "allowed": False,
                    "reason": (
                        "HVAC cannot be turned OFF because "
                        "occupancy is above the safety threshold."
                    )
                }

            if schedule == 1:
                return {
                    "allowed": False,
                    "reason": (
                        "HVAC cannot be turned OFF because "
                        "the academic area is currently scheduled."
                    )
                }

            return {
                "allowed": True,
                "reason": (
                    "HVAC OFF is allowed because occupancy is "
                    "very low and the area is unscheduled."
                )
            }
class ConstraintChecker:

    VALID_ACTIONS = {
        "Do Nothing",
        "Reduce Academic HVAC",
        "Turn Academic HVAC OFF",
        "Turn Academic Lighting OFF",
        "Shift EV Charging",
        "Turn Water Pump OFF",
    }

    def __init__(self, occupancy_threshold=20):
        self.occupancy_threshold = occupancy_threshold

    def _result(self, allowed, reason, rule_id):
        return {
            "allowed": allowed,
            "validation_status": "ALLOWED" if allowed else "REJECTED",
            "safety_status": "PASSED" if allowed else "FAILED",
            "reason": reason,
            "rule_id": rule_id,
            "rule": rule_id,
        }

    def _action_name(self, action):
        if not isinstance(action, dict):
            return action if isinstance(action, str) else None
        return action.get("action")

    def validate_action(self, action, state):
        """Validate an action before what-if evaluation or execution."""

        action_name = self._action_name(action)
        if not isinstance(action, dict) or not action_name:
            return self._result(
                False,
                "Action must be a mapping with a non-empty action name.",
                "ACTION_MALFORMED",
            )

        if action_name not in self.VALID_ACTIONS:
            return self._result(
                False,
                f"Unknown action is not executable: {action_name!r}.",
                "ACTION_UNKNOWN",
            )

        if action_name == "Do Nothing":
            return self._result(True, "No device action was requested.", "ACTION_NO_OP")

        required_state = {
            "Academic_Occupancy": state.get("Academic_Occupancy"),
            "Academic_Schedule": state.get("Academic_Schedule"),
            "Academic_HVAC": state.get("Academic_HVAC"),
            "Academic_Lighting": state.get("Academic_Lighting"),
            "EV_Charging": state.get("EV_Charging"),
            "Water Pump": state.get("Water Pump", "OFF"),
            "Tariff": state.get("Tariff"),
        }
        if any(value is None for value in required_state.values()):
            return self._result(
                False,
                "Required operating state is unavailable for validation.",
                "STATE_UNAVAILABLE",
            )

        try:
            occupancy = float(required_state["Academic_Occupancy"])
            schedule = int(required_state["Academic_Schedule"])
        except (TypeError, ValueError):
            return self._result(
                False,
                "Occupancy and schedule must be valid numeric operating state.",
                "STATE_INVALID",
            )

        if action_name == "Turn Academic HVAC OFF":
            if required_state["Academic_HVAC"] != "ON":
                return self._result(False, "Academic HVAC is not ON and cannot be turned OFF.", "HVAC_STATE")
            if occupancy > self.occupancy_threshold:
                return self._result(False, "HVAC OFF is prohibited above the occupancy threshold.", "HVAC_OCCUPANCY")
            if schedule == 1:
                return self._result(False, "HVAC OFF is prohibited while the academic area is scheduled.", "HVAC_SCHEDULE")
            return self._result(True, "HVAC OFF is allowed during low occupancy and no scheduled activity.", "HVAC_OFF_SAFE_WINDOW")

        if action_name == "Reduce Academic HVAC":
            if required_state["Academic_HVAC"] != "ON":
                return self._result(False, "Academic HVAC is not ON and cannot be reduced.", "HVAC_STATE")
            return self._result(True, "HVAC ECO reduction is allowed while HVAC is ON.", "HVAC_ECO_AVAILABLE")

        if action_name == "Turn Academic Lighting OFF":
            if required_state["Academic_Lighting"] != "ON":
                return self._result(False, "Academic lighting is not ON and cannot be turned OFF.", "LIGHTING_STATE")
            if occupancy > self.occupancy_threshold:
                return self._result(False, "Lighting OFF is prohibited above the occupancy threshold.", "LIGHTING_OCCUPANCY")
            return self._result(True, "Lighting OFF is allowed at low occupancy.", "LIGHTING_OFF_SAFE_WINDOW")

        if action_name == "Shift EV Charging":
            if required_state["EV_Charging"] != "ON":
                return self._result(False, "EV charging is not ON and cannot be shifted.", "EV_STATE")
            if required_state["Tariff"] != "Peak":
                return self._result(False, "EV shifting is only allowed during the defined peak period.", "EV_PEAK_ONLY")
            return self._result(True, "EV shifting is allowed during peak tariff while charging is ON.", "EV_PEAK_SHIFT")

        if action_name == "Turn Water Pump OFF":
            if "Water Pump" not in state:
                return self._result(False, "Water pump state is unavailable.", "ACTION_UNKNOWN")
            if required_state.get("Water Pump") != "ON":
                return self._result(False, "Water pump is not ON and cannot be turned OFF.", "PUMP_STATE")
            if occupancy > self.occupancy_threshold and schedule == 1:
                return self._result(False, "Pump OFF is prohibited during active scheduled occupancy.", "PUMP_OPERATIONAL_DEMAND")
            return self._result(True, "Pump OFF is allowed outside the protected operating window.", "PUMP_OFF_SAFE_WINDOW")

        return self._result(False, "Action is not available on the simulated device set.", "DEVICE_UNAVAILABLE")

    def check(self, action, state):
        if isinstance(action, str):
            action = {"action": action}
        return self.validate_action(action, state)

    def validate_unobserved_action(self, action):
        """Validate direct adapter calls that have no observation context."""

        action_name = self._action_name(action)
        if not isinstance(action, dict) or not action_name:
            return self._result(False, "Action must be a mapping with a non-empty action name.", "ACTION_MALFORMED")
        if action_name not in self.VALID_ACTIONS:
            return self._result(False, f"Unknown action is not executable: {action_name!r}.", "ACTION_UNKNOWN")
        return self._result(
            True,
            "Direct simulated command accepted without an agent observation context.",
            "DIRECT_SIMULATED_COMMAND",
        )

    def validate_expected_effect(self, action, state, evaluation):
        validation = self.validate_action(action, state)
        if not validation["allowed"]:
            return validation

        expected_saving = evaluation.get("estimated_saving_MW")
        if expected_saving is None:
            return self._result(True, "No expected impact was supplied.", "EFFECT_NOT_SPECIFIED")

        try:
            expected_saving = float(expected_saving)
        except (TypeError, ValueError):
            return self._result(False, "Expected load impact must be numeric.", "EFFECT_INVALID")

        if expected_saving < 0:
            return self._result(False, "Expected load impact cannot be negative.", "EFFECT_INVALID")

        if self._action_name(action) != "Do Nothing" and expected_saving <= 0:
            return self._result(
                False,
                "The action has no positive effect in the current simulated device state.",
                "EFFECT_INCONSISTENT",
            )

        validation["expected_impact_MW"] = expected_saving
        return validation