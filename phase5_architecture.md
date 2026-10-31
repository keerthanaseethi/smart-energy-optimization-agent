# Phase 5.0 Architecture Plan

## 1. Executive Summary

This project is a deterministic smart-energy decision system built around a validated forecasting and replay pipeline, not a real autonomous campus control system. The core objective of Phase 5.0 is to define the end-to-end architecture for a hackathon-ready prototype that clearly separates:

- real historical and external data,
- derived analysis artifacts,
- simulated virtual campus behavior,
- future testbed and real control modes,
- and a constrained LLM interaction layer.

The architecture explicitly avoids inventing fake campus telemetry, avoids claiming real control, and preserves the proven deterministic decision loop already validated in earlier phases. The design supports a bounded proactive runtime and a simple dashboard view for demonstration while maintaining auditability, provenance, and safety.

Important boundary: the current prototype is a simulation-first decision support system. Device control is only enabled in SIMULATED mode. TESTBED and REAL control remain future capabilities gated behind explicit implementation, authorization, and safety validation.

---

## 2. Current Validated Foundation

The current project foundation is already validated and intentionally narrow:

- The forecasting model remains the existing AEP-trained XGBoost artifact in `models/saved/energy_forecast_model.json`.
- Forecasting logic remains unchanged and continues to use the existing feature engineering and trained model artifact.
- The replay/simulation environment is deterministic and bounded.
- The system already enforces a clear distinction between:
  - data provenance,
  - adapter-based execution control,
  - and verification outcomes.
- The execution boundary is structured around adapter interfaces rather than hardcoded device control.
- The current runtime remains dry-run/simulated and records an auditable trace for each decision.
- The project is intentionally not connected to a real campus energy source, a real automation system, or a live LLM service.

Current validated semantics:

- The system can observe data and simulate campus states.
- The system can decide on an action using the deterministic logic.
- The system can simulate action execution and verify the post-action state.
- The system can log all steps in an auditable way.
- The system cannot claim real autonomous campus control.

---

## 3. Data Architecture

The project must keep strict semantics between data classes. The following categories are the authoritative data model for the architecture.

### Data Classes

#### REAL_HISTORICAL
Definition:
- AEP historical regional/grid-level energy data.
- Not campus telemetry.
- Used as contextual historical reference, not as a direct campus energy ground truth.

Purpose:
- Understand demand patterns and energy context.
- Support historical comparison and evaluation.
- Provide reference energy context without implying direct campus measurements.

Restrictions:
- Never presented as real campus telemetry.
- Must be clearly labeled as regional historical data.

#### REAL_EXTERNAL
Definition:
- Open-Meteo and any other genuinely validated external data source.
- Real weather or ambient context when available and properly ingested.

Purpose:
- Supply real weather or environmental context.
- Improve forecast context and decision support.
- Enrich diagnostics while remaining read-only.

Restrictions:
- Read-only ingestion only.
- No simulated weather should be described as real weather.
- No forced temporal alignment should be invented.

#### DERIVED
Definition:
- Features, diagnostics, opportunity scores, forecast outputs, what-if estimates, decision explanations, and derived metadata.

Purpose:
- Power the deterministic decision engine.
- Support audit trails and model comparisons.
- Provide output for UI/dashboard explanation.

Restrictions:
- Derived values must be explicitly labeled as derived and not treated as direct sensor truth.

#### SIMULATED
Definition:
- Virtual campus/device state.
- Replay/backtesting scenarios.
- Simulated execution and readback verification.

Purpose:
- Demonstrate the decision engine under deterministic conditions.
- Enable bounded proactive runs and regression validation.
- Support hackathon demo flows without real devices.

Restrictions:
- SIMULATED is the only enabled mode today.
- Must be explicitly labeled in all UI and logs.

#### TESTBED
Definition:
- A future isolated genuine testbed such as Home Assistant, if truly connected.

Purpose:
- Allow controlled environment testing without live campus operations.

Restrictions:
- Not implemented now.
- Requires dedicated authorization and safety boundaries before activation.

#### REAL
Definition:
- Future authorized real control only.

Purpose:
- Real campus command execution when explicit requirements, permissions, validation, and operational readiness are satisfied.

Restrictions:
- Not implemented now.
- Must never be enabled by default.

### Data Strategy Requirements

The project must document the following facts explicitly:

- AEP is regional historical data, not campus data.
- Open-Meteo is real external weather data.
- Current AEP and Open-Meteo samples have no temporal overlap.
- EIA validation remains deferred.
- No fake campus telemetry should be introduced.

### Data Flow Model

The data flow is intentionally one-way and provenance-aware:

1. Real external and historical data are ingested and labeled.
2. Derived features and forecasts are created from the normalized inputs.
3. The deterministic decision engine evaluates opportunities and actions.
4. The execution adapter can only operate in SIMULATED mode.
5. All outputs are logged with provenance metadata.

This avoids mixing real sensor truth, simulated device state, and derived action recommendations in a way that could be mistaken for real control.

---

## 4. Agent Architecture

The agent architecture remains deterministic and bounded. It is not a free-form autonomous operator.

### Core Agent Responsibilities

The agent is responsible for:

- observing state,
- loading forecast and context,
- detecting issues/opportunities,
- generating candidate actions,
- filtering disallowed actions via constraints,
- estimating what-if impact,
- selecting the highest-confidence valid action,
- delegating execution to the adapter boundary,
- verifying the result,
- recording audit metadata.

### Architectural Rule

The deterministic decision engine is the authoritative logic. It does not depend on live control or a live LLM to make a valid decision.

The agent architecture is intentionally separated into:

- data ingest layer,
- context/feature assembly,
- opportunity detection,
- action generation,
- safety/constraint enforcement,
- scoring and selection,
- execution adapter,
- verification layer,
- audit/logging layer.

This allows future expansion without rewriting the decision engine or altering the control semantics.

---

## 5. LLM Boundary

The LLM boundary is intentionally limited and non-authoritative.

### LLM May Handle

The LLM may handle:

- natural-language interaction,
- explanations,
- summaries,
- intent interpretation,
- presenting deterministic results.

### The LLM Must NOT Do

The LLM must not:

- control devices directly,
- replace forecasting,
- replace constraints,
- replace safety validation,
- replace optimization/decision logic,
- replace verification.

### LLM API Design

This architecture defines the interface as:

#### C. LLM API

Purpose:
- Accept user prompts and structured deterministic outputs.
- Return human-readable explanations, summaries, or intent interpretations.
- Present an action recommendation along with provenance and audit details.

Constraints:
- The LLM only consumes already-determined results.
- It is not a source of truth for action selection.
- It cannot issue control commands.
- It cannot suppress audit metadata.
- It must not be used to override safety enforcement or verification.

This is a presentation and explanation boundary only.

---

## 6. Control/Execution Architecture

The project must maintain a clean adapter-based control boundary.

### Execution Modes

Current enabled mode:

- SIMULATED

Future modes intentionally deferred:

- TESTBED
- REAL

### Interface A: DATA API

Purpose:
- Provide normalized data and context to the deterministic engine.
- Supply read-only information, forecasts, and derived context.

Expected responsibility:
- Return labeled data objects with provenance.
- Keep historical, external, and derived sources distinct.
- Avoid mixing real and simulated state in the same schema without explicit labels.

### Interface B: CONTROL/ACTION API

Purpose:
- Encapsulate device execution semantics behind a consistent action boundary.
- Allow the decision engine to request an action without directly coupling to a specific device implementation.

Current implementation semantics:
- SIMULATED only.
- The adapter performs a simulated action and readback verification.
- The result must be treated as a decision artifact, not a claim of real control.

Future extensibility:
- TESTBED and REAL adapters can be added later without rewriting the deterministic decision engine.
- The adapter interface remains stable while execution mode changes.

### Required Control Rule

The system must not implement TESTBED or REAL execution now. The design is intentionally future-proof but currently disabled.

---

## 7. Provenance Model

Every data point, decision, and action must carry provenance metadata.

### Provenance Fields

At minimum, every record should carry:

- source type,
- source name,
- data class (REAL_HISTORICAL, REAL_EXTERNAL, DERIVED, SIMULATED, TESTBED, REAL),
- timestamp,
- collection method,
- validity status,
- whether it is raw, transformed, or derived,
- whether it is read-only,
- whether it was used for forecasting, constraint evaluation, or control.

### Provenance Principles

- Real data is never mixed with simulated control without explicit labeling.
- Derived results are marked as derived, not measured truth.
- Execution logs clearly state whether a decision was SIMULATED, TESTBED, or REAL.
- The audit trail must include the verification result and status.

### Why This Matters

This makes the system understandable in a hackathon setting and keeps the project honest about what is real versus simulated. It also prevents the dashboard from implying real operational control when none exists.

---

## 8. Proactive Runtime

The proactive runtime is a bounded simulation loop that repeatedly observes, decides, executes valid actions, verifies, and logs state transitions.

### Current State

The project already contains a completed Phase 4E.5 bounded loop that reuses the existing deterministic pipeline.

### Design Intent

This loop is not an autonomous campus control system. It is a bounded proactive simulation mechanism that can run on replayed context or a finite set of rows and generate an auditable decision sequence.

### Future Evolution

When genuine data and authorized interfaces become available, this same loop can later become a periodic runtime that:

- reads recent context,
- triggers a bounded decision cycle,
- logs outcome,
- and escalates only when a valid trusted execution mode is available.

### Current Restriction

The present runtime remains a simulation-only operational model. It must not be described as autonomous real campus control.

---

## 9. UI Architecture

The dashboard should be simple, transparent, and hackathon-friendly.

### Required Dashboard Sections

The UI must show:

- energy context,
- forecast,
- detected issue,
- diagnosis/reason,
- recommended action,
- what-if impact,
- execution status,
- verification status,
- audit history,
- provenance,
- clear SIMULATED labeling.

### UI Design Principles

- Keep the interface deterministic and explainable.
- Label all simulated elements clearly.
- Show provenance at the point of each metric or recommendation.
- Show whether the status is simulated, validated, or unverified.
- Do not imply real campus control.

### Example UI Flow

1. Select a replay timestep or scenario.
2. Show temporal context and forecast.
3. Show detected issue and reason.
4. Show recommended action and what-if savings estimate.
5. Show adapter execution status.
6. Show verification result and audit record.
7. Mark everything as SIMULATED.

---

## 10. Evaluation Metrics

The prototype must evaluate both prediction quality and operational correctness.

### Prediction Metrics

#### MAE (Mean Absolute Error)
Purpose:
- Measures average forecast error magnitude.

What it proves:
- Forecast accuracy on a scale comparable to the load values.

#### RMSE (Root Mean Squared Error)
Purpose:
- Emphasizes larger forecast errors.

What it proves:
- Sensitivity to outliers and high-error periods.

#### MAPE (Mean Absolute Percentage Error)
Purpose:
- Measures percentage error relative to actual demand.

What it proves:
- Relative forecast accuracy when comparing across load levels.

### Operational Metrics

#### Opportunity Detection
Purpose:
- Measures whether the system correctly identifies a meaningful issue or mismatch.

What it proves:
- The agent is detecting actionable situations rather than generating noise.

#### Constraint Compliance
Purpose:
- Measures whether recommended actions satisfy safety and operational rules.

What it proves:
- The decision system is not violating constraints.

#### Execution Success
Purpose:
- Measures whether the adapter executed the action without failing.

What it proves:
- The execution pathway is functioning under the enabled mode.

#### Verification Success
Purpose:
- Measures whether the system confirms the intended post-action state.

What it proves:
- The action actually matched the expected simulated readback.

#### Simulated Peak Reduction
Purpose:
- Measures load reduction in the simulated campus model.

What it proves:
- The action has a meaningful effect in the simulated environment.

#### Interval Energy Impact
Purpose:
- Quantifies the energy reduction over a reporting interval.

What it proves:
- The action has measurable operational value in the current replay window.

#### Invalid-Action Prevention
Purpose:
- Measures how often invalid, unsafe, or unapproved actions are rejected.

What it proves:
- The constraint layer is working as a protection boundary.

#### Audit Completeness
Purpose:
- Measures whether each decision contains the required provenance and lifecycle fields.

What it proves:
- The system remains explainable and reviewable.

---



---

## 11. Remaining Implementation Phases

After Phase 5.0, the remaining work is divided into future phases. Each phase below includes objective, expected files/modules, tests, provenance, dependencies, and scope restrictions.

### Phase 6.0 — Data Normalization and Provenance Hardening
Objective:
- Strengthen data validation and ensure all data structures include provenance metadata.

Expected files/modules:
- data preprocessing modules
- provenance helpers
- replay source normalization
- audit/logging helpers

Tests:
- provenance completeness checks,
- source labeling validation,
- dataset mismatch detection,
- no temporal overlap warnings,
- no simulated data mislabeled as real.

Data/execution provenance:
- REAL_HISTORICAL, REAL_EXTERNAL, DERIVED, SIMULATED tags required.

Dependencies:
- Existing deterministic replay and decision logic.

Scope restrictions:
- No real control enabled.
- No LLM integration.
- No dashboard development.

### Phase 7.0 — Operational Safety and Constraint Layer Expansion
Objective:
- Increase safety rule coverage and runtime validation for action selection.

Expected files/modules:
- analysis/constraints.py
- action validation logic
- execution guardrails

Tests:
- invalid-action prevention,
- constraint compliance metrics,
- rejection of unsafe actions,
- audit trace coverage.

Data/execution provenance:
- All rejected actions logged as denied and provenance-tagged.

Dependencies:
- Existing deterministic engine and constraint set.

Scope restrictions:
- No TESTBED or REAL control.
- No external service integration.

### Phase 8.0 — UI and Explainability Layer
Objective:
- Build a simple, interpretable interface for the deterministic results.

Expected files/modules:
- dashboard modules
- explanation formatting
- audit summary views

Tests:
- dashboard rendering smoke checks,
- provenance labeling checks,
- status labeling checks,
- no real-control implication.

Data/execution provenance:
- Every visible statistic and recommendation must include source/provenance labeling.

Dependencies:
- Existing replay and decision outputs.

Scope restrictions:
- No new backend control path.
- No LLM dependency.

### Phase 9.0 — Testbed Integration (Optional, Deferred)
Objective:
- Connect to an isolated test environment if and when a real device or automation layer is authorized.

Expected files/modules:
- adapter implementations for TESTBED mode,
- integration and safety checks,
- secure wiring for isolated environment.

Tests:
- isolated testbed dry-run validation,
- command gating tests,
- fail-safe path checks.

Data/execution provenance:
- TESTBED identity and authorization metadata required.

Dependencies:
- explicit external hardware integration and authorization.

Scope restrictions:
- Do not enable without a validated isolated environment.

### Phase 10.0 — Real Control Readiness (Future Only)
Objective:
- Prepare a production-grade real-control path only when authorized and operationally validated.

Expected files/modules:
- secure real control adapter,
- authorization and approval flows,
- real-time verification and rollback logic.

Tests:
- fail-safe and rollback tests,
- authorization enforcement,
- real-world verification checks.

Data/execution provenance:
- REAL mode with strict audit trail and governance.

Dependencies:
- signed-off operational requirements, permissions, and safety review.

Scope restrictions:
- Not implemented in current scope.
- Not active in the hackathon prototype.

---


Phase 5.0 establishes the architecture for a deterministic, provenance-aware, simulation-first prototype. It preserves the completed bounded proactive loop, keeps LLM functionality clearly non-authoritative, keeps control strictly in SIMULATED mode, and defines a future path for TESTBED and REAL activation without slipping into unsupported claims. The document intentionally does not invent APIs, external integrations, or production control capabilities that are not presently implemented.
