# Device Dataset Audit

This audit is the evidence gate for KAIRA's device-intelligence layer. The existing
regional AEP/XGBoost model is not a device model and is intentionally excluded from
the device training targets.

| Dataset | Source | Device / use | Real or synthetic | Target | Units | Sampling | Features / coverage | License / usage | Useful for | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| ASHRAE Great Energy Predictor III | [Kaggle competition](https://www.kaggle.com/competitions/ashrae-energy-prediction) and [ASHRAE metadata](https://www.ashrae.org/technical-resources/ashrae-great-energy-predictor-iii) | Building-level electricity and thermal-meter modeling; HVAC context only when supported by meter type and metadata | Real building meter data | `meter_reading` by building and meter type | Dataset-specific meter units; electricity is not automatically an HVAC target | Hourly | Building metadata, timestamp, meter type, weather | Kaggle competition terms and source terms must be reviewed before redistribution | Building-level demand/context modeling and calibration research | A whole-building electricity meter must not be relabeled as HVAC, lighting, or pump electricity; no appliance-level ground truth for most buildings |
| ACN-Data | [Caltech ACN Data](https://ev.caltech.edu/dataset) and [ACN-Data documentation](https://acnportal.readthedocs.io/) | EV charging behavior | Real charging-station sessions | Session/EVSE charging current and power traces | Amps / kW depending on export and phase configuration | Session/event data; commonly seconds to minutes | Arrival, departure, station, pilot/current signals, energy/session metadata where available | Dataset terms and site-specific access conditions apply | EV arrival, departure, flexibility, deadline and charging-power modeling | It models charging sessions, not a particular KAIRA campus charger; tariff and battery SoC may require additional configured inputs |
| UCI Occupancy Detection | [UCI repository](https://archive.ics.uci.edu/dataset/357/occupancy+detection) | HVAC/lighting context | Real sensor readings from an office experiment | Occupancy label, not energy | Temperature °C, humidity %, light lux, CO2 ppm, humidity ratio | Approximately minute-level sensor records | Temperature, humidity, light, CO2 and occupancy label | UCI repository dataset license/terms | Occupancy/context features and validation of context handling | It has no direct appliance-energy target; it must not be used to claim a lighting-power model |
| Pecan Street Dataport | [Pecan Street data access](https://www.pecanstreet.org/dataport/) | Residential circuit/appliance energy where access is granted | Real smart-meter/circuit data | Circuit or appliance electricity measurements | Dataset/export dependent, commonly kW/kWh | Commonly sub-hourly; access/export dependent | Whole-home and circuit channels, timestamps, metadata subject to access | Access is controlled and terms vary; not assumed redistributable | Appliance-load methodology and calibration when a valid circuit label exists | Access may require application/payment; residential circuits are not campus HVAC/pump data and labels must be verified |
| UCI Condition Monitoring of Hydraulic Systems | [UCI repository](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems) | Hydraulic pump/motor condition and power research | Real controlled laboratory test-rig measurements | Hydraulic variables and pump/motor condition signals; target must be selected from the documented channels | Dataset channel-specific | Multi-rate sensor recordings; verify the channel timestamps before resampling | Pressure, flow, temperature, motor/pump-related sensors and condition labels | UCI repository dataset license/terms | Pump/motor behavior and condition-aware research | It is an oil-based laboratory hydraulic rig, not a campus water pump; it cannot be presented as campus pump telemetry without calibration |
| CU-BEMS smart building energy and IAQ data | [Kaggle dataset](https://www.kaggle.com/datasets/claytonmiller/cubems-smart-building-energy-and-iaq-data) | Explicit floor-zone lighting circuits | Real smart-building electrical measurements | `z1_Light(kW)` through `z4_Light(kW)` in the validated Floor 2 file; summed target is direct lighting power | kW | One minute | Timestamp plus named zone lighting channels; no occupancy/daylight in the selected file | CC BY-SA 4.0; source terms must be reviewed before redistribution | Lighting-power modeling and temporal baselines | One building/floor context; missing channel rows require explicit exclusion; not campus telemetry |
| UK-DALE house 1 channel 3 | [Official CEDA archive](https://data.ceda.ac.uk/edc/efficiency/residential/EnergyConsumption/Domestic/UK-DALE-2017/UK-DALE-FULL-disaggregated/ukdale.zip) and [metadata](https://raw.githubusercontent.com/JackKelly/UK-DALE_metadata/master/building1.yaml) | Solar-thermal water-pumping station and control electronics | Real household appliance/circuit measurement | `house_1/channel_3.dat`, explicitly identified as `solar_thermal_pump` | W | Nominal six seconds; irregular timestamps in raw channel | UNIX timestamp plus power; 21,281,208 rows acquired from the ZIP entry; 80.0% zero readings; observed max 2,048 W | CC BY 4.0; official archive returned HTTP 200 without credentials | Direct pump electrical-power validation | Solar-thermal circulation pump, not campus irrigation/booster pump; control electronics are bundled; source channel needs domain adaptation |
| UK-DALE house 1 channel 8 | [Official CEDA archive](https://data.ceda.ac.uk/edc/efficiency/residential/EnergyConsumption/Domestic/UK-DALE-2017/UK-DALE-FULL-disaggregated/ukdale.zip) and [metadata](https://raw.githubusercontent.com/JackKelly/UK-DALE_metadata/master/building1.yaml) | Kitchen lighting circuit | Real household appliance/circuit measurement | `house_1/channel_8.dat`, explicitly identified as `kitchen_lights` | W | Nominal six seconds; irregular timestamps in raw channel | UNIX timestamp plus power; 21,449,386 rows acquired from the ZIP entry; 56.1% zero readings; observed max 1,325 W | CC BY 4.0; official archive returned HTTP 200 without credentials | Independent lighting validation | Retrofit-era circuit and household context; CU-BEMS is preferred for the current lighting benchmark because it has a smaller, cleaner minute-level file |
| SCADA Pipeline Operations Dataset | [Kaggle dataset](https://www.kaggle.com/datasets/zara2099/scada-pipeline-operations-dataset) | Pipeline pump/compressor monitoring | **Simulated SCADA / digital twin** | `energy_consumption` is present but simulated | Unspecified in the source file | Claimed 1 Hz, but raw sample requires validation | Pressure, flow, pump state/speed, energy and fault labels | CC0 for the published synthetic data | Testing schema handling only | Rejected as direct pump evidence because the source explicitly says simulated |
| Current KAIRA VirtualCampus context | `data/simulated/campus_context.csv` | Simulation integration and deterministic regression tests | **Synthetic / simulated** | Simulated HVAC, lighting, EV and pump targets generated by VirtualCampus formulas | MW | Hourly replay context | Temperature-like context, occupancy, schedule, device states and tariff | Internal project artifact | Testing API/control boundaries and simulation behavior | It is not real telemetry and must not be reported as evidence of real-world device-model accuracy |

## Decision gate

CU-BEMS now provides a validated direct lighting target. A direct electrical
water-pump dataset has not yet passed the evidence gate. The SCADA pipeline
candidate was downloaded but rejected because its documentation explicitly
identifies it as simulated.

The device-intelligence implementation may proceed per device only after:

1. the source record and license are verified;
2. the target is proven to measure the claimed device quantity;
3. units, sampling, missingness, duplicates, and time range are profiled;
4. chronological train/validation/test splits are defined; and
5. a baseline and leakage-safe evaluation are recorded.

Where a valid appliance target is unavailable, KAIRA must keep the deterministic
VirtualCampus formula as an explicitly simulated fallback rather than fabricate a
trained device model.

## Training status

The UCI hydraulic archive was profiled locally. It contains 2,205 complete
60-second cycles and a measured `EPS1` motor-power channel sampled at 100 Hz.
That channel supports a real hydraulic motor-power regression target, but the
rig uses oil and is not a campus water-pump installation. KAIRA therefore
stores the trained result as `target_type=PROXY`, with `provenance=REAL_HISTORICAL`,
and does not register it as the active VirtualCampus water-pump model. The
training pipeline is [train_hydraulic_motor.py](../models/device_training/train_hydraulic_motor.py).

## Current model boundary

`models/device_models.py` provides the common inference boundary used by
`VirtualCampus.get_device_predictions()`. It supports registering a validated
device-specific predictor, but the newly benchmarked artifacts remain
evaluation artifacts only and no real device predictor is registered yet.
Until a target-validated dataset is profiled and trained, every default
prediction is labelled `SIMULATED` and uses the existing deterministic
VirtualCampus formula. This is an integration seam, not evidence that the
current simulator has learned real appliance behavior.
