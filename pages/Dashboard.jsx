import { Download, Power, ShieldCheck } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useSimulation } from '../context/SimulationContext.jsx';
import { formatNumber, shortTime } from '../utils/backendMappers.js';
import { energyApi } from '../services/energyApi.js';
import AIAgentPanel from '../components/AIAgentPanel.jsx';

export default function Dashboard() {
  const { current, replay, analytics, decisions, agentControlEnabled, loading, error, selectReplayDate, nextStep, setAgentControl } = useSimulation();
  const state = current?.state;
  const decision = current?.decision;
  const dates = replay?.options?.dates ?? [];
  const selectedDate = replay?.options?.selected_date ?? '';
  const year = selectedDate.slice(0, 4);
  const month = selectedDate.slice(5, 7);
  const months = [...new Set(dates.filter((date) => date.startsWith(year)).map((date) => date.slice(5, 7)))];
  const filteredDates = dates.filter((date) => date.startsWith(`${year}-${month}`));

  const selectedTimeline = (analytics?.timeline ?? [])
    .filter((item) => !selectedDate || String(item.time ?? '').startsWith(selectedDate))
    .map((item) => ({ ...item, forecastMW: String(item.time) === String(state?.Datetime) ? state?.Forecast?.forecast_MW : null }));
  
  const timeline = selectedTimeline.length
    ? selectedTimeline
    : [{ time: state?.Datetime, referenceDemandMW: state?.Reference_Demand_MW, forecastMW: state?.Forecast?.forecast_MW }];
  
  const latest = decisions[0];

  const report = async () => {
    const reportWindow = window.open('about:blank', '_blank', 'noopener,noreferrer');
    try {
      const blob = await energyApi.downloadReplayReport();
      const url = URL.createObjectURL(blob);
      if (reportWindow) reportWindow.location.href = url;
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `kaira-situation-${selectedDate || 'report'}.pdf`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (reportError) {
      if (reportWindow) reportWindow.close();
      throw reportError;
    }
  };

  const selectYear = (nextYear) => { const next = dates.find((date) => date.startsWith(nextYear)); if (next) selectReplayDate(next); };
  const selectMonth = (nextMonth) => { const next = dates.find((date) => date.startsWith(`${year}-${nextMonth}`)); if (next) selectReplayDate(next); };
  const advanceHour = () => nextStep();

  if (loading && !state) return <div className="rounded-lg border border-ink-100 bg-white p-5 text-sm text-ink-700">Loading replay dataset…<p className="mt-2 text-xs text-ink-500">The backend owns the simulation state. If this takes longer than a few seconds, refresh once the API is running.</p></div>;
  if (error) return <div className="rounded-lg bg-alert-light p-4 text-sm text-alert-dark">Backend unavailable: {error}</div>;

  // Format decision data for AIAgentPanel
  const panelDecision = {
    situation: decision?.opportunity?.reason || `Evaluating AEP grid demand for ${shortTime(state?.Datetime)}. Regional load is ${formatNumber(state?.Reference_Demand_MW)} MW.`,
    options: decision?.action_validations?.map(v => ({
      label: v.action,
      impact: `${formatNumber(v.estimated_saving_MW || 0, 1)} MW`
    })) || [
      { label: decision?.action?.action || 'Do Nothing', impact: `${formatNumber(decision?.action?.estimated_saving_MW || 0, 1)} MW` }
    ],
    selected: decision?.action?.action || 'Do Nothing',
    expectedImpact: decision?.action?.estimated_saving_MW || 0,
    duration: 'Selected Hour',
    explanation: decision?.action?.explanation || 'Regional grid demand is nominal. Baseline load predictions align with historical AEP values.'
  };

  return (
    <div className="dashboard-shell">
      <section className="dashboard-hero">
        <div className="hero-grid" />
        <div className="relative z-10 max-w-3xl">
          <div className="eyebrow"><span className="eyebrow-dot" /> KAIRA Regional Grid Operations</div>
          <h2 className="hero-title">Expected demand, historical context, and the next safe decision.</h2>
          <p className="hero-copy">This dashboard focuses specifically on the AEP regional energy demand dataset. It provides grid-level demand forecasting and regional optimization insights.</p>
          <div className="hero-meta">
            <span><ShieldCheck size={13} /> AEP: REAL_HISTORICAL DATA</span>
            <span>Forecast: DERIVED XGBOOST</span>
          </div>
        </div>
      </section>

      {/* CONTINUOUS KAIRA AI AGENT STREAM PANEL */}
      <section>
        <AIAgentPanel decision={panelDecision} status="AEP Grid Stream" />
      </section>

      <section className="truth-strip">
        <ShieldCheck size={17} />
        <div>
          <strong>Historical AEP Dataset Overview</strong>
          <span>Select any year (2004–2018) or date below to move through historical grid source records.</span>
        </div>
        <span className="provenance-pill derived">HISTORICAL AEP FOCUS</span>
      </section>

      <section className="replay-selector">
        <div>
          <span className="section-kicker">Replay selection</span>
          <p>Hourly regional/AEP source date</p>
        </div>
        <label>Year<select value={year} onChange={(event) => selectYear(event.target.value)}>{(replay?.options?.years ?? []).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>Month<select value={month} onChange={(event) => selectMonth(event.target.value)}>{months.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>Date<select value={selectedDate} onChange={(event) => selectReplayDate(event.target.value)}>{filteredDates.map((item) => <option key={item}>{item}</option>)}</select></label>
        <button type="button" className="report-button" onClick={advanceHour} disabled={loading}>{loading ? 'Loading…' : 'Next hour'}</button>
        <button type="button" className="report-button" onClick={report}><Download size={15} /> Report</button>
      </section>

      <section className="dashboard-readout">
        <Readout label="Expected regional demand prediction" value={`${formatNumber(state?.Forecast?.forecast_MW)} MW`} provenance="DERIVED XGBOOST" />
        <Readout label="Historical regional demand" value={`${formatNumber(state?.Reference_Demand_MW)} MW`} provenance="REAL_HISTORICAL AEP" />
        <Readout label="Replay row" value={shortTime(replay?.source_timestamp)} provenance="HISTORICAL INPUT" />
      </section>

      <section className="chart-panel">
        <div className="panel-heading">
          <div><span className="section-kicker">Historical graph</span><h3>Regional demand and prediction</h3></div>
          <span className="provenance-pill derived">AEP + XGBOOST</span>
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#26352f" vertical={false} />
              <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 10, fill: '#8da39a' }} />
              <YAxis tick={{ fontSize: 10, fill: '#8da39a' }} />
              <Tooltip formatter={(value, name) => [`${formatNumber(value)} MW`, name === 'referenceDemandMW' ? 'Historical AEP' : 'Prediction']} />
              <Line dataKey="referenceDemandMW" stroke="#d7a84f" dot={false} strokeWidth={2} />
              <Line dataKey="forecastMW" stroke="#63c995" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="agent-control-banner">
        <div>
          <span className="section-kicker">Autonomous Agent Execution</span>
          <strong>{latest?.Execution_Status === 'SUCCESS' ? 'Latest decision executed in simulation' : latest ? 'Recommendation visible' : 'Monitoring regional grid'}</strong>
          <p>{decision?.opportunity?.reason ?? 'Advance the replay to inspect deterministic AI recommendations.'}</p>
        </div>
        <button type="button" role="switch" aria-checked={agentControlEnabled} onClick={() => setAgentControl(!agentControlEnabled)} className={`agent-switch ${agentControlEnabled ? 'on' : 'off'}`}>
          <Power size={17} /> {agentControlEnabled ? 'AGENT ENABLED' : 'RECOMMENDATION ONLY'}
        </button>
      </section>
    </div>
  );
}

function Readout({ label, value, provenance }) { 
  return (
    <div className="readout">
      <span>{label}</span>
      <strong>{value}</strong>
      <em>{provenance}</em>
    </div>
  ); 
}
