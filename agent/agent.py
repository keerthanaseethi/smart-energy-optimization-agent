# ==================================================
# Smart Energy Decision Agent
# ==================================================

import pandas as pd
from models.forecasting.forecast_engine import ForecastEngine
from simulation.devices import VirtualCampus
from simulation.what_if import WhatIfSimulator
from simulation.campus_energy import CampusEnergyModel
from analysis.constraints import ConstraintChecker
from adapters.control_adapter import ControlAdapter, ExecutionStatus
from data.provenance import make_provenance


class EnergyAgent:

    def __init__(self):

        self.campus = VirtualCampus()

        self.what_if = WhatIfSimulator()

        self.constraints = ConstraintChecker()

        self.forecaster = ForecastEngine()

        self.energy_model = CampusEnergyModel()
        # Optional control adapter (injected by replay or runtime). If set,
        # executions are delegated to the adapter (default simulated).
        self.control_adapter = None
        # Optional weather data source (injected). If set, observe() will
        # attempt to fetch weather context but will continue gracefully
        # if the fetch fails or is not present.
        self.weather_source = None
        self._last_exec_result = None
        self._last_state = None
        self._last_action_validations = []

    # --------------------------------------------------
    # Synchronize virtual campus
    # --------------------------------------------------

    def synchronize(self, row):

        campus = self.campus

        if row["academic_hvac"] == "ON":
            campus.hvac.turn_on()
        else:
            campus.hvac.turn_off()

        if row["academic_lighting"] == "ON":
            campus.lighting.turn_on()
        else:
            campus.lighting.turn_off()

        if row["ev_charging"] == "ON":
            campus.ev_charger.start_charging()
        else:
            campus.ev_charger.stop_charging()

        if row.get("pump_state") == "ON":
            campus.water_pump.turn_on()
        elif row.get("pump_state") == "OFF":
            campus.water_pump.turn_off()

    # --------------------------------------------------
    # Observe
    # --------------------------------------------------

    def observe(self, row):

        forecast = None

        try:

            forecast = (
                self.forecaster.forecast_from_row(
                    row
                )
            )

        except ValueError:

            forecast = None

        occupancy = float(
            row["academic_occupancy"]
        )

        schedule = int(
            row["academic_schedule"]
        )

        temperature = float(
            row["temperature"]
        )

        # --------------------------------------------------
        # EV requirement
        #
        # If the EV has been deliberately shifted and
        # has now resumed, that resumed load is considered
        # an expected operational load.
        # --------------------------------------------------

        ev_state = (
            self.campus.ev_charger.state
        )

        ev_required = (
            row["ev_charging"] == "ON"
            or ev_state == "ON"
        )

        # --------------------------------------------------
        # Campus baseline
        # --------------------------------------------------

        baseline = (
            self.energy_model.estimate_baseline(
                occupancy=occupancy,
                schedule=schedule,
                temperature=temperature,
                ev_required=ev_required
            )
        )

        campus_demand = (
            self.campus.get_total_load()
        )
        device_predictions = self.campus.get_device_predictions(
            timestamp=pd.Timestamp(row["Datetime"])
        )
        expected_device_demand = sum(
            prediction["predicted_power_mw"]
            for prediction in device_predictions.values()
        )

        campus_deviation = (
            campus_demand - baseline
        )

        context_provenance = make_provenance(
            "SIMULATED",
            "simulation.context_generator",
            "data/simulated/campus_context.csv",
            data_timestamp_start=pd.Timestamp(row["Datetime"]).isoformat(),
            data_timestamp_end=pd.Timestamp(row["Datetime"]).isoformat(),
            units={
                "Campus_Demand_MW": "MW",
                "Campus_Baseline_MW": "MW",
                "Reference_Demand_MW": "MW regional reference",
                "Temperature": "simulated degrees C",
                "Academic_Occupancy": "percent",
            },
            geographic_scope="virtual campus simulation; reference demand is regional AEP, not campus telemetry",
            semantic_description="Simulated campus observation assembled from replay context and virtual device state.",
            transformation="replay context applied to VirtualCampus and deterministic baseline calculation",
            metadata={
                "reference_demand_semantics": "AEP regional/grid-level historical demand, not campus telemetry",
                "device_state": self.campus.get_state(),
            },
        )

        result = {

            "Datetime":
                row["Datetime"],

            # External demand
            "Reference_Demand_MW":
                float(
                    row[
                        "reference_system_demand_MW"
                    ]
                ),

            # Forecast
            "Forecast":
                forecast,

            # Context
            "Academic_Occupancy":
                occupancy,

            "Academic_Schedule":
                schedule,

            "Temperature":
                temperature,

            "Environmental_Context": {
                **self.campus.get_environment(),
                "provenance": "SIMULATED",
                "source": "VirtualCampusEnvironment",
            },

            # Device state
            "Academic_HVAC":
                self.campus.hvac.state,

            "Academic_Lighting":
                self.campus.lighting.state,

            "EV_Charging":
                self.campus.ev_charger.state,

            "Water Pump":
                self.campus.water_pump.state,

            "Tariff":
                row["tariff"],

            # Campus energy
            "Campus_Demand_MW":
                campus_demand,

            "Campus_Baseline_MW":
                baseline,

            "Campus_Deviation_MW":
                campus_deviation,
            "Device_Predictions": device_predictions,
            "Expected_Device_Demand_MW": expected_device_demand,
            "Actual_Device_State": self.campus.get_state(),
            "Optimal_Device_State": None,
            # Optional external weather context (read-only)
            "Weather": self._fetch_weather_context(row),
            "Provenance_Metadata": context_provenance,
            "Device_State_Provenance": make_provenance(
                "SIMULATED",
                "VirtualCampus",
                "VirtualCampus.devices",
                units={"device_load": "MW"},
                geographic_scope="virtual campus; not live telemetry",
                semantic_description="Current simulated device states and loads.",
                transformation="device state readback from VirtualCampus",
            ),
        }
        self._last_state = result
        return result

    def _fetch_weather_context(self, row):
        """Attempt to fetch weather context for the given row's datetime.

        Returns a dict with `time`, `timeseries` (TimeSeries), or None on failure.
        This method is deliberately non-fatal for replay and will not raise.
        """

        if self.weather_source is None:
            return None

        try:
            dt = pd.to_datetime(row["Datetime"]).tz_localize(None)
            start = (dt - pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
            end = (dt + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")

            ts = self.weather_source.fetch(start_date=start, end_date=end)

            return {
                "time": row["Datetime"],
                "timeseries": ts,
            }

        except Exception:
            # Swallow errors — weather is optional for replay
            return None

    # --------------------------------------------------
    # Opportunity detection
    # --------------------------------------------------

    def identify_opportunity(
        self,
        state
    ):

        occupancy = state[
            "Academic_Occupancy"
        ]

        schedule = state[
            "Academic_Schedule"
        ]

        hvac = state[
            "Academic_HVAC"
        ]

        lighting = state[
            "Academic_Lighting"
        ]

        ev = state[
            "EV_Charging"
        ]

        tariff = state[
            "Tariff"
        ]

        forecast = state[
            "Forecast"
        ]

        campus_deviation = state[
            "Campus_Deviation_MW"
        ]

        # --------------------------------------------------
        # HVAC mismatch
        # --------------------------------------------------

        if (
            hvac == "ON"
            and occupancy <= 10
            and schedule == 0
        ):

            return {

                "type":
                    "HVAC_MISMATCH",

                "severity":
                    "High",

                "reason":
                    "HVAC is operating during "
                    "an unscheduled period with "
                    "very low occupancy."
            }

        # --------------------------------------------------
        # Lighting mismatch
        # --------------------------------------------------

        if (
            lighting == "ON"
            and occupancy <= 10
        ):

            return {

                "type":
                    "LIGHTING_MISMATCH",

                "severity":
                    "Medium",

                "reason":
                    "Lighting is operating while "
                    "occupancy is very low."
            }

        # --------------------------------------------------
        # Forecast-aware EV opportunity
        # --------------------------------------------------

        if (
            ev == "ON"
            and tariff == "Peak"
            and forecast is not None
        ):

            forecast_demand = (
                forecast[
                    "forecast_MW"
                ]
            )

            current_reference = (
                state[
                    "Reference_Demand_MW"
                ]
            )

            if (
                forecast_demand
                > current_reference
            ):

                return {

                    "type":
                        "EV_FORECAST_PEAK",

                    "severity":
                        "Medium",

                    "reason":
                        "EV charging is active during "
                        "peak tariff and the next-hour "
                        "forecast indicates increasing "
                        "system demand."
                }

        if (
            state.get("Water Pump") == "ON"
            and schedule == 0
            and occupancy <= 10
        ):
            return {
                "type": "PUMP_MISMATCH",
                "severity": "Medium",
                "reason": (
                    "Water pump is operating outside the scheduled low-occupancy "
                    "operating window."
                ),
            }

        # --------------------------------------------------
        # Campus baseline mismatch
        #
        # Only treat a positive deviation as an
        # opportunity when the deviation is meaningful.
        # --------------------------------------------------

        if campus_deviation > 0.5:

            return {

                "type":
                    "CAMPUS_BASELINE_MISMATCH",

                "severity":
                    "Low",

                "reason":
                    "Current simulated campus demand "
                    "is above the expected operating "
                    "baseline."
            }

        # --------------------------------------------------
        # Normal
        # --------------------------------------------------

        return {

            "type":
                "NORMAL",

            "severity":
                "None",

            "reason":
                "No actionable energy opportunity "
                "was detected."
        }

    # --------------------------------------------------
    # Generate actions
    # --------------------------------------------------

    def generate_actions(
        self,
        state,
        opportunity
    ):

        opportunity_type = (
            opportunity["type"]
        )

        if opportunity_type == (
            "HVAC_MISMATCH"
        ):

            return [

                {
                    "action":
                        "Reduce Academic HVAC",

                    "operational_impact":
                        1.0
                },

                {
                    "action":
                        "Turn Academic HVAC OFF",

                    "operational_impact":
                        2.0
                },

                {
                    "action":
                        "Do Nothing",

                    "operational_impact":
                        0.0
                }
            ]

        if opportunity_type == (
            "LIGHTING_MISMATCH"
        ):

            return [

                {
                    "action":
                        "Turn Academic Lighting OFF",

                    "operational_impact":
                        0.5
                },

                {
                    "action":
                        "Do Nothing",

                    "operational_impact":
                        0.0
                }
            ]

        if opportunity_type in [

            "EV_PEAK",

            "EV_FORECAST_PEAK"

        ]:

            return [

                {
                    "action":
                        "Shift EV Charging",

                    "operational_impact":
                        0.5
                },

                {
                    "action":
                        "Do Nothing",

                    "operational_impact":
                        0.0
                }
            ]

        if opportunity_type == "PUMP_MISMATCH":
            return [
                {"action": "Turn Water Pump OFF", "operational_impact": 1.0},
                {"action": "Do Nothing", "operational_impact": 0.0},
            ]

        return [

            {
                "action":
                    "Do Nothing",

                "operational_impact":
                    0.0
            }
        ]

    # --------------------------------------------------
    # Constraint filtering
    # --------------------------------------------------

    def filter_allowed_actions(
        self,
        actions,
        state
    ):

        allowed = []
        self._last_action_validations = []

        for action in actions:

            result = self.constraints.validate_action(action, state)
            validation_record = {**action, "validation": result}
            self._last_action_validations.append(validation_record)

            if result["allowed"]:

                allowed.append(
                    action
                )

        return allowed

    # --------------------------------------------------
    # What-if evaluation
    # --------------------------------------------------

    def evaluate_actions(self, actions, state=None):

        evaluations = []

        for action in actions:

            result = (
                self.what_if.simulate(
                    self.campus,
                    action,
                    timestamp=state.get("Datetime") if state else None,
                )
            )

            evaluation = {

                **action,

                "current_demand_MW":
                    result[
                        "current_demand_MW"
                    ],

                "simulated_demand_MW":
                    result[
                        "simulated_demand_MW"
                    ],

                "estimated_saving_MW":
                    result[
                        "estimated_saving_MW"
                    ],
                "current_predictions": result["current_predictions"],
                "simulated_predictions": result["simulated_predictions"],
                "prediction_units": result["units"],
                "prediction_model_used": result["model_used"],
                "prediction_fallback_used": result["fallback_used"],
                "prediction_provenance": result["provenance"],
                "prediction_quality": result["prediction_quality"],
                "baseline_power_kw": result["baseline_power_kw"],
                "candidate_power_kw": result["candidate_power_kw"],
                "delta_power_kw": result["delta_power_kw"],
                "baseline_energy_kwh": result["baseline_energy_kwh"],
                "candidate_energy_kwh": result["candidate_energy_kwh"],
                "energy_delta_kwh": result["energy_delta_kwh"],
                "score_formula": (
                    "estimated_saving_MW - 0.2 * operational_impact"
                ),
                "evidence": {
                    "candidate_action": action.get("action"),
                    "baseline_predicted_demand_MW": result["current_demand_MW"],
                    "candidate_predicted_demand_MW": result["simulated_demand_MW"],
                    "peak_power_change_MW": result["simulated_demand_MW"] - result["current_demand_MW"],
                    "interval_energy_change_MWh": (
                        result["simulated_demand_MW"] - result["current_demand_MW"]
                    ) * 1.0,
                    "units": result["units"],
                    "model_used": result["model_used"],
                    "prediction_quality": result["prediction_quality"],
                    "provenance": result["provenance"],
                },
            }
            if state is not None:
                evaluation["validation"] = self.constraints.validate_expected_effect(
                    action,
                    state,
                    evaluation,
                )
            evaluations.append(evaluation)

        return evaluations

    # --------------------------------------------------
    # Select best action
    # --------------------------------------------------

    def select_best_action(
        self,
        evaluations
    ):

        if not evaluations:

            return {

                "action":
                    "Do Nothing",

                "operational_impact":
                    0.0,

                "estimated_saving_MW":
                    0.0
            }

        for evaluation in evaluations:

            evaluation["score"] = (

                evaluation[
                    "estimated_saving_MW"
                ]

                -

                0.2
                * evaluation[
                    "operational_impact"
                ]
            )
            evaluation["score_formula"] = (
                "estimated_saving_MW - 0.2 * operational_impact"
            )

        return max(
            evaluations,
            key=lambda x: x["score"]
        )

    # --------------------------------------------------
    # Decide
    # --------------------------------------------------

    def decide(
        self,
        state
    ):

        opportunity = (
            self.identify_opportunity(
                state
            )
        )

        actions = (
            self.generate_actions(
                state,
                opportunity
            )
        )

        allowed_actions = (
            self.filter_allowed_actions(
                actions,
                state
            )
        )

        evaluations = self.evaluate_actions(allowed_actions, state)
        evaluations = [
            evaluation
            for evaluation in evaluations
            if evaluation.get("validation", {}).get("allowed", True)
        ]

        best_action = (
            self.select_best_action(
                evaluations
            )
        )

        return {

            "opportunity":
                opportunity,

            "actions":
                evaluations,

            "action":
                best_action,

            "action_validations":
                self._last_action_validations,

            "selected_validation":
                best_action.get("validation")
                if isinstance(best_action, dict)
                else None,
            "evidence": {
                "trigger": opportunity["type"],
                "opportunity": opportunity,
                "candidate_actions": evaluations,
                "selected_action": best_action,
                "provenance": "DERIVED",
            },
        }

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(
        self,
        action
    ):

        if self._last_state is None:
            validation = self.constraints.validate_unobserved_action(action)
        else:
            validation = self.constraints.validate_action(action, self._last_state)
        action_name = action.get("action") if isinstance(action, dict) else None

        if not validation["allowed"]:
            self._last_exec_result = None
            return {
                "status": "NOT_EXECUTED",
                "message": validation["reason"],
                "verification": {"matched": False, "status": "NOT_REQUIRED"},
                "validation": validation,
            }

        if action_name == "Do Nothing":
            return {
                "status": "NO_ACTION",
                "message": "No action was required.",
                "verification": {"matched": True, "status": "NOT_REQUIRED"},
                "validation": validation,
            }

        # If a control adapter is present, delegate execution to it.
        if self.control_adapter is not None:

            exec_result = self.control_adapter.execute(action, mode="simulated")

            # stash for later verification/logging
            self._last_exec_result = exec_result

            verification = getattr(exec_result, "verification", {}) or {}
            matched = bool(verification.get("matched", False))

            # Only report success if the adapter executed and then verified a
            # successful readback. Verification mismatches must be treated as
            # failed/unverified even when the adapter returned SIMULATED state.
            if getattr(exec_result, "status", None) == ExecutionStatus.SIMULATED and matched:
                return {
                    "status": "SUCCESS",
                    "message": exec_result.raw_response,
                    "verification": verification,
                    "validation": validation,
                }

            return {
                "status": "FAILED",
                "message": exec_result.raw_response,
                "verification": verification,
                "validation": validation,
            }

        # Fallback: original direct manipulation of campus devices
        action_name = action["action"]

        if action_name == "Reduce Academic HVAC":
            message = self.campus.hvac.set_eco()

        elif action_name == "Turn Academic HVAC OFF":
            message = self.campus.hvac.turn_off()

        elif action_name == "Turn Academic Lighting OFF":
            message = self.campus.lighting.turn_off()

        elif action_name == "Shift EV Charging":
            message = self.campus.ev_charger.shift_charging(resume_hour=22)

        elif action_name == "Turn Water Pump OFF":
            message = self.campus.water_pump.turn_off()

        elif action_name == "Do Nothing":
            return {"status": "NO_ACTION", "message": "No action was required."}

        else:
            return {"status": "FAILED", "message": "Unknown action."}

        return {"status": "SUCCESS", "message": message}

    # --------------------------------------------------
    # Verify
    # --------------------------------------------------

    def verify(
        self,
        action
    ):

        return {

            "action":
                action["action"],

            "campus_state":
                self.campus.get_state(),

            "campus_load_MW":
                self.campus.get_total_load()
        }

    # --------------------------------------------------
    # Campus demand
    # --------------------------------------------------

    def get_campus_load(self):

        return (
            self.campus.get_total_load()
        )


# ==================================================
# Standalone test
# ==================================================

if __name__ == "__main__":

    import pandas as pd

    data = pd.read_csv(
        "data/simulated/campus_context.csv"
    )

    data["Datetime"] = pd.to_datetime(
        data["Datetime"]
    )

    scenario = data[
        data["Datetime"]
        == pd.Timestamp(
            "2017-03-15 18:00:00"
        )
    ].iloc[0]

    agent = EnergyAgent()

    agent.synchronize(
        scenario
    )

    state = agent.observe(
        scenario
    )

    print("=" * 75)
    print(
        "CAMPUS + FORECAST-AWARE ENERGY AGENT"
    )
    print("=" * 75)

    print()

    print("CURRENT CONTEXT")

    print(
        f"Time: "
        f"{state['Datetime']}"
    )

    print(
        f"Campus demand: "
        f"{state['Campus_Demand_MW']:.1f} MW"
    )

    print(
        f"Campus baseline: "
        f"{state['Campus_Baseline_MW']:.1f} MW"
    )

    print(
        f"Campus deviation: "
        f"{state['Campus_Deviation_MW']:.1f} MW"
    )

    print(
        f"AEP reference demand: "
        f"{state['Reference_Demand_MW']:.2f} MW"
    )

    if state["Forecast"] is not None:

        print(
            f"Next-hour AEP forecast: "
            f"{state['Forecast']['forecast_MW']:.2f} MW"
        )

    print(
        f"Occupancy: "
        f"{state['Academic_Occupancy']}%"
    )

    print(
        f"Temperature: "
        f"{state['Temperature']:.1f} °C"
    )

    print(
        f"Tariff: "
        f"{state['Tariff']}"
    )

    print(
        f"HVAC: "
        f"{state['Academic_HVAC']}"
    )

    print()

    print("OPPORTUNITY")

    decision = agent.decide(
        state
    )

    print(
        f"Type: "
        f"{decision['opportunity']['type']}"
    )

    print(
        f"Severity: "
        f"{decision['opportunity']['severity']}"
    )

    print(
        f"Reason: "
        f"{decision['opportunity']['reason']}"
    )

    print()

    print("ACTION EVALUATION")

    for action in decision["actions"]:

        print()

        print(
            f"Action: "
            f"{action['action']}"
        )

        print(
            f"Current load: "
            f"{action['current_demand_MW']:.1f} MW"
        )

        print(
            f"Simulated load: "
            f"{action['simulated_demand_MW']:.1f} MW"
        )

        print(
            f"Estimated saving: "
            f"{action['estimated_saving_MW']:.1f} MW"
        )

        print(
            f"Score: "
            f"{action['score']:.2f}"
        )

    print()

    print("SELECTED ACTION")

    print(
        decision["action"]["action"]
    )

    execution = agent.execute(
        decision["action"]
    )

    print()

    print("EXECUTION")

    print(
        f"Status: "
        f"{execution['status']}"
    )

    print(
        f"Message: "
        f"{execution['message']}"
    )

    verification = agent.verify(
        decision["action"]
    )

    print()

    print("VERIFICATION")

    print(
        f"Campus state: "
        f"{verification['campus_state']}"
    )

    print(
        f"Campus load: "
        f"{verification['campus_load_MW']:.1f} MW"
    )

    print()

    print("=" * 75)
    print("AGENT TEST COMPLETED")
    print("=" * 75)