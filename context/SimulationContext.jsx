import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { energyApi } from '../services/energyApi.js';

const SimulationContext = createContext(null);

export function SimulationProvider({ children }) {
  const [state, setState] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestInFlight = useRef(false);

  const loadState = useCallback(async ({ silent = false } = {}) => {
    if (requestInFlight.current) return null;
    requestInFlight.current = true;
    if (!silent) setLoading(true);
    try {
      const payload = await energyApi.getState();
      setState(payload);
      setError(null);
      return payload;
    } catch (err) {
      // Background polling must not replace a working dashboard with a transient error.
      if (!silent) {
        setError(err.name === 'AbortError' ? 'The backend is still warming up. Retrying…' : err.message);
      }
      return null;
    } finally {
      requestInFlight.current = false;
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadState();
    const interval = window.setInterval(() => loadState({ silent: true }), 3000);
    return () => window.clearInterval(interval);
  }, [loadState]);

  const nextStep = useCallback(async () => {
    const payload = await energyApi.stepReplay();
    setState(payload);
    return payload;
  }, []);

  const reset = useCallback(async () => {
    const payload = await energyApi.resetReplay();
    setState(payload);
    return payload;
  }, []);

  const selectReplayDate = useCallback(async (date) => {
    const payload = await energyApi.selectReplayDate(date);
    setState(payload);
    return payload;
  }, []);

  const toggleDeviceControl = useCallback(async (id) => {
    const current = state?.devices?.find((device) => device.id === id);
    if (!current) return null;
    const payload = await energyApi.setDeviceAiControl(id, !current.aiControl);
    await loadState({ silent: true });
    return payload;
  }, [loadState, state?.devices]);

  const setDeviceState = useCallback(async (id, deviceState) => {
    const payload = await energyApi.setDeviceState(id, deviceState);
    await loadState({ silent: true });
    return payload;
  }, [loadState]);

  const setDeviceParameters = useCallback(async (id, parameters) => {
    const payload = await energyApi.setDeviceParameters(id, parameters);
    await loadState({ silent: true });
    return payload;
  }, [loadState]);

  const decideCurrent = useCallback(async () => energyApi.decideCurrent(), []);

  const executeCurrentDecision = useCallback(async () => {
    const payload = await energyApi.executeCurrentDecision();
    await loadState({ silent: true });
    return payload;
  }, [loadState]);

  const setAgentControl = useCallback(async (enabled) => {
    const payload = await energyApi.setAgentControl(enabled);
    await loadState({ silent: true });
    return payload;
  }, [loadState]);

  const setEnvironment = useCallback(async (values) => {
    const payload = await energyApi.setEnvironment(values);
    await loadState({ silent: true });
    return payload;
  }, [loadState]);

  const runSimulation = useCallback(async () => {
    const payload = await energyApi.whatIf();
    const result = {
      status: 'done',
      before: payload?.decision?.action?.current_demand_MW ?? payload?.state?.Campus_Demand_MW,
      after: payload?.decision?.action?.simulated_demand_MW ?? payload?.state?.Campus_Demand_MW,
      reduction: payload?.decision?.action?.estimated_saving_MW ?? 0,
      action: payload?.selected_action ?? 'Do Nothing',
      provenance: payload?.provenance ?? 'DERIVED',
      execution: payload?.execution ?? { status: 'NOT_EXECUTED', mode: 'SIMULATED' },
      raw: payload,
    };
    setSimulationResult(result);
    return result;
  }, []);

  const scenario = useMemo(() => ({
    campus: Number(state?.current?.state?.Campus_Demand_MW ?? 0),
    occupancy: Number(state?.current?.state?.Academic_Occupancy ?? 0),
    time: state?.replay?.timestamp ?? state?.current?.state?.Datetime,
    action: state?.current?.decision?.action?.action ?? 'Do Nothing',
    reduction: Number(state?.current?.decision?.action?.estimated_saving_MW ?? 0),
  }), [state]);

  const resolveAlert = useCallback(async (id) => {
    await energyApi.resolveAlert(id);
    await loadState({ silent: true });
  }, [loadState]);

  const value = useMemo(() => ({
    apiState: state,
    loading,
    error,
    mode: state?.mode ?? 'SIMULATED',
    replay: state?.replay,
    current: state?.current,
    environment: state?.environment ?? {},
    agentControlEnabled: state?.agent_control_enabled ?? true,
    devices: state?.devices ?? [],
    decisions: state?.decisions ?? [],
    analytics: state?.analytics,
    alerts: state?.alerts ?? [],
    provenance: state?.provenance,
    refresh: loadState,
    nextStep,
    reset,
    selectReplayDate,
    toggleDeviceControl,
    setDeviceState,
    setDeviceParameters,
    decideCurrent,
    executeCurrentDecision,
    setAgentControl,
    setEnvironment,
    scenario,
    simulationResult,
    runSimulation,
    resolveAlert,
  }), [state, loading, error, loadState, nextStep, reset, selectReplayDate, toggleDeviceControl, setDeviceState, setDeviceParameters, decideCurrent, executeCurrentDecision, setAgentControl, setEnvironment, scenario, simulationResult, runSimulation, resolveAlert]);

  return <SimulationContext.Provider value={value}>{children}</SimulationContext.Provider>;
}

export function useSimulation() {
  const context = useContext(SimulationContext);
  if (!context) throw new Error('useSimulation must be used inside SimulationProvider');
  return context;
}
