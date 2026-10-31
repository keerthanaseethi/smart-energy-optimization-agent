"""Read-only tools permitted at the LLM boundary."""

from __future__ import annotations

from typing import Any, Mapping, Optional

import pandas as pd


class EnergyReadTools:
    """Expose structured energy results without exposing execution methods."""

    def __init__(self, results: Optional[pd.DataFrame] = None):
        self.results = results if results is not None else pd.DataFrame()

    def _latest(self) -> dict[str, Any]:
        if self.results.empty:
            return {}
        return self.results.iloc[-1].to_dict()

    def get_current_energy_context(self) -> dict[str, Any]:
        row = self._latest()
        return {
            key: row.get(key)
            for key in (
                "Datetime", "Campus_Demand_MW", "Campus_Baseline_MW",
                "Campus_Deviation_MW", "Reference_Demand_MW", "Temperature_C",
                "Occupancy", "Tariff", "Provenance_Metadata",
            )
            if key in row
        }

    def get_forecast(self) -> dict[str, Any]:
        row = self._latest()
        return {key: row.get(key) for key in ("Forecast_Datetime", "Forecast_MW") if key in row}

    def get_latest_opportunity(self) -> dict[str, Any]:
        row = self._latest()
        return {
            key: row.get(key)
            for key in ("Opportunity", "Severity", "Opportunity_Reason", "Selected_Action")
            if key in row
        }

    def explain_decision(self) -> dict[str, Any]:
        row = self._latest()
        return {
            key: row.get(key)
            for key in (
                "Datetime", "Opportunity", "Opportunity_Reason", "Selected_Action",
                "What_If_Estimated_Impact_MW", "Validation_Status", "Safety_Status",
                "Rejection_Reason", "Rule_ID", "Execution_Status", "Verification_Status",
                "Impact_Semantics", "Execution_Mode", "Provenance_Metadata",
            )
            if key in row
        }

    def get_audit_history(self) -> list[dict[str, Any]]:
        if self.results.empty:
            return []
        return self.results.to_dict(orient="records")

    def get_replay_summary(self) -> dict[str, Any]:
        if self.results.empty:
            return {"observations": 0, "provenance": "SIMULATED"}
        return {
            "observations": int(len(self.results)),
            "actions": self.results["Action"].value_counts().to_dict() if "Action" in self.results else {},
            "total_peak_reduction_MW": float(self.results.get("Peak_Reduction_MW", pd.Series(dtype=float)).sum()),
            "total_interval_energy_impact_MWh": float(
                self.results.get("Interval_Energy_Impact_MWh", pd.Series(dtype=float)).sum()
            ),
            "provenance": "SIMULATED",
        }
