# Agent Decision Contract

The backend is the source of numerical and safety truth. Communication layers
may explain a structured result but may not calculate new savings, override
constraints, invent telemetry, or claim physical execution.

## Cycle

`observe -> forecast -> predict -> analyze -> what-if -> constrain -> score -> decide -> execute -> verify -> feedback`

`VirtualCampus` owns simulated device state. The React client observes and
requests permitted actions; it is not the simulation clock.

## Prediction contract

Each device prediction contains:

- `predicted_power_mw` and explicit `unit`
- `model_id`, `model_version`, `model_status`
- `provenance` (`DERIVED` for model output, `SIMULATED` for fallback)
- `target_type`, `dataset`, `limitations`
- `prediction_quality`
- `approved_for_prediction`, `approved_for_control`
- `fallback_used`

Power (kW/MW) is never presented as energy (kWh/MWh). The EV session artifact
is therefore not used as instantaneous charging power.

## Evidence contract

What-if results carry current and candidate predictions, units, model identity,
fallback and provenance maps, quality maps, peak-power change, and interval
energy change in both MW/MWh and kW/kWh. Agent decisions carry the opportunity trigger, candidate
evaluations, selected action, score, validation, and execution/verification.

The score is intentionally transparent:

`score = estimated_saving_MW - 0.2 * operational_impact`

Constraints are evaluated before execution. A rejected action is
`NOT_EXECUTED`; Agent Control OFF leaves recommendations visible but prevents
execution. A valid no-action result is preferred over a forced intervention.

## Expected, actual, optimal

- **Expected:** model-derived device demand under the current timestamp/state.
- **Actual:** the current simulated VirtualCampus state and load.
- **Optimal:** the best feasible candidate returned by constrained what-if
  evaluation, not simply the minimum-power state.

## Communication grounding

Natural-language responses must be generated from the structured decision and
evidence object. If a value is unavailable, communication must say so. The
system must distinguish recommendation, decision, simulated execution,
verification, safety rejection, and no-action outcomes.
