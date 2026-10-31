import json

import pytest
from starlette.testclient import TestClient

import api.server as server
import api.state as state_module
from api.state import SmartEnergyRuntime
from simulation.decision_log import DecisionLogger


@pytest.fixture
def isolated_runtime(tmp_path, monkeypatch):
    runtime_file = tmp_path / "runtime_state.json"
    ui_file = tmp_path / "ui_state.json"
    monkeypatch.setattr(state_module, "RUNTIME_STATE_FILE", runtime_file)
    monkeypatch.setattr(state_module, "UI_STATE_FILE", ui_file)
    runtime = SmartEnergyRuntime()
    runtime.logger = DecisionLogger(tmp_path / "decisions.csv")
    monkeypatch.setattr(server, "runtime", runtime)
    return runtime


def test_ev_on_off_changes_load_and_state(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "ON")
    on_load = runtime.agent.get_campus_load()
    result = runtime.set_device_state("ev_charging", "OFF")

    assert result["device"]["rawState"] == "OFF"
    assert result["device"]["power"] == 0.0
    assert on_load == pytest.approx(1.2)
    assert runtime.agent.get_campus_load() == pytest.approx(0.0)


def test_ev_off_on_and_hvac_off(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "ON")
    runtime.set_device_state("ev_charging", "OFF")
    assert runtime.set_device_state("ev_charging", "ON")["device"]["rawState"] == "ON"
    assert runtime.set_device_state("hvac", "OFF")["device"]["rawState"] == "OFF"


def test_invalid_device_and_state_are_rejected(isolated_runtime):
    with pytest.raises(KeyError):
        isolated_runtime.set_device_state("solar_array", "ON")
    with pytest.raises(ValueError):
        isolated_runtime.set_device_state("ev_charging", "ECO")


def test_invalid_api_state_is_rejected(isolated_runtime):
    response = TestClient(server.app).patch(
        "/api/devices/ev_charging/state", json={"state": "ECO"}
    )
    assert response.status_code == 400


def test_ai_control_api_rejects_invalid_payload(isolated_runtime):
    client = TestClient(server.app)
    assert client.patch("/api/devices/hvac/ai-control", content="{").status_code == 400
    assert client.patch("/api/devices/hvac/ai-control", json={"enabled": "yes"}).status_code == 400


def test_manual_control_is_simulated_and_distinct_from_agent(isolated_runtime):
    runtime = isolated_runtime
    result = runtime.set_device_state("hvac", "OFF")
    record = runtime.decision_history()[-1]

    assert result["execution"]["status"] == "SIMULATED"
    assert result["execution"]["control_origin"] == "USER_SIMULATED_CONTROL"
    assert result["device"]["provenance"] == "SIMULATED"
    assert record["Control_Origin"] == "USER_SIMULATED_CONTROL"
    assert record["Execution_Provenance"] == "SIMULATED"


def test_runtime_state_survives_restart(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "OFF")
    persisted = json.loads(state_module.RUNTIME_STATE_FILE.read_text(encoding="utf-8"))
    restarted = SmartEnergyRuntime()

    assert persisted["device_states"]["EV Charging"] == "OFF"
    assert restarted.agent.campus.get_state()["EV Charging"] == "OFF"
    assert restarted.agent.campus.get_total_load() == pytest.approx(runtime.agent.campus.get_total_load())


def test_hvac_setpoint_changes_backend_load_and_persists(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("hvac", "ON")
    baseline = runtime.agent.campus.get_total_load()
    result = runtime.set_device_parameters("hvac", {"setpoint_c": 20})

    assert result["device"]["parameters"]["setpoint_c"] == 20.0
    assert result["device"]["power"] <= baseline
    restarted = SmartEnergyRuntime()
    assert restarted.agent.campus.hvac.setpoint_c == 20.0


def test_lighting_brightness_changes_backend_load(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("lighting", "ON")
    result = runtime.set_device_parameters("lighting", {"brightness_pct": 50})

    assert result["device"]["parameters"]["brightness_pct"] == 50.0
    assert result["device"]["power"] == pytest.approx(0.15)


def test_parameter_api_rejects_unsupported_values(isolated_runtime):
    client = TestClient(server.app)
    response = client.patch("/api/devices/hvac/parameters", json={"setpoint_c": 40})
    assert response.status_code == 400


def test_disabled_ai_control_keeps_agent_action_recommendation_only(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_ai_control("hvac", False)
    result = runtime.step()

    assert result["current"]["decision"]["action"]["action"] in {
        "Do Nothing",
        "Reduce Academic HVAC",
        "Turn Academic HVAC OFF",
    }
    if result["decisions"][0]["Selected_Action"] != "Do Nothing":
        assert result["decisions"][0]["Execution_Status"] == "NOT_EXECUTED"


def test_audit_history_orders_latest_runtime_event_first(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("hvac", "OFF")
    runtime.step()
    history = runtime.decision_history()

    assert history[0]["Audit_Logged_At"] >= history[1]["Audit_Logged_At"]


def test_replay_state_and_devices_share_virtual_campus(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "OFF")

    device = next(item for item in runtime.devices() if item["id"] == "ev_charging")
    replay_state = runtime.get_state()

    assert device["rawState"] == "OFF"
    assert replay_state["devices"][2]["rawState"] == "OFF"
    assert replay_state["current"]["state"]["Campus_Demand_MW"] == pytest.approx(1.1)


def test_device_state_api_updates_devices_and_replay_state(isolated_runtime):
    client = TestClient(server.app)
    response = client.patch("/api/devices/ev_charging/state", json={"state": "OFF"})
    assert response.status_code == 200
    assert response.json()["execution"]["control_origin"] == "USER_SIMULATED_CONTROL"
    assert client.get("/api/devices").json()["devices"][2]["rawState"] == "OFF"
    assert client.get("/api/replay/state").json()["devices"][2]["rawState"] == "OFF"


def test_agent_control_off_keeps_recommendation_without_execution(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_agent_control(False)
    result = runtime.step()
    record = result["decisions"][0]
    assert result["agent_control_enabled"] is False
    assert record["Control_Origin"] == "AGENT_RECOMMENDATION_ONLY" or record["Selected_Action"] == "Do Nothing"
    assert record["Execution_Status"] in {"NOT_EXECUTED", "NO_ACTION"}


def test_reset_returns_to_opportunity_window_and_active_agent_decision(isolated_runtime):
    runtime = isolated_runtime
    runtime.select_replay_date("2017-08-01")

    runtime.reset(clear_log=False)

    assert runtime.data["Datetime"].iloc[0].date().isoformat() == "2017-03-15"
    assert runtime.preview_decision()["decision"]["action"]["action"] != "Do Nothing"


def test_environment_inputs_are_controllable_and_persist(isolated_runtime):
    runtime = isolated_runtime
    result = runtime.set_environment({
        "occupancy_pct": 85,
        "outdoor_temperature_c": 35,
        "outdoor_humidity_pct": 70,
        "indoor_temperature_c": 24,
        "indoor_humidity_pct": 55,
    })
    assert result["environment"]["occupancy_pct"] == 85.0
    state = runtime.get_state()
    assert state["environment"]["outdoor_temperature_c"] == 35.0
    assert state["current"]["state"]["Environmental_Context"]["provenance"] == "SIMULATED"


def test_agent_control_endpoint_is_explicitly_simulated(isolated_runtime):
    client = TestClient(server.app)
    response = client.patch("/api/agent/control", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["agent_control_enabled"] is False
    assert "no agent action" in response.json()["message"].lower()


def test_aep_replay_context_does_not_overwrite_virtual_environment(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_environment({
        "outdoor_temperature_c": 21,
        "indoor_temperature_c": 19,
        "occupancy_pct": 5,
    })

    state = runtime.get_state()

    assert state["environment"]["outdoor_temperature_c"] == 21.0
    assert state["environment"]["indoor_temperature_c"] == 19.0
    assert state["environment"]["occupancy_pct"] == 5.0
    assert state["current"]["state"]["Temperature"] != 21.0
    assert state["current"]["state"]["Environmental_Context"]["outdoor_temperature_c"] != 21.0


def test_aep_replay_step_preserves_virtual_device_state(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "OFF")
    runtime.set_environment({"main_power": False})
    before = (
        runtime.agent.campus.get_state().copy(),
        runtime.agent.campus.get_environment().copy(),
    )

    runtime.step()

    assert runtime.agent.campus.get_state() == before[0]
    assert runtime.agent.campus.get_environment() == before[1]


def test_main_power_is_independent_from_appliance_state_and_load(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("hvac", "ON")
    runtime.set_device_state("lighting", "ON")
    active_load = runtime.agent.campus.get_total_load()

    result = runtime.set_environment({"main_power": False})

    assert result["environment"]["main_power"] is False
    assert runtime.agent.campus.get_state()["HVAC"] == "ON"
    assert runtime.agent.campus.get_state()["Lighting"] == "ON"
    assert runtime.agent.campus.get_total_load() == 0.0
    assert active_load > 0

    runtime.set_environment({"main_power": True})
    assert runtime.agent.campus.get_total_load() == pytest.approx(active_load)


def test_main_power_persists_without_erasing_device_states(isolated_runtime):
    runtime = isolated_runtime
    runtime.set_device_state("ev_charging", "ON")
    runtime.set_environment({"main_power": False})

    persisted = json.loads(state_module.RUNTIME_STATE_FILE.read_text(encoding="utf-8"))
    restarted = SmartEnergyRuntime()

    assert persisted["environment"]["main_power"] is False
    assert persisted["device_states"]["EV Charging"] == "ON"
    assert restarted.agent.campus.environment.main_power is False
    assert restarted.agent.campus.get_state()["EV Charging"] == "ON"
    assert restarted.agent.campus.get_total_load() == 0.0


def test_main_power_api_and_device_api_remain_independent(isolated_runtime):
    client = TestClient(server.app)
    client.patch("/api/devices/ev_charging/state", json={"state": "ON"})

    power_response = client.patch("/api/environment", json={"main_power": False})
    assert power_response.status_code == 200
    assert power_response.json()["environment"]["main_power"] is False
    assert client.get("/api/devices").json()["devices"][2]["rawState"] == "ON"
    assert client.get("/api/devices").json()["devices"][2]["power"] == 0.0

    client.patch("/api/devices/ev_charging/state", json={"state": "OFF"})
    assert client.get("/api/environment").json()["environment"]["main_power"] is False
