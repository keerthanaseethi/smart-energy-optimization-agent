# Smart Energy Agent

## Current project status

This repository is currently frozen at the last verified replay/proof-of-concept checkpoint.

The working prototype includes:
- forecasting on historical energy data
- opportunity detection and mismatch analysis
- action generation and evaluation
- safety / constraint checking
- virtual execution and replay backtesting
- decision logging

This code is intentionally preserved as the working baseline.

## Honest architecture statement

This project is not a live campus-control system yet.

The current system must be understood as:
- a deterministic energy decision prototype
- using real historical public energy data for forecasting and demand analysis
- using a clearly labeled simulation/backtest layer for demo and replay
- not a real building management system, not a real equipment control API, and not a live campus automation system

## Data reality

The dataset in `data/raw/AEP_hourly.csv` is real PJM/AEP regional demand data. It is not building-level or campus-level telemetry.

The simulated campus context and device control logic are prototype-only and must remain clearly labeled as:

> Simulation / Backtest — not real device control

## Chosen architectural direction

The repo is proceeding under a documented honest path:

- Path A style: genuine historical-data optimization using real public energy data
- explicit simulation/backtest layer for replay and demo
- no fake real-world API layer
- no false claims of live device control

## Next safe milestones

1. Preserve the working replay code and last-good behavior.
2. Complete the data and API audit and keep it in `docs/data_audit.md`.
3. Define the real data sources and constraints for the next phase.
4. Only after that, build the Streamlit dashboard with visible simulation labels.
5. Add LLM or orchestration layers only as explanatory aids, never as direct equipment control.

## Files to review

- `docs/data_audit.md` — project data/API audit and architecture boundary
- `agent/agent.py` — deterministic decision loop
- `simulation/replay.py` — backtest replay engine
- `simulation/devices.py` — virtual device layer
- `data/raw/AEP_hourly.csv` — real historical regional energy data

## Important note

The project must not be described as a live smart-campus control system unless a genuine real-time facility meter, sensor dataset, and device/API integration are added later.
