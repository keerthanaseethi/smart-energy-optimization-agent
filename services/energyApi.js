const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function request(path, options = {}) {
  const { timeout: timeoutMs = 20000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(fetchOptions.headers ?? {}) },
      signal: controller.signal,
      ...fetchOptions,
    });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

export const energyApi = {
  // The first state request can include model initialization; allow it to warm up.
  getState: () => request('/api/replay/state', { timeout: 60000 }),
  stepReplay: () => request('/api/replay/step', { method: 'POST' }),
  resetReplay: () => request('/api/replay/reset', { method: 'POST' }),
  selectReplayDate: (date) => request('/api/replay/select-date', { method: 'POST', body: JSON.stringify({ date }) }),
  decideCurrent: () => request('/api/agent/decide-current', { method: 'POST' }),
  executeCurrentDecision: () => request('/api/agent/execute-current', { method: 'POST' }),
  explain: (question) => request('/api/explain', {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
  downloadReplayReport: async () => {
    const response = await fetch(`${API_BASE}/api/reports/replay.pdf`);
    if (!response.ok) throw new Error('Could not generate the replay PDF');
    return response.blob();
  },
  setAgentControl: (enabled) => request('/api/agent/control', {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  }),
  setEnvironment: (values) => request('/api/environment', {
    method: 'PATCH',
    body: JSON.stringify(values),
  }),
  whatIf: () => request('/api/what-if', { method: 'POST' }),
  setDeviceAiControl: (id, enabled) => request(`/api/devices/${id}/ai-control`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  }),
  setDeviceState: (id, state) => request(`/api/devices/${id}/state`, {
    method: 'PATCH',
    body: JSON.stringify({ state }),
  }),
  setDeviceParameters: (id, parameters) => request(`/api/devices/${id}/parameters`, {
    method: 'PATCH',
    body: JSON.stringify(parameters),
  }),
  resolveAlert: (id) => request(`/api/alerts/${encodeURIComponent(id)}/resolve`, { method: 'PATCH' }),
};
