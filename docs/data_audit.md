# Data & API Audit — Smart Energy Consumption Optimization Agent

## Status at this checkpoint

This project is intentionally frozen at the last known-good replay state:

- forecasting works
- opportunity detection works
- action evaluation works
- constraint checking works
- virtual execution works
- EV rescheduling works
- decision logging works
- replay works

We are not building the dashboard yet, not adding LangGraph, and not adding LLM control flow yet.

The current working code is a proof of concept and must remain preserved as-is. The next step is not a feature extension, but a correctness audit of the data and API boundaries.

---

## 1. What is the actual facility target?

The project brief describes a smart campus with controllable devices:

- HVAC
- Lighting
- EV charger
- Water pump

This is a useful prototype concept, but as of now there is no real campus facility, no real building-management system, and no real connected device layer.

Conclusion:

- The current target is a simulated campus environment used for demo and backtesting.
- It is not a real, operating campus energy system.
- Any claim that the agent is operating a real campus is not legitimate at this stage.

---

## 2. What genuine energy data do we actually have?

The dataset downloaded into `data/raw/` is the Kaggle hourly PJM energy dataset, specifically the AEP file:

- `AEP_hourly.csv`

This file contains:

- timestamp
- `AEP_MW` demand values

The data is real, but it is not campus-level consumption. It is regional/grid-level demand for the American Electric Power service territory.

Important facts:

- The file represents aggregate regional power demand, not a single building or campus.
- The dataset is historical and public, useful for forecasting and peak-risk analysis.
- It does not contain building occupancy, indoor temperature, equipment state, or campus asset operation data.

Therefore, the genuine data we have is:

- historical regional energy demand time series
- no verified campus-level energy telemetry
- no verified facility operation context data from a real system

---

## 3. What genuine contextual data do we have?

At present, the project includes simulated context such as:

- occupancy
- academic schedule
- temperature
- tariff
- HVAC state
- lighting state
- EV charging state
- pump state

These values are being created in the simulated campus layer and are useful for demo logic, but they are not real-world plant/facility data.

The project currently has:

- a simulated campus context file in `data/simulated/campus_context.csv`
- a simulation layer in `simulation/devices.py` and related modules
- replay logic that feeds those values sequentially through the agent

This means the contextual layer is a prototype dataset, not genuine operational data.

Conclusion:

- The forecasting pipeline can operate on real public energy data.
- The campus context layer remains simulated.
- This must be clearly labeled everywhere as simulation/backtest, not real operating context.

---

## 4. Why did we only download one particular file?

The reason was practical and valid for the first working prototype:

- `AEP_hourly.csv` was selected as a single, manageable dataset to validate the full pipeline
- it allowed the team to test ingestion, feature engineering, forecasting, mismatch detection, action evaluation, and replay
- it gave a working end-to-end proof of concept

This was a reasonable first step.

However, the mistake was treating that single regional file as if it were the data source for the final campus agent without explicitly validating the domain mismatch.

The deeper issue is:

- we started from a public grid dataset,
- then we overlaid a simulated campus model on top of it,
- and we risked presenting the simulation as if it were real building operations.

This is precisely the architectural risk that must be corrected before moving forward.

---

## 5. What can the agent legitimately forecast?

Given only genuine public energy data, the agent can legitimately do the following:

- forecast future regional demand patterns
- detect hourly or daily demand anomalies
- identify peak-risk windows
- estimate likely high-demand periods
- model demand responsiveness at the aggregate level

It cannot legitimately forecast:

- the exact operational state of a real campus building
- exact real-time occupancy of a real facility
- real HVAC load or exact building-level zonal temperature behavior
- real EV charging demand for a campus unless that data is provided by real systems

Conclusion: with the current genuine data, the forecasting engine is valid only for regional energy-demand behavior, not real building operations.

---

## 6. What can it legitimately optimize or decide?

The genuine optimization surface depends on the dataset and problem framing.

### Option A: regional historical optimization agent

If we remain with public PJM/AEP data, the agent can legitimately optimize or decide things like:

- demand peak avoidance
- load shifting opportunities at an aggregate level
- anomaly response in regional demand profiles
- policy or operational suggestions for flexible load timing under tariff constraints

This is honest and valid, but it is not a physical-control agent.

### Option B: real-time control agent

If we want an agent that truly decides and controls equipment, then the system must have:

- a real energy API or smart meter feed
- real contextual signals
- a real building-management or device API
- a real control path

Without those, optimization is only a simulation.

Conclusion:

- The current agent is best understood as a simulation-based decision engine.
- It is not a real-world control agent.
- Any true action-taking system must be grounded in real APIs or a verifiable sandbox.

---

## 7. What can it actually control today?

Right now, the project can control only the virtual campus objects defined in the simulation layer:

- `VirtualCampus`
- HVAC device object
- lighting object
- EV charger object
- pump object

These behaviors are implemented in the simulation modules, not in a real API.

Therefore:

- the current action layer is a prototype execution layer
- it is not a real building control API
- it is not a real EV charging system integration
- it is not a real campus automation layer

This must remain explicitly labeled as:

> Simulation / Backtest — not real device control

---

## 8. Data API vs control API vs LLM API

This is one of the key corrections we need to preserve.

### Data API

This is how the agent receives new real energy or context data.

Example types:

- smart meter feed
- utility API
- BMS telemetry feed
- sensor or IoT stream

### Control API

This is how the agent changes a real device or system state.

Example types:

- BMS API
- HVAC controller API
- EV charger API
- demand-response platform API

### LLM API

This is not the source of truth for energy or control.

It is useful only for:

- explaining the decision
- summarizing why an action was selected
- interacting with the user
- generating narratives/instructions

The LLM should never be the only authority on energy measurements or direct equipment control.

---

## 9. The architectural decision we will keep

We are choosing a clear, honest path for this repo:

### Chosen path: Path A with an explicit simulation/backtest layer

This project will continue as a genuine historical-data optimization agent for real public energy data, with a clearly separated simulation/backtest layer for demo and replay.

This means:

- real public energy data remains the backbone
- the agent can forecast and reason over actual measurable historical patterns
- the decision engine can still evaluate proposed interventions
- the replay engine can be used as a demo and validation sandbox
- the virtual campus is not presented as real equipment control

### Why this is the right choice now

Because the project currently lacks all of the following:

- real building telemetry
- real occupancy data
- real HVAC control access
- real charger API access
- real building management system integration

Without these, a real-time physical-control architecture would be invented rather than implemented.

---

## 10. What we will do next

The next incremental work should be:

1. preserve the current working replay/proof-of-concept code exactly as-is
2. document the audit in this repo
3. decide explicitly which real datasets we want to use going forward
4. define whether we are continuing as:
   - a regional demand optimization agent, or
   - a hybrid architecture that keeps a simulation layer for demos while staying honest about the boundary
5. only then proceed to the dashboard stage

---

## 11. Recommended project framing

The project should be described as:

> A deterministic smart energy decision system that operates on genuine historical energy data and a clearly labeled simulation/backtest layer for replay and demonstration. It is not a live campus-control system unless a genuine real-time metering and control API is added later.

This keeps the work honest, explainable, and aligned with the mentor’s requirement that the agent must execute actions, while also respecting the fact that real energy control requires real data and real APIs.

---

## 12. Final position

We should not fake the system by pretending the simulation is a real control layer.

We should also not pretend that a single regional dataset is full campus reality.

The correct direction is:

- keep the working proof-of-concept intact
- treat AEP as a real but regional demand signal
- keep the virtual campus as a simulation and replay environment
- define the project honestly as a historical-data optimization prototype with a labelled backtest layer
- only expand to real control when a genuine control API and real facility data are available

This is the correct checkpoint before any dashboard or LLM augmentation work.
