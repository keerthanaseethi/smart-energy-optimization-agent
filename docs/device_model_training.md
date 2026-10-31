# Device Model Training Status

This document records the result of the first real-data training pass. A model
is marked trained only when its target is measured by the source dataset.

| Device | Dataset | Target | Units | Model | Test metrics | Trained | Registered/used |
|---|---|---|---|---|---|---|---|
| HVAC | HVAC AHU Blower Energy Consumption | `Consumption` | kWh per irregular interval | RandomForestRegressor | MAE 1.37; RMSE 1.91; R2 0.103; median baseline MAE 1.10 | Evaluated, not approved | Not registered |
| Lighting | CU-BEMS smart building energy and IAQ data, Floor 2 | Sum of `z1_Light(kW)` ... `z4_Light(kW)` | kW at one-minute sampling | HistGradientBoostingRegressor | MAE 0.94; RMSE 2.43; R2 0.787 | Yes, generalized external | Not registered |
| EV Charging | Residential EV charging from apartment buildings | `El_kWh` per session | kWh | RandomForestRegressor | MAE 7.60; RMSE 11.37; R2 0.090 | Yes, generalized external | Not registered |
| Water Pump | UCI Condition Monitoring of Hydraulic Systems | EPS1 cycle-mean hydraulic-rig motor power | W | RandomForestRegressor | MAE 9.15 W; RMSE 11.82 W; R2 -0.658 | Yes, proxy | Not registered |
| Water Pump candidate | UK-DALE house 1 `solar_thermal_pump` (channel 3) | Direct channel power | W | Not trained yet | - | Validated dataset candidate | Not registered |

## Hydraulic proxy decision

The UCI hydraulic dataset contains 2,205 complete cycles and a measured EPS1
motor-power signal sampled at 100 Hz. The training pipeline summarizes each
60-second cycle into 64 statistics from the other sensor channels and predicts
the cycle-mean EPS1 power. The split is chronological (1,764 train rows and
441 test rows), with no shuffle.

The result is intentionally classified as `target_type=PROXY`. The source is
an oil-based laboratory hydraulic test rig, not a campus water pump, and the
runtime VirtualCampus does not expose the source's 64 hydraulic features.
The negative test R2 also means this artifact is not presented as a
production-quality predictor. It is retained as reproducible evidence and a
future integration candidate, not silently used to control the simulated pump.

## Unsupported targets

- ASHRAE provides real building-level meter readings and weather, but does not
  provide clean fixture-level lighting or equipment-level HVAC electricity for
  this project. Building electricity will not be relabelled as HVAC power.
- UCI Occupancy Detection provides real occupancy/context readings, including
  illuminance in lux, but no lighting-energy target. Lux is not watts.
- ACN-Data is the appropriate EV candidate because it contains measured charging
  sessions, but its API requires registration/token access. No unverified
  sample or fabricated EV target is used.

The HVAC, lighting, and EV artifacts are reproducible generalized behavior models saved
under `models/saved/device/`. They are not campus telemetry and are not wired
into `VirtualCampus`: the current runtime context cannot provide all of their
source features without fabricating values. Lighting and water pump therefore
remain on the explicit `SIMULATED_FALLBACK` path in `DeviceModelRegistry`.

The improved HVAC evaluation records median/mean/ridge baselines and two
tree-based candidates. The best candidate improves RMSE but does not beat the
median baseline on MAE, so HVAC is explicitly not approved for integration.
The improved EV candidate beats the best baseline on both MAE and RMSE, but it
is still a session-energy model and requires real session inputs at runtime.
The CU-BEMS lighting candidate beats its best baseline on both metrics, but it
also remains a generalized building-floor model pending a runtime feature and
unit adapter review.

The UK-DALE pump channel is now raw-validated as a direct electrical target:
21,281,208 timestamp/power rows, nominal six-second sampling, and an explicit
`solar_thermal_pump` metadata identity. It remains a dataset candidate rather
than a registered model because it bundles control electronics and represents a
solar-thermal household installation, not the simulated campus pump.

The HVAC source contains only timestamp fields and interval energy; duplicate
timestamps were resolved by keeping the last row. The EV source contains
measured session energy, but 34 sessions with missing duration were excluded.
