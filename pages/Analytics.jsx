import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useSimulation } from '../context/SimulationContext.jsx';
import { formatNumber, shortTime } from '../utils/backendMappers.js';

export default function Analytics() {
  const { analytics, loading, error } = useSimulation();
  if (loading && !analytics) return <div className="text-sm text-ink-500">Loading forecast evaluation…</div>;
  if (error) return <div className="rounded-lg bg-alert-light p-4 text-sm text-alert-dark">Backend unavailable: {error}</div>;
  const timeline = analytics?.timeline ?? [];
  const forecastRows = timeline.filter((row) => row.referenceDemandMW != null && row.forecastMW != null);
  const mae = forecastRows.length ? forecastRows.reduce((sum, row) => sum + Math.abs(Number(row.forecastMW) - Number(row.referenceDemandMW)), 0) / forecastRows.length : null;
  return <div className="mx-auto flex max-w-6xl flex-col gap-5">
    <section className="dashboard-hero"><div className="hero-grid" /><div className="relative z-10 max-w-3xl"><div className="eyebrow">Energy analytics</div><h2 className="hero-title">Forecast performance on the selected replay.</h2><p className="hero-copy">Only hourly backend replay rows are shown here. No campus/device KPI or invented real-time telemetry is included.</p><div className="hero-meta"><span>Model output: DERIVED XGBOOST</span><span>Reference: REAL_HISTORICAL AEP</span></div></div></section>
    <section className="dashboard-readout"><Readout label="Rows with forecast + reference" value={forecastRows.length} provenance="BACKEND REPLAY DATA" /><Readout label="Mean absolute error" value={mae == null ? 'N/A' : `${formatNumber(mae)} MW`} provenance="DERIVED FROM SELECTED ROWS" /><Readout label="Recorded simulated impact" value={`${formatNumber(analytics?.totalEnergyImpactMWh)} MWh`} provenance="DERIVED AUDIT" /></section>
    <section className="chart-panel"><div className="panel-heading"><div><span className="section-kicker text-emerald-300">Forecast evaluation</span><h3>Historical regional demand vs XGBoost prediction</h3></div><span className="provenance-pill derived">NO LIVE DATA</span></div><div className="h-80 px-3 pb-4"><ResponsiveContainer width="100%" height="100%"><LineChart data={timeline}><CartesianGrid strokeDasharray="3 3" stroke="#26352f" vertical={false} /><XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 10, fill: '#8da39a' }} /><YAxis tick={{ fontSize: 10, fill: '#8da39a' }} /><Tooltip formatter={(value, name) => [`${formatNumber(value)} MW`, name === 'referenceDemandMW' ? 'Historical AEP' : 'XGBoost prediction']} /><Line dataKey="referenceDemandMW" stroke="#d7a84f" dot={false} strokeWidth={2} /><Line dataKey="forecastMW" stroke="#63c995" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer></div></section>
  </div>;
}
function Readout({ label, value, provenance }) { return <div className="readout"><span>{label}</span><strong>{value}</strong><em>{provenance}</em></div>; }
