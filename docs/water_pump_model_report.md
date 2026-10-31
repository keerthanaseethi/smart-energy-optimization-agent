# Water Pump Runtime Model Report

## Dataset and boundary

The UCI hydraulic motor artifact and UK-DALE `solar_thermal_pump` evidence
remain documented but are not treated as campus-water-pump telemetry. The UCI
target is a hydraulic test-rig motor proxy; UK-DALE is a household solar
thermal control circuit.

Because neither is a defensible campus pump target, the runtime uses
`virtualcampus-water-pump-calibrated-v1`. This is a transparent engineering
simulation layer, not a learned campus model and not live telemetry.

## Contract

The model uses the available simulated context: pump state, moisture demand,
pressure factor, schedule activity, and device factor. It returns instantaneous
power in kW and interval energy in kWh. `OFF` predicts zero power. The
prediction is `DERIVED` from a `SIMULATED_CALIBRATED` model and is approved only
for simulated control:
`APPROVED_FOR_SIMULATED_CONTROL`.

No fabricated direct dataset metrics are reported. The existing hydraulic
proxy metrics remain in its manifest with `approved_for_control=false`.
