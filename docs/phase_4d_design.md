# Phase 4D Design — Adapter & Execution Boundary

Status: APPROVED (Phase 4D). Implementation planning only. Do NOT modify code or models in this step.

## 1. Overview
- Goal: design adapters and an execution boundary that let the agent ingest real external data and safely exercise testbed/real device control while preserving the exact existing forecasting and simulation behavior.
- Hard constraints (enforced): do NOT change `models/saved/energy_forecast_model.json`, do NOT add weather features to the model, do NOT retrain the current model, preserve simulation behavior as-is.

## 2. Corrected provenance semantics
- `REAL_HISTORICAL` — genuine historical datasets. In this project, **AEP is historical regional/grid-level demand and is NOT campus/building telemetry**.
- `REAL_EXTERNAL` — external third-party providers (Open‑Meteo, EIA).
- `DERIVED` — features computed from one or more source series.
- `SIMULATED` — outputs produced by the VirtualCampus/simulation pipeline.
- `TESTBED` — measurements or devices in an isolated test environment (e.g., Home Assistant test instance).

All data objects must include `provenance` (one of the above) and `source_meta` (source id, fetch_time, units, timezone, rows, notes). Transformations produce new `DERIVED` outputs that reference original sources.

## 3. Explicit current weather alignment status
- Open‑Meteo sample validated (2026-09-10 → 2026-09-12) is `REAL_EXTERNAL:Open-Meteo` and has ZERO temporal overlap with the AEP historical window (2004-10-08 → 2018-08-03).
- Conclusion: there is currently NO AEP–weather joined dataset. A future historical Open‑Meteo request may be used only if it genuinely overlaps the AEP period. Do NOT fabricate or infer historical weather values.

## 4. High-level architecture (ASCII)

[Agent Runtime]
    |
    v
[Observe Adapters: Energy / Weather / Building State]  <-- each returns TimeSeries/StateSnapshot with `provenance` + `source_meta`
    |
    v
[Forecast Engine (UNCHANGED)]  --reads `REAL_HISTORICAL` AEP features only
    |
    v
[Detect -> Diagnose -> Generate Actions] -> [What‑if via SimulationAdapter]
    |
    v
[Control Adapter (SimulationAdapter | TestbedAdapter | RealAdapter)]
    |
    v
[Verify (readback via BuildingStateSource)]
    |
    v
[Log (append-only, includes provenance & execution_result)]

Notes: Forecast Engine continues to operate unchanged on `AEP_features.csv`.

## 5. Adapter interfaces (design signatures)

- EnergyDataSource
  - fetch(start, end) -> TimeSeries {df, provenance, source_meta}
  - describe() -> {series_id, units, geography, frequency_hint}

- WeatherDataSource
  - fetch(start, end, variables) -> TimeSeries
  - describe() -> {provider, timezone, fields}

- BuildingStateSource
  - read_state(entity_ids) -> StateSnapshot {state, provenance, timestamp}
  - subscribe(callback) [optional for testbeds]

- ControlAdapter
  - execute(action, mode='dry'|'simulated'|'testbed'|'real') -> ExecResult {execution_id, status, raw_response, provenance}
  - verify(execution_id, timeout) -> VerificationResult {matched, observed_state, provenance}

All return objects MUST contain `provenance` and `source_meta`. Implementations must not drop provenance.

## 6. Execution statuses & verification
- Execution status enum: `SIMULATED`, `TESTBED`, `REAL`, `NOT_EXECUTED`.
- Execution flow (atomic):
  1. decide(action)
  2. execute(action, target_mode) -> ExecResult
  3. read_actual_state(exec_id) -> observed_state
  4. verify(exec_id) -> VerificationResult (matched boolean + delta)
  5. log decision + exec + verification (include provenance + human_approval_token when REAL)

Policy: a `SIMULATED` execution must never be recorded or interpreted as `REAL` or `TESTBED` in downstream logic.

## 7. Home Assistant (Testbed) design notes
- Home Assistant is a **TESTBED adapter** by default. It must not be enabled unless a real HA instance and credentials are available and a human enables testbed mode.
- Authentication boundary: client token/credentials must be stored locally (env/vault) and never committed.
- Read-state: `read_state(entity_id) -> {state, attributes, timestamp, provenance='TESTBED'}`.
- Control/service: `call_service(entity_id, service, params)` returns `ExecResult` with `status='TESTBED'` during testbed mode.
- Post-action verification: poll `read_state` until change observed or `timeout` → return `VerificationResult`.
- Failure handling: retries, then escalate and mark `NOT_EXECUTED`; generate safety_event.
- Dry-run/safe-mode: runtime default `DRY_RUN=true` — in dry-run the adapter returns `SIMULATED` ExecResult without network calls.

## 8. Weather joining rules (how to join a future overlapping historical weather dataset)
- Normalize timestamps to UTC; record timezone in `source_meta`.
- Infer frequency (seconds). Require hourly (3600) for direct join with AEP features; otherwise produce `DERIVED` resampled series with explicit rules and provenance.
- Deduplicate deterministically and record duplicates in `source_meta`.
- Do NOT impute missing values for features used by the current model; any imputation must produce `DERIVED` outputs and be recorded.
- DST: convert to UTC prior to any join to avoid local DST ambiguity.

## 9. LLM boundary
- LLM is explanation/intent-only: it may summarize, explain, or translate user intents to constrained intent objects.
- LLM must NOT execute commands, invent sensor readings, or produce execution results. Deterministic numerical logic remains authoritative.

## 10. Minimal Phase 4E implementation plan (KEEP MINIMAL)
Phase 4E will be staged and minimal as approved:
1. Wire `Existing Agent -> ControlAdapter -> SimulationAdapter -> Execute -> Verify -> Log` (preserve current simulation behavior exactly). No external credentials required.
2. Integrate read-only `WeatherDataSource` and `EnergyDataSource` as `REAL_EXTERNAL` inputs (EIA validation DEFERRED). These adapters return data with provenance but do not alter model inputs.
3. Implement `adapter_manager` to enforce provenance metadata and global `DRY_RUN=true` default.
4. Create tests that exercise the path `Agent -> SimulationAdapter` and ensure logs include provenance and execution_status `SIMULATED`.

Home Assistant remains unimplemented until a real instance and credentials/test devices are available.

## 11. Security, safety, and governance
- Default runtime: `DRY_RUN=true`.
- Any transition to `TESTBED` or `REAL` execution must require an explicit human approval token and audit log entry.
- Credentials must be stored locally and out of repo; access controlled by local ops.

## 12. EIA status
- EIA validation: **DEFERRED — requires local EIA credentials/series selection**.

## 13. Deliverables (this document + checklist)
- This `docs/phase_4d_design.md` (design doc) — created per approval.
- Next step after approval: implement only the minimal Phase 4E staged changes listed in Section 10.

---
Do NOT scaffold implementation files or change model artifacts. STOP after review.
