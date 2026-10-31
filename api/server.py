from __future__ import annotations

import json
import io
import re

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from api.state import runtime


def response(payload, status_code: int = 200):
    return JSONResponse(payload, status_code=status_code)


async def health(request: Request):
    return response({"status": "ok", "mode": "SIMULATED"})


async def replay_state(request: Request):
    return response(runtime.get_state())


async def replay_step(request: Request):
    return response(runtime.step())


async def replay_reset(request: Request):
    # Reset the in-memory replay session without deleting the persisted audit trail.
    return response(runtime.reset(clear_log=False))


async def replay_options(request: Request):
    return response(runtime.replay_options())


async def replay_select_date(request: Request):
    try:
        payload = await request.json()
        return response(runtime.select_replay_date(str(payload.get("date", ""))))
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    except ValueError as exc:
        return response({"detail": str(exc)}, 400)


async def decide_current(request: Request):
    return response(runtime.preview_decision())


async def execute_current_decision(request: Request):
    try:
        return response(runtime.execute_current_decision())
    except ValueError as exc:
        return response({"detail": str(exc)}, 400)
    except RuntimeError as exc:
        return response({"detail": str(exc)}, 409)


async def devices(request: Request):
    return response({"mode": "SIMULATED", "devices": runtime.devices()})


async def set_device_ai_control(request: Request):
    device_id = request.path_params["device_id"]
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    if not isinstance(payload, dict) or not isinstance(payload.get("enabled"), bool):
        return response({"detail": "'enabled' must be a boolean"}, 400)
    try:
        device = runtime.set_device_ai_control(device_id, payload["enabled"])
    except KeyError:
        return response({"detail": "Unknown simulated device"}, 404)
    return response({"mode": "SIMULATED", "device": device})


async def set_agent_control(request: Request):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    if not isinstance(payload, dict) or not isinstance(payload.get("enabled"), bool):
        return response({"detail": "'enabled' must be a boolean"}, 400)
    return response(runtime.set_agent_control(payload["enabled"]))


async def environment(request: Request):
    if request.method == "GET":
        return response({"mode": "SIMULATED", "environment": runtime.agent.campus.get_environment()})
    try:
        payload = await request.json()
        return response(runtime.set_environment(payload))
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    except ValueError as exc:
        return response({"detail": str(exc)}, 400)


async def set_device_state(request: Request):
    device_id = request.path_params["device_id"]
    try:
        payload = await request.json()
        requested_state = str(payload.get("state", "")).upper()
        result = runtime.set_device_state(device_id, requested_state)
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    except KeyError:
        return response({"detail": "Unknown simulated device"}, 404)
    except ValueError as exc:
        return response({"detail": str(exc)}, 400)
    except RuntimeError as exc:
        return response({"detail": str(exc)}, 409)
    return response(result)


async def set_device_parameters(request: Request):
    device_id = request.path_params["device_id"]
    try:
        payload = await request.json()
        result = runtime.set_device_parameters(device_id, payload)
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    except KeyError:
        return response({"detail": "Unknown simulated device"}, 404)
    except ValueError as exc:
        return response({"detail": str(exc)}, 400)
    except RuntimeError as exc:
        return response({"detail": str(exc)}, 409)
    return response(result)


async def what_if(request: Request):
    preview = runtime.preview_decision()
    preview["operation"] = "WHAT_IF_PREVIEW"
    preview["execution"] = {
        "status": "NOT_EXECUTED",
        "mode": "SIMULATED",
        "message": "What-if evaluation only; no VirtualCampus state was changed.",
    }
    return response(preview)


async def execute_simulated(request: Request):
    result = runtime.step()
    result["operation"] = "REPLAY_STEP_EXECUTION"
    return response(result)


async def decisions(request: Request):
    return response({"decisions": runtime.decision_history(), "provenance": "SIMULATED"})


async def analytics(request: Request):
    history = runtime.decision_history()
    return response(runtime.analytics(history))


async def alerts(request: Request):
    return response({"alerts": runtime.alerts(runtime.decision_history())})


async def resolve_alert(request: Request):
    return response(runtime.resolve_alert(request.path_params["alert_id"]))


async def explain(request: Request):
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return response({"detail": "Request body must be valid JSON"}, 400)
    return response(runtime.explain(payload.get("question", "")))


def _pdf_escape(value: str) -> str:
    return re.sub(r"([\\()])", r"\\\1", value)


def _build_report_pdf() -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    state = runtime.get_state()
    current = state.get("current", {}).get("state", {})
    decision = state.get("current", {}).get("decision", {})
    forecast = (current.get("Forecast") or {}).get("forecast_MW")
    action = (decision.get("action") or {}).get("action", "No action")
    reason = (decision.get("opportunity") or {}).get("reason", "No opportunity recorded.")
    timestamp = state.get("replay", {}).get("source_timestamp", "N/A")
    timeline = state.get("analytics", {}).get("timeline", [])
    horizon = timeline[:8]
    if forecast is not None:
        horizon = [{"time": timestamp, "referenceDemandMW": current.get("Reference_Demand_MW"), "forecastMW": forecast}] + horizon[1:]
    devices = state.get("devices", [])
    output = io.BytesIO()
    with PdfPages(output) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.08, 0.95, "KAIRA | Situation-aware Energy Operations Report", fontsize=18, weight="bold")
        fig.text(0.08, 0.925, f"Current replay row: {timestamp}", fontsize=9, color="#475569")
        y = 0.87
        sections = [
            ("Executive summary", "This report explains the current replay situation, the deterministic forecast, the simulated VirtualCampus state, and the next safe decision. It is designed for review and presentation, not physical control."),
            ("Current situation", f"Historical AEP demand: {current.get('Reference_Demand_MW', 'N/A')} MW (REAL_HISTORICAL). Derived XGBoost forecast: {forecast if forecast is not None else 'N/A'} MW. VirtualCampus load: {current.get('Campus_Demand_MW', 'N/A')} MW (SIMULATED)."),
            ("Decision and why", f"Selected action: {action}. Reason: {reason} Agent control is {'ON' if state.get('agent_control_enabled') else 'OFF; recommendations only'}."),
            ("What happens next", "The chart on the next page shows the selected replay window and the available derived forecast point. Future points are not invented when the model does not provide them; the report labels that limitation explicitly."),
            ("Truth boundary", "AEP values are regional historical reference data. Device values, VirtualCampus behavior, actions, and verification are simulated. No physical telemetry or physical command is represented."),
        ]
        for title, text in sections:
            fig.text(0.08, y, title, fontsize=11, weight="bold", color="#146b4c")
            y -= 0.025
            fig.text(0.08, y, text, fontsize=9, wrap=True, va="top")
            y -= 0.075
        fig.text(0.08, y, "Device evidence", fontsize=11, weight="bold", color="#146b4c")
        y -= 0.03
        for device in devices:
            model = device.get("deviceModel", {})
            fig.text(0.1, y, f"{device.get('name')}: {device.get('rawState')} | actual {device.get('actualPower')} MW | expected {device.get('expectedPower')} MW | model {model.get('id')} | provenance {model.get('provenance')}", fontsize=7.5)
            y -= 0.032
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, axes = plt.subplots(2, 1, figsize=(8.27, 11.69), constrained_layout=True)
        labels = [str(item.get("time", ""))[-8:] for item in horizon]
        historical = [item.get("referenceDemandMW") for item in horizon]
        predictions = [item.get("forecastMW") for item in horizon]
        axes[0].plot(labels, historical, marker="o", label="Historical AEP (REAL_HISTORICAL)", color="#d7a84f")
        axes[0].plot(labels, predictions, marker="o", label="XGBoost forecast (DERIVED)", color="#1c9b6e")
        axes[0].set_title("Current replay and available near-term forecast")
        axes[0].set_ylabel("Demand (MW)")
        axes[0].tick_params(axis="x", rotation=35, labelsize=7)
        axes[0].grid(alpha=.25)
        axes[0].legend(fontsize=8)
        names = [device.get("name", "") for device in devices]
        loads = [float(device.get("actualPower") or 0) for device in devices]
        axes[1].bar(names, loads, color=["#7c4fe0", "#2e6fe0", "#d7a84f", "#1c9b6e"])
        axes[1].set_title("Current simulated VirtualCampus device load")
        axes[1].set_ylabel("Power (MW)")
        axes[1].tick_params(axis="x", rotation=20, labelsize=8)
        axes[1].grid(axis="y", alpha=.25)
        fig.text(0.01, 0.01, "Interpretation: this figure combines regional historical/forecast context with simulated device state. It is not a physical-campus measurement.", fontsize=7, color="#475569")
        pdf.savefig(fig)
        plt.close(fig)
    return output.getvalue()


async def replay_report(request: Request):
    return Response(
        _build_report_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=kaira-replay-report.pdf"},
    )


routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/replay/state", replay_state, methods=["GET"]),
    Route("/api/replay/step", replay_step, methods=["POST"]),
    Route("/api/replay/reset", replay_reset, methods=["POST"]),
    Route("/api/replay/options", replay_options, methods=["GET"]),
    Route("/api/replay/select-date", replay_select_date, methods=["POST"]),
    Route("/api/agent/decide-current", decide_current, methods=["POST"]),
    Route("/api/agent/execute-current", execute_current_decision, methods=["POST"]),
    Route("/api/devices", devices, methods=["GET"]),
    Route("/api/devices/{device_id}/ai-control", set_device_ai_control, methods=["PATCH"]),
    Route("/api/agent/control", set_agent_control, methods=["PATCH"]),
    Route("/api/environment", environment, methods=["GET", "PATCH"]),
    Route("/api/devices/{device_id}/state", set_device_state, methods=["PATCH"]),
    Route("/api/devices/{device_id}/parameters", set_device_parameters, methods=["PATCH"]),
    Route("/api/what-if", what_if, methods=["POST"]),
    Route("/api/actions/execute-simulated", execute_simulated, methods=["POST"]),
    Route("/api/decisions", decisions, methods=["GET"]),
    Route("/api/analytics", analytics, methods=["GET"]),
    Route("/api/alerts", alerts, methods=["GET"]),
    Route("/api/alerts/{alert_id}/resolve", resolve_alert, methods=["PATCH"]),
    Route("/api/explain", explain, methods=["POST"]),
    Route("/api/reports/replay.pdf", replay_report, methods=["GET"]),
]


app = Starlette(debug=True, routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
