# Final Device Model Report

This report is the evidence-backed model inventory for the simulated
VirtualCampus. `REAL_EXTERNAL` describes the training source; predictions are
`DERIVED`; device state and execution remain `SIMULATED`.

| Device | Dataset | Target | Units | Best model | MAE | RMSE | R2 | Prediction | Control | Registered | Fallback |
|---|---|---|---|---|---:|---:|---:|---|---|---|---|
| Lighting | CU-BEMS Floor 2 | Sum of `z1_Light(kW)` through `z4_Light(kW)` | kW | HistGradientBoosting | 0.942 | 2.432 | 0.787 | Approved | Approved | Yes | Safe fallback |
| EV charging | Residential EV apartment sessions | `El_kWh` per session | kWh/session | RandomForest | 6.481 | 10.247 | 0.261 | Approved | Not approved | No | Active |
| HVAC | AHU Blower Energy Consumption | `Consumption` | kWh/irregular interval | RandomForest | 1.365 | 1.910 | 0.103 | Research only | Not approved | No | Active |
| Water pump | UCI hydraulic rig / UK-DALE pump candidate | Proxy or domain-mismatched electrical power | W | None registered | 9.15 proxy | 11.82 proxy | -0.658 proxy | Not approved | Not approved | No | Active |

## Approval gates

Control approval requires a valid target, known provenance, leakage-safe
evaluation, meaningful baseline improvement, acceptable error, correct units,
available runtime features, stable behavior, documented limitations, and the
existing safety constraints. A positive R2 alone is insufficient.

## Runtime behavior

- Lighting uses the CU-BEMS artifact when ON and converts predicted kW to the
  VirtualCampus MW contract. OFF is an explicit zero operational state.
- EV remains fallback-only because its model predicts session energy, not
  instantaneous charging power. The runtime must not relabel kWh/session as kW.
- HVAC remains fallback-only because it does not beat the median baseline on
  MAE and lacks meaningful conditioning variables.
- Water pump remains fallback-only. The UK-DALE `solar_thermal_pump` channel is
  a real household pump/control circuit, not campus-water-pump telemetry.

## Quality and provenance

Every prediction exposes `prediction_quality`, approval flags, model identity,
target type, dataset, limitations, provenance, and fallback status. Failed
inference falls back explicitly and records the reason. No confidence interval
is fabricated.
