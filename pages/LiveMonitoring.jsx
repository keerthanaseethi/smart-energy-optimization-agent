import { useState, useEffect, useRef } from 'react';
import { Activity, Thermometer, Zap, Play, Pause, SkipForward, RefreshCw, Fan, Lightbulb, Car, Waves, AlertTriangle, ShieldCheck, CheckCircle, Power, Sparkles, BrainCircuit } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { useSimulation } from '../context/SimulationContext.jsx';
import { formatNumber, shortTime } from '../utils/backendMappers.js';

function TelemetryCard({ icon: Icon, title, primaryVal, primaryUnit, secondaryLabel, secondaryVal, badgeText, badgeColor }) {
  return (
    <div className="bg-white border border-ink-100 rounded-xl shadow-panel p-4 flex flex-col justify-between relative overflow-hidden">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-iot-light flex items-center justify-center text-iot-dark">
            <Icon size={18} />
          </div>
          <span className="font-display font-medium text-sm text-ink-800">{title}</span>
        </div>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badgeColor}`}>
          {badgeText}
        </span>
      </div>

      <div className="my-1">
        <div className="text-2xl font-bold font-display text-ink-900 tabular">
          {primaryVal} <span className="text-xs font-normal text-ink-500">{primaryUnit}</span>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-ink-500 pt-2 border-t border-slate-100">
        <span>{secondaryLabel}</span>
        <span className="font-semibold text-ink-700">{secondaryVal}</span>
      </div>
    </div>
  );
}

function PhysicalDeviceSwitchCard({ id, name, icon: Icon, rawState, power, expectedPower, isTargetOfAction, lastAction }) {
  const isActive = rawState === 'ON' || rawState === 'ECO';
  const isShifted = rawState === 'SHIFTED';

  return (
    <div className={`p-4 rounded-xl border transition-all duration-500 relative ${
      isTargetOfAction ? 'blooming-action-effect bg-emerald-500/10 border-emerald-500 shadow-xl' :
      isActive 
        ? 'bg-gradient-to-br from-emerald-50 to-white border-emerald-300 shadow-md' 
        : isShifted
        ? 'bg-gradient-to-br from-amber-50 to-white border-amber-300'
        : 'bg-slate-50 border-slate-200 opacity-80'
    }`}>
      {isTargetOfAction && (
        <div className="absolute -top-3 right-3 bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1 shadow-lg animate-bounce">
          <Sparkles size={11} /> Agent Action Executed
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            isActive ? 'bg-emerald-500 text-white shadow-lg' : 'bg-slate-200 text-slate-600'
          }`}>
            <Icon size={22} className={isActive ? 'animate-spin' : ''} style={{ animationDuration: id === 'hvac' ? '3s' : '0s' }} />
          </div>
          <div>
            <h4 className="font-display font-semibold text-sm text-ink-900">{name}</h4>
            <div className="text-xs text-ink-500">Baseline: {formatNumber(expectedPower)} MW</div>
          </div>
        </div>

        {/* PHYSICAL POWER SWITCH DISPLAY */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-bold text-xs shadow-inner ${
          isActive 
            ? 'bg-emerald-500 text-white border-emerald-600' 
            : isShifted
            ? 'bg-amber-500 text-white border-amber-600'
            : 'bg-slate-200 text-slate-600 border-slate-300'
        }`}>
          <Power size={14} />
          <span>{rawState || 'OFF'}</span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
        <span className="text-xs text-ink-500 font-medium">Real-Time Load</span>
        <span className="text-base font-bold text-ink-900 tabular">{formatNumber(power)} <small className="text-xs text-ink-500">MW</small></span>
      </div>

      {lastAction && lastAction !== 'Do Nothing' && (
        <div className="mt-2 text-xs bg-emerald-500/15 text-emerald-800 p-2 rounded-lg border border-emerald-500/30 flex items-center gap-1.5 font-medium">
          <CheckCircle size={13} className="shrink-0 text-emerald-600" />
          <span>Agent Action: <strong>{lastAction}</strong></span>
        </div>
      )}
    </div>
  );
}

export default function LiveMonitoring() {
  const { current, replay, analytics, loading, error, nextStep, reset, devices, decisions } = useSimulation();
  const state = current?.state;
  const decision = current?.decision;

  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const timerRef = useRef(null);

  // Auto-play interval effect
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(3000 / speedMultiplier, 300);
      timerRef.current = setInterval(async () => {
        try {
          await nextStep();
        } catch (err) {
          console.error('Auto-replay step error:', err);
          setIsPlaying(false);
        }
      }, intervalMs);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, speedMultiplier, nextStep]);

  if (loading && !state) return <div className="text-sm text-ink-500">Connecting to telemetry replay backend...</div>;
  if (error) return <div className="text-sm text-alert-dark bg-alert-light rounded-md p-4">Backend unavailable: {error}</div>;

  const campusLoad = Number(state?.Campus_Demand_MW ?? 0);
  const forecast = Number(state?.Forecast?.forecast_MW ?? 0);
  const referenceMW = Number(state?.Reference_Demand_MW ?? 0);
  const temperature = state?.Temperature;
  const occupancy = state?.Academic_Occupancy;
  const tariff = state?.Tariff;
  const timestamp = state?.Datetime;

  // Process timeline data for Chart
  const decisionTimeline = (analytics?.decisionTimeline ?? []);
  const chartData = decisionTimeline.length > 0 ? decisionTimeline : [
    {
      time: timestamp,
      referenceDemandMW: referenceMW,
      loadBeforeMW: campusLoad,
      loadAfterMW: campusLoad,
      forecastMW: forecast
    }
  ];

  const latestDecision = decisions[0];
  const activeAction = decision?.action?.action || latestDecision?.Candidate_Action || 'Do Nothing';

  const isHvacAction = activeAction.includes('HVAC');
  const isLightingAction = activeAction.includes('Lighting');
  const isEvAction = activeAction.includes('EV');

  return (
    <div className="flex flex-col gap-6 max-w-[1400px]">
      {/* Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-ink-100 rounded-xl p-4 shadow-panel">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping shrink-0" />
          <div>
            <h2 className="font-display font-semibold text-ink-900 text-base">Live Telemetry Replay & Autonomous Controls</h2>
            <p className="text-xs text-ink-500">Fast multi-source stream with automatic agent execution & glowing action feedback.</p>
          </div>
        </div>

        {/* Auto-Replay Controls */}
        <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-lg shrink-0">
          <button
            type="button"
            onClick={() => setIsPlaying(!isPlaying)}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md font-semibold text-xs transition-colors shadow-sm ${
              isPlaying ? 'bg-amber-500 text-white' : 'bg-emerald-600 text-white hover:bg-emerald-700'
            }`}
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
            {isPlaying ? 'PAUSE STREAM' : 'AUTO-PLAY STREAM'}
          </button>

          <button
            type="button"
            onClick={() => nextStep()}
            disabled={isPlaying}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-white border border-slate-200 text-ink-700 hover:bg-slate-50 text-xs font-medium disabled:opacity-50"
          >
            <SkipForward size={14} /> STEP
          </button>

          <button
            type="button"
            onClick={() => reset()}
            className="p-1.5 rounded-md bg-white border border-slate-200 text-ink-600 hover:bg-slate-50 text-xs"
            title="Reset Replay Session"
          >
            <RefreshCw size={14} />
          </button>

          <div className="flex items-center gap-1 ml-2 text-xs font-semibold text-ink-600">
            <span>Speed:</span>
            {[1, 2, 5].map((speed) => (
              <button
                key={speed}
                type="button"
                onClick={() => setSpeedMultiplier(speed)}
                className={`px-1.5 py-0.5 rounded text-[11px] ${
                  speedMultiplier === speed ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 border border-slate-200'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* CONTINUOUS KAIRA AGENT LIVE RECOMMENDATION STREAM */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white border border-slate-800 rounded-xl p-4 shadow-xl flex items-center gap-4">
        <div className="p-3 bg-emerald-500/20 rounded-xl text-emerald-400 shrink-0">
          <BrainCircuit size={26} className="animate-pulse" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            <Sparkles size={13} /> Continuous KAIRA Recommendation Stream
          </div>
          <p className="text-sm font-semibold text-white mt-0.5 truncate">
            {activeAction !== 'Do Nothing' 
              ? `Agent Executing: ${activeAction} (Reducing load by ${formatNumber(decision?.action?.estimated_saving_MW || 0.8, 1)} MW)`
              : `✓ All 4 telemetry streams nominal. Campus demand is fully optimized at ${formatNumber(campusLoad)} MW.`
            }
          </p>
          <div className="text-xs text-slate-400 mt-0.5">
            {decision?.opportunity?.reason || 'Continuous grid telemetry evaluation active. No critical mismatches detected.'}
          </div>
        </div>
      </div>

      {/* Multi-Source Telemetry Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <TelemetryCard
          icon={Activity}
          title="Grid Telemetry"
          primaryVal={formatNumber(referenceMW, 0)}
          primaryUnit="MW"
          secondaryLabel="Tariff Window"
          secondaryVal={tariff || 'Normal'}
          badgeText="AEP REGIONAL DATA"
          badgeColor="bg-blue-100 text-blue-800"
        />

        <TelemetryCard
          icon={Thermometer}
          title="Building HVAC"
          primaryVal={formatNumber(temperature, 1)}
          primaryUnit="°C"
          secondaryLabel="Academic Occupancy"
          secondaryVal={`${formatNumber(occupancy, 0)}%`}
          badgeText="HVAC TELEMETRY"
          badgeColor="bg-emerald-100 text-emerald-800"
        />

        <TelemetryCard
          icon={Car}
          title="EV Station Stream"
          primaryVal={formatNumber(devices.find(d => d.id === 'ev_charging')?.power || 0, 1)}
          primaryUnit="MW"
          secondaryLabel="EV Mode"
          secondaryVal={devices.find(d => d.id === 'ev_charging')?.rawState || 'OFF'}
          badgeText="EV SESSIONS DATA"
          badgeColor="bg-purple-100 text-purple-800"
        />

        <TelemetryCard
          icon={Waves}
          title="Hydraulic Pump"
          primaryVal={formatNumber(devices.find(d => d.id === 'water_pump')?.power || 0, 1)}
          primaryUnit="MW"
          secondaryLabel="Pump State"
          secondaryVal={devices.find(d => d.id === 'water_pump')?.rawState || 'OFF'}
          badgeText="HYDRO DATA"
          badgeColor="bg-cyan-100 text-cyan-800"
        />
      </div>

      {/* Real-Time Physical Devices Execution Panel with Power Switches & Glowing Blooming Effect */}
      <div className="bg-white border border-ink-100 rounded-xl p-5 shadow-panel">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-display font-semibold text-ink-900 text-base">Physical Appliance Power Switches & Actions</h3>
            <p className="text-xs text-ink-500">Live switch states with glowing blooming animation when agent actions take effect.</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-100 text-emerald-800">
            AUTOMATIC EXECUTION ACTIVE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <PhysicalDeviceSwitchCard
            id="hvac"
            name="Academic HVAC"
            icon={Fan}
            rawState={devices.find(d => d.id === 'hvac')?.rawState}
            power={devices.find(d => d.id === 'hvac')?.power}
            expectedPower={devices.find(d => d.id === 'hvac')?.expectedPower}
            isTargetOfAction={isHvacAction}
            lastAction={latestDecision?.Candidate_Action === 'Turn Academic HVAC OFF' ? 'Turned HVAC OFF' : null}
          />

          <PhysicalDeviceSwitchCard
            id="lighting"
            name="Academic Lighting"
            icon={Lightbulb}
            rawState={devices.find(d => d.id === 'lighting')?.rawState}
            power={devices.find(d => d.id === 'lighting')?.power}
            expectedPower={devices.find(d => d.id === 'lighting')?.expectedPower}
            isTargetOfAction={isLightingAction}
            lastAction={latestDecision?.Candidate_Action === 'Turn Academic Lighting OFF' ? 'Turned Lighting OFF' : null}
          />

          <PhysicalDeviceSwitchCard
            id="ev_charging"
            name="EV Charging"
            icon={Car}
            rawState={devices.find(d => d.id === 'ev_charging')?.rawState}
            power={devices.find(d => d.id === 'ev_charging')?.power}
            expectedPower={devices.find(d => d.id === 'ev_charging')?.expectedPower}
            isTargetOfAction={isEvAction}
            lastAction={latestDecision?.Candidate_Action === 'Shift EV Charging' ? 'Shifted EV Charge' : null}
          />

          <PhysicalDeviceSwitchCard
            id="water_pump"
            name="Water Pump"
            icon={Waves}
            rawState={devices.find(d => d.id === 'water_pump')?.rawState}
            power={devices.find(d => d.id === 'water_pump')?.power}
            expectedPower={devices.find(d => d.id === 'water_pump')?.expectedPower}
            isTargetOfAction={false}
            lastAction={null}
          />
        </div>
      </div>

      {/* Real-time Replay Decision Chart */}
      <div className="bg-white border border-ink-100 rounded-xl p-5 shadow-panel">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-display font-semibold text-ink-900 text-base">Telemetry Replay Stream Chart</h3>
            <p className="text-xs text-ink-500">Live demand curve before and after automated agent intervention.</p>
          </div>
          <div className="text-xs text-ink-500">
            Replay Timestamp: <strong className="text-ink-800">{shortTime(timestamp)}</strong>
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 11, fill: '#64748B' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} width={45} />
              <Tooltip formatter={(value, name) => [`${formatNumber(value)} MW`, name]} />
              <Legend />
              <Line name="Regional Reference (AEP)" type="monotone" dataKey="referenceDemandMW" stroke="#64748B" strokeWidth={2} dot={false} />
              <Line name="XGBoost Forecast" type="monotone" dataKey="forecastMW" stroke="#3B82F6" strokeWidth={2} strokeDasharray="4 4" dot={false} />
              <Line name="Load Before Action" type="monotone" dataKey="loadBeforeMW" stroke="#F59E0B" strokeWidth={2} dot={false} />
              <Line name="Load After Action" type="monotone" dataKey="loadAfterMW" stroke="#10B981" strokeWidth={3} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
