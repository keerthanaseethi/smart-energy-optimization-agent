import { useMemo, useState, useEffect } from 'react';
import { Car, Fan, Lightbulb, Power, ShieldCheck, Waves, X, HelpCircle, CheckCircle2, XCircle, Sparkles, BrainCircuit } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext.jsx';
import { formatNumber } from '../utils/backendMappers.js';

const APPLIANCES = [
  { id: 'hvac', label: 'Academic HVAC System', icon: Fan, desc: 'Climate control & ventilation' },
  { id: 'lighting', label: 'Academic Lighting Grid', icon: Lightbulb, desc: 'Smart academic zone lighting' },
  { id: 'ev_charging', label: 'EV Station Infrastructure', icon: Car, desc: 'EV charging infrastructure' },
  { id: 'water_pump', label: 'Campus Water Pump', icon: Waves, desc: 'Hydraulic pumping unit' },
];

export default function VirtualEnvironment() {
  const {
    environment, devices, agentControlEnabled, setEnvironment,
    setDeviceState, setDeviceParameters, setAgentControl, error,
    decideCurrent, executeCurrentDecision
  } = useSimulation();

  const [selectedId, setSelectedId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [agentQuestion, setAgentQuestion] = useState(null);
  const [decisionFeedback, setDecisionFeedback] = useState(null);
  const [lastExecutedDevice, setLastExecutedDevice] = useState(null);

  const deviceMap = useMemo(() => Object.fromEntries(devices.map((device) => [device.id, device])), [devices]);
  const selected = selectedId ? deviceMap[selectedId] : null;
  const mainPowerOn = environment?.main_power !== false;

  // Whenever environment or devices change, check if agent has a recommendation
  useEffect(() => {
    let active = true;
    async function checkAgentRecommendation() {
      try {
        const preview = await decideCurrent();
        if (!active || !preview?.decision) return;
        
        const action = preview.decision.action;
        const opportunity = preview.decision.opportunity;
        const actionName = action?.action || 'Do Nothing';
        const savingMW = action?.estimated_saving_MW || 0;

        if (actionName !== 'Do Nothing' && savingMW > 0) {
          setAgentQuestion({
            opportunity: opportunity?.type || 'OPTIMIZATION_OPPORTUNITY',
            reason: opportunity?.reason || 'Energy mismatch detected based on current inputs.',
            actionName: actionName,
            savingMW: savingMW,
            rawPreview: preview,
          });
        } else {
          setAgentQuestion(null);
        }
      } catch (err) {
        console.error('Error fetching preview decision:', err);
      }
    }

    checkAgentRecommendation();
    return () => { active = false; };
  }, [environment, devices, decideCurrent]);

  const update = async (operation) => {
    setSaving(true);
    try { 
      await operation(); 
    } finally { 
      setSaving(false); 
    }
  };

  const setMasterPower = () => update(() => setEnvironment({ main_power: !mainPowerOn }));

  const handleUserChoice = async (approved) => {
    if (!agentQuestion) return;
    setSaving(true);
    try {
      if (approved) {
        await executeCurrentDecision();
        const actionName = agentQuestion.actionName;
        let targetId = null;
        if (actionName.includes('HVAC')) targetId = 'hvac';
        else if (actionName.includes('Lighting')) targetId = 'lighting';
        else if (actionName.includes('EV')) targetId = 'ev_charging';
        
        setLastExecutedDevice(targetId);
        setTimeout(() => setLastExecutedDevice(null), 4000);

        setDecisionFeedback({
          type: 'approved',
          message: `Approved & Executed: ${agentQuestion.actionName} (Saved ${formatNumber(agentQuestion.savingMW, 2)} MW)`
        });
      } else {
        setDecisionFeedback({
          type: 'rejected',
          message: `Rejected: Kept current manual configuration for ${agentQuestion.actionName}`
        });
      }
      setAgentQuestion(null);
      setTimeout(() => setDecisionFeedback(null), 5000);
    } catch (err) {
      console.error('Error handling user decision choice:', err);
    } finally {
      setSaving(false);
    }
  };

  if (error) return <div className="rounded-lg bg-alert-light p-4 text-sm text-alert-dark">Backend unavailable: {error}</div>;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      {/* Header Banner */}
      <section className="dashboard-hero">
        <div className="hero-grid" />
        <div className="relative z-10 max-w-3xl">
          <div className="eyebrow"><span className="eyebrow-dot" /> Interactive Virtual Operating Room</div>
          <h2 className="hero-title">Manual parameter tuning & agent interactive decision control.</h2>
          <p className="hero-copy">Tune initial inputs below. When energy opportunities occur, KAIRA asks for your direct approval with interactive Yes/No choices and glowing visual feedback.</p>
          <div className="hero-meta">
            <span><ShieldCheck size={13} /> INTERACTIVE VIRTUAL LAB</span>
            <span>{saving ? 'Updating virtual environment…' : 'System connected'}</span>
          </div>
        </div>
      </section>

      {/* CONTINUOUS KAIRA AI AGENT STREAM */}
      <section className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-xl p-4 shadow-xl border border-slate-800 flex items-center gap-4">
        <div className="p-3 bg-emerald-500/20 rounded-xl text-emerald-400 shrink-0">
          <BrainCircuit size={26} className="animate-pulse" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            <Sparkles size={13} /> Continuous KAIRA Recommendation Stream
          </div>
          <p className="text-sm font-semibold text-white mt-0.5">
            {agentQuestion 
              ? `Recommendation: Execute "${agentQuestion.actionName}" to save ${formatNumber(agentQuestion.savingMW, 2)} MW.` 
              : `✓ All initial parameters balanced. Virtual campus load is optimal at ${formatNumber(devices.reduce((t, d) => t + Number(d.power || 0), 0))} MW.`
            }
          </p>
          <div className="text-xs text-slate-400 mt-0.5">
            {agentQuestion?.reason || 'System is monitoring environmental inputs continuously.'}
          </div>
        </div>
      </section>

      {/* Agent Control Switch Banner */}
      <section className="agent-control-banner">
        <div>
          <span className="section-kicker">Autonomous Agent Mode</span>
          <strong>{agentControlEnabled ? 'ON — Agent presents interactive confirmation prompts' : 'OFF — Passive recommendation mode'}</strong>
          <p>Operates independently from historical AEP replay. You can adjust initial inputs directly, and the agent will propose smart decisions.</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={agentControlEnabled}
          onClick={() => update(() => setAgentControl(!agentControlEnabled))}
          className={`agent-switch ${agentControlEnabled ? 'on' : 'off'}`}
        >
          <Power size={18} /> {agentControlEnabled ? 'AGENT ENABLED' : 'AGENT DISABLED'}
        </button>
      </section>

      {/* INTERACTIVE AGENT CONFIRMATION PROMPT (YES / NO) */}
      {agentQuestion && (
        <section className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-xl p-5 shadow-xl border border-blue-400/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-3 bg-blue-500/20 rounded-lg text-blue-300 shrink-0">
                <HelpCircle size={28} />
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold text-blue-300 uppercase tracking-wider">
                  <Sparkles size={14} /> Agent Decision Request (Interactive Question)
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Do you approve executing "{agentQuestion.actionName}"?
                </h3>
                <p className="text-sm text-blue-100/90 mt-1 max-w-2xl">
                  {agentQuestion.reason} Estimated peak load reduction: <strong className="text-emerald-300">{formatNumber(agentQuestion.savingMW, 2)} MW</strong>.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
              <button
                type="button"
                onClick={() => handleUserChoice(true)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm shadow-lg transition-transform active:scale-95"
              >
                <CheckCircle2 size={18} /> YES — Approve Action
              </button>
              <button
                type="button"
                onClick={() => handleUserChoice(false)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium text-sm transition-transform active:scale-95"
              >
                <XCircle size={18} /> NO — Reject Choice
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Decision Feedback Toast */}
      {decisionFeedback && (
        <div className={`p-4 rounded-lg flex items-center gap-3 text-sm font-medium ${decisionFeedback.type === 'approved' ? 'bg-emerald-500/10 text-emerald-700 border border-emerald-500/30' : 'bg-amber-500/10 text-amber-700 border border-amber-500/30'}`}>
          {decisionFeedback.type === 'approved' ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
          <span>{decisionFeedback.message}</span>
        </div>
      )}

      {/* Virtual Room Grid with Visual Power Switches & Blooming Effects */}
      <section className="room-shell">
        <div className="room-header">
          <div>
            <span className="section-kicker text-emerald-300">Environment Sandbox</span>
            <h3>Interactive Appliance Switches & Control Room</h3>
            <p className="room-subtitle">Adjust appliance parameters or outdoor conditions to observe agent choices.</p>
          </div>
          <button type="button" onClick={setMasterPower} className={`master-power ${mainPowerOn ? 'on' : ''}`}>
            <Power size={16} /> Main Power {mainPowerOn ? 'ON' : 'OFF'}
          </button>
        </div>

        <div className="kaira-room clean-room">
          <div className={`power-bus ${mainPowerOn ? 'live' : ''}`}>
            <Power size={22} />
            <strong>MAIN POWER BUS</strong>
            <span>{mainPowerOn ? 'POWER DISTRIBUTED' : 'MAIN SUPPLY DISCONNECTED'}</span>
          </div>

          <div className="room-window">
            OUTDOOR TEMP: {formatNumber(environment?.outdoor_temperature_c)}°C
          </div>

          {APPLIANCES.map(({ id, label, icon: Icon, desc }) => {
            const device = deviceMap[id];
            const isOn = device?.rawState !== 'OFF';
            const isBlooming = lastExecutedDevice === id;

            return (
              <button
                type="button"
                key={id}
                onClick={() => setSelectedId(id)}
                className={`room-device room-appliance relative transition-all duration-500 ${
                  isBlooming ? 'blooming-action-effect bg-emerald-500/20 border-emerald-400 shadow-2xl' : ''
                } ${!isOn ? 'room-device-off' : ''}`}
              >
                {isBlooming && (
                  <span className="absolute -top-2 bg-emerald-500 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider animate-bounce">
                    Action Executed
                  </span>
                )}
                <Icon size={34} className={isOn ? 'text-emerald-400' : 'text-slate-400'} />
                <strong>{label}</strong>

                {/* VISUAL POWER SWITCH BADGE */}
                <div className={`my-1 px-2.5 py-1 rounded-md text-xs font-bold flex items-center gap-1 border ${
                  isOn ? 'bg-emerald-500 text-white border-emerald-600' : 'bg-slate-700 text-slate-300 border-slate-600'
                }`}>
                  <Power size={12} />
                  <span>SWITCH: {device?.rawState || 'OFF'}</span>
                </div>

                <span>{formatNumber(device?.power)} MW</span>
                <small className="text-xs text-slate-400">{desc}</small>
              </button>
            );
          })}

          <div className="room-floor-label">
            INDOOR TEMP: {formatNumber(environment?.indoor_temperature_c)}°C · OCCUPANCY: {formatNumber(environment?.occupancy_pct, 0)}% · <span className="provenance-pill simulated">SIMULATED ROOM</span>
          </div>
        </div>
      </section>

      {/* Appliance Parameter Modal */}
      {selected && (
        <AppliancePanel
          device={selected}
          environment={environment}
          onClose={() => setSelectedId(null)}
          update={update}
          setEnvironment={setEnvironment}
          setDeviceState={setDeviceState}
          setDeviceParameters={setDeviceParameters}
        />
      )}

      <div className="text-xs text-ink-500">
        Total Virtual Sandbox Load: <strong>{formatNumber(devices.reduce((total, device) => total + Number(device.power || 0), 0))} MW</strong>. Calculated dynamically from current room settings.
      </div>
    </div>
  );
}

function AppliancePanel({ device, environment, onClose, update, setEnvironment, setDeviceState, setDeviceParameters }) {
  const [values, setValues] = useState(device.parameters ?? {});

  const saveParameter = (name, value) => {
    const next = { ...values, [name]: value };
    setValues(next);
    return update(() => setDeviceParameters(device.id, { [name]: value }));
  };

  const Field = ({ label, name, type = 'number', min, max, step = 1, options, value, onValue }) => (
    <label className="control-field">
      <span>{label}</span>
      {options ? (
        <select value={value ?? values[name] ?? ''} onChange={(event) => onValue ? onValue(event.target.value) : saveParameter(name, event.target.value)}>
          {options.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : (
        <input
          type={type}
          min={min}
          max={max}
          step={step}
          value={value ?? values[name] ?? ''}
          onChange={(event) => onValue ? onValue(Number(event.target.value)) : saveParameter(name, type === 'number' ? Number(event.target.value) : event.target.value)}
        />
      )}
    </label>
  );

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="device-panel" role="dialog" aria-modal="true" aria-label={`${device.name} controls`}>
        <div className="flex items-center justify-between">
          <div>
            <span className="section-kicker">Parameter Controls</span>
            <h3>{device.name}</h3>
          </div>
          <button type="button" onClick={onClose} aria-label="Close controls"><X /></button>
        </div>
        <p className="panel-note">Adjust parameters below to trigger real-time agent optimization analysis.</p>

        <label className="control-field">
          <span>Device Power State</span>
          <button
            type="button"
            className={`inline-power ${device.rawState !== 'OFF' ? 'on' : ''}`}
            onClick={() => update(() => setDeviceState(device.id, device.rawState === 'OFF' ? 'ON' : 'OFF'))}
          >
            <Power size={15} /> {device.rawState === 'OFF' ? 'OFF' : 'ON'}
          </button>
        </label>

        {device.id === 'hvac' && (
          <>
            <Field label="Outdoor Temperature (°C)" name="ambient_c" min="-40" max="60" step=".5" />
            <Field label="Indoor Temperature (°C)" name="indoor_temperature_c" min="5" max="40" value={environment.indoor_temperature_c} onValue={(val) => update(() => setEnvironment({ indoor_temperature_c: val }))} />
            <Field label="Occupancy Rate (%)" name="occupancy_pct" min="0" max="100" value={environment.occupancy_pct} onValue={(val) => update(() => setEnvironment({ occupancy_pct: val }))} />
            <Field label="Target Setpoint (16–20°C)" name="setpoint_c" min="16" max="20" step=".5" />
          </>
        )}

        {device.id === 'lighting' && (
          <>
            <Field label="Lighting Type" name="lighting_type" type="text" options={['warm', 'cool', 'standard']} />
            <Field label="Brightness Level (%)" name="brightness_pct" min="0" max="100" />
          </>
        )}

        {device.id === 'ev_charging' && (
          <>
            <Field label="Battery Charge (%)" name="current_charge_pct" min="0" max="100" />
            <Field label="Target Charge (%)" name="target_charge_pct" min="0" max="100" />
            <Field label="Departure Hour (0-23)" name="departure_hour" min="0" max="23" />
            <Field label="Charging Mode" name="charging_mode" type="text" options={['standard', 'eco', 'fast']} />
          </>
        )}

        {device.id === 'water_pump' && (
          <>
            <Field label="Moisture Level (%)" name="moisture_pct" min="0" max="100" />
            <Field label="Pressure Factor" name="pressure_factor" min=".1" max="3" step=".1" />
            <Field label="Automated Schedule" name="schedule_active" type="text" options={['true', 'false']} onValue={(val) => saveParameter('schedule_active', val === 'true')} value={values.schedule_active ? 'true' : 'false'} />
          </>
        )}
      </section>
    </div>
  );
}
