# HVAC Runtime Model Report

## Decision

The previously trained AHU blower artifact remains evidence-only:
`ahu-blower-energy-v1` predicts irregular-interval `Consumption` in kWh, has
MAE 1.365, RMSE 1.910, R2 0.103, and does not beat the median baseline MAE
of 1.103. It is therefore `FALLBACK_ONLY` for autonomous control and is not
used by the VirtualCampus runtime.

The runtime uses `virtualcampus-hvac-calibrated-v1`, an explicit
`SIMULATED_CALIBRATED` power model. It consumes only available simulated
context: HVAC state, outdoor temperature, outdoor humidity, occupancy, and
setpoint. It returns instantaneous kW and derives interval kWh using the
simulation timestep.

## Contract

- `ON`, `ECO`, and `OFF` are model inputs.
- `OFF` predicts zero power.
- `ECO` is capped by the calibrated eco operating envelope.
- Provenance is `DERIVED` for the prediction and `SIMULATED_CALIBRATED` for
  the calibration source.
- No physical-campus telemetry, statistical confidence interval, or physical
  savings claim is made.

This model is approved only for simulated control:
`APPROVED_FOR_SIMULATED_CONTROL`.
