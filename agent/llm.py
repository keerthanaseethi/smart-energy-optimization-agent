"""Energy-only Groq explanation boundary with full LLM conversational intelligence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol

from integrations.config import ConfigurationError, get_config_value, require_config_value


REFUSAL = (
    "I can answer any questions related to energy consumption, forecasting, "
    "optimization, device physics, data provenance, and general assistant topics."
)


class LLMConfigurationError(RuntimeError):
    pass


class LLMProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        ...


class EnergyDomainGuard:
    """Application-level domain guard allowing user queries."""

    def classify(self, question: str) -> str:
        if not isinstance(question, str) or not question.strip():
            return "REJECTED"
        return "ACCEPTED"

    def check(self, question: str) -> tuple[bool, str]:
        return True, ""


@dataclass
class GroqProvider:
    model: str = "qwen/qwen3.8-27b"
    env_file: str = ".env"

    def __post_init__(self) -> None:
        try:
            self.api_key = require_config_value("GROQ_API_KEY", self.env_file)
        except ConfigurationError as exc:
            raise LLMConfigurationError(str(exc)) from exc

        # Model candidates list in order of preference
        self.candidate_models = [
            self.model,
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b",
            "groq/compound-mini",
            "llama3-70b-8192",
            "llama3-8b-8192",
        ]

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            from groq import Groq
        except ImportError as exc:
            raise LLMConfigurationError(
                "Groq SDK is not installed. Install the groq requirement."
            ) from exc

        client = Groq(api_key=self.api_key)
        
        last_exception = None
        for m in self.candidate_models:
            if not m:
                continue
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=600,
                )
                self.model = m
                return response.choices[0].message.content
            except Exception as exc:
                last_exception = exc
                continue

        raise RuntimeError(f"Groq API call failed across candidates: {last_exception}")

    @property
    def metadata(self) -> dict[str, str]:
        return {"provider": "Groq", "model": self.model, "provenance": "REAL_EXTERNAL:Groq"}


class GroundedEnergyAssistant:
    """Natural-language explanation over deterministic structured results using Groq LLM."""

    def __init__(self, provider: Optional[LLMProvider] = None, guard: Optional[EnergyDomainGuard] = None):
        self.provider = provider
        self.guard = guard or EnergyDomainGuard()

    def _compact_context(self, context: Mapping[str, Any]) -> dict[str, Any]:
        """Extract a clean, lightweight context summary to avoid payload size limit issues."""
        state = context.get("current", {}).get("state", {}) if isinstance(context.get("current"), Mapping) else {}
        decision = context.get("current", {}).get("decision", {}) if isinstance(context.get("current"), Mapping) else {}
        action = decision.get("action", {}) if isinstance(decision, Mapping) else {}
        opportunity = decision.get("opportunity", {}) if isinstance(decision, Mapping) else {}
        devices = context.get("devices", [])

        ts = str(state.get("Datetime", "")).replace("T", " ")

        device_summary = []
        if isinstance(devices, list):
          for d in devices:
              if isinstance(d, dict):
                  device_summary.append({
                      "name": d.get("name"),
                      "state": d.get("rawState"),
                      "power_MW": d.get("power"),
                  })

        return {
            "timestamp": ts,
            "campus_demand_MW": state.get("Campus_Demand_MW"),
            "reference_demand_MW": state.get("Reference_Demand_MW"),
            "forecast_MW": (state.get("Forecast") or {}).get("forecast_MW") if isinstance(state.get("Forecast"), dict) else None,
            "outdoor_temp_c": state.get("Temperature"),
            "occupancy_pct": state.get("Academic_Occupancy"),
            "tariff": state.get("Tariff"),
            "active_action": action.get("action", "Do Nothing"),
            "estimated_saving_MW": action.get("estimated_saving_MW", 0.0),
            "opportunity": opportunity.get("reason"),
            "devices": device_summary,
        }

    def answer(self, question: str, context: Mapping[str, Any]) -> dict[str, Any]:
        if self.provider is None:
            try:
                self.provider = build_groq_assistant()
            except Exception:
                pass

        compact = self._compact_context(context)
        compact_json = json.dumps(compact, default=str)

        system_prompt = (
            "You are KAIRA, a friendly, intelligent, highly communicative AI Energy Assistant. "
            "Respond conversationally using clean paragraphs, bullet points, and bold metrics. "
            "CRITICAL: Do NOT output raw markdown table syntax (do NOT use ASCII pipe columns like |---|---|). "
            "Instead, summarize key findings, metrics, and recommendations in warm, professional, communicatable text.\n\n"
            f"LIVE CAMPUS OPERATIONAL DATA: {compact_json}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        if self.provider is not None:
            try:
                answer = self.provider.complete(messages)
                metadata = getattr(self.provider, "metadata", {"provider": "Groq"})
                return {
                    "answer": answer,
                    "status": "GROQ_LLM_ANSWER",
                    "response_type": self._response_type(question, context),
                    "provenance": "REAL_EXTERNAL:Groq",
                    "provider": metadata,
                    "grounded_context": compact,
                }
            except Exception as exc:
                print(f"Groq provider error: {exc}")

        # Fallback to local grounded assistant answer
        return {
            "answer": self._fallback_answer(question, context),
            "status": "ANSWERED_FALLBACK",
            "response_type": self._response_type(question, context),
            "provenance": "DERIVED",
            "provider": None,
            "grounded_context": compact,
        }

    def _fallback_answer(self, question: str, context: Mapping[str, Any]) -> str:
        """Answer common operational questions without inventing values or requiring Groq."""
        state = context.get("current", {}).get("state", {}) if isinstance(context.get("current"), Mapping) else {}
        decision = context.get("current", {}).get("decision", {}) if isinstance(context.get("current"), Mapping) else {}
        what_if = context.get("what_if_result")
        forecast = (state.get("Forecast") or {}).get("forecast_MW")
        historical = state.get("Reference_Demand_MW")
        campus = state.get("Campus_Demand_MW")
        device_predictions = state.get("Device_Predictions", {})
        opportunity = (decision.get("opportunity") or {}).get("reason") or "No active opportunity is recorded."
        decisions = context.get("decisions") or []
        lower = question.lower()

        if what_if:
            return (
                f"What-if for {what_if.get('action', 'the requested action')}: "
                f"{what_if.get('baseline_power_kw', 0.0):.3f} kW baseline to "
                f"{what_if.get('candidate_power_kw', 0.0):.3f} kW candidate, a "
                f"{abs(what_if.get('delta_power_kw', 0.0)):.3f} kW simulated power change. "
                f"Interval energy impact is {abs(what_if.get('energy_delta_kwh', 0.0)):.3f} kWh."
            )
        if any(term in lower for term in ("what did", "how much did", "after your action", "save")):
            latest = decisions[-1] if decisions else None
            if latest:
                return (
                    f"The latest recorded action was {latest.get('Action', ' unavailable')}. "
                    f"Execution status was {latest.get('Execution_Status', 'unknown')}. "
                    f"Simulated interval reduction was {latest.get('Energy_Reduction_MWh', 0.0):.4f} MWh "
                    f"({latest.get('Peak_Reduction_MW', 0.0):.4f} MW)."
                )
            return "No previous agent action is recorded, so no simulated savings can be reported."
        if "forecast" in lower or "predict" in lower:
            return f"The current XGBoost forecast is {forecast:.1f} MW." if isinstance(forecast, (int, float)) else "No forecast is available for the selected replay row."
        if "hvac" in lower:
            prediction = device_predictions.get("hvac", {})
            power = prediction.get("predicted_power_kw")
            model = prediction.get("model_used")
            return (
                f"HVAC is {state.get('Academic_HVAC', 'ON')} in the simulated VirtualCampus. "
                f"The model predicts {power:.1f} kW using {model}. Context: {opportunity}"
                if isinstance(power, (int, float))
                else "HVAC prediction is currently active."
            )
        if "pump" in lower:
            prediction = device_predictions.get("water_pump", {})
            power = prediction.get("predicted_power_kw")
            model = prediction.get("model_used")
            return (
                f"Water Pump is {state.get('Water Pump', 'ON')} in the simulated VirtualCampus. "
                f"The model predicts {power:.1f} kW using {model}."
                if isinstance(power, (int, float))
                else "Water Pump prediction is currently active."
            )
        if "action" in lower or "recommend" in lower or "decision" in lower or "why" in lower:
            action = (decision.get("action") or {}).get("action") or "Do Nothing"
            return f"The deterministic agent selected '{action}'. Reason: {opportunity}"
        
        return (
            f"Hello! I am KAIRA, your AI energy assistant powered by Groq LLM. "
            f"Current campus load is {campus:.2f} MW, with historical AEP demand at {historical:.1f} MW "
            f"and XGBoost forecast at {forecast:.1f} MW. Feel free to ask me any question!"
            if all(isinstance(v, (int, float)) for v in (historical, forecast, campus))
            else "Hello! I am KAIRA, your AI assistant powered by Groq LLM. How can I help you today?"
        )

    def _response_type(self, question: str, context: Mapping[str, Any]) -> str:
        lower = question.lower()
        if "what if" in lower or "what happens if" in lower:
            return "INFORMATION"
        if any(term in lower for term in ("do it", "execute", "turn off", "switch")):
            return "EXECUTION_RESULT"
        if any(term in lower for term in ("should", "optimize", "recommend")):
            return "RECOMMENDATION"
        return "INFORMATION"


def build_groq_assistant(env_file: str = ".env") -> GroundedEnergyAssistant:
    model = get_config_value("GROQ_MODEL", env_file) or "qwen/qwen3.8-27b"
    return GroundedEnergyAssistant(provider=GroqProvider(model=model, env_file=env_file))
