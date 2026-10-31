import { useState } from 'react';
import { ShieldCheck, AlertCircle, CheckCircle2, ArrowRight, Zap, Info, FileText } from 'lucide-react';
import Modal from '../components/Modal.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import { useSimulation } from '../context/SimulationContext.jsx';
import { mapDecisionRecord, formatNumber } from '../utils/backendMappers.js';

export default function Decisions() {
  const [selected, setSelected] = useState(null);
  const { decisions, loading, error } = useSimulation();
  const records = decisions.map(mapDecisionRecord);

  if (loading && !decisions.length) return <div className="text-sm text-ink-500">Loading backend decision history...</div>;
  if (error) return <div className="text-sm text-alert-dark bg-alert-light rounded-md p-4">Backend unavailable: {error}</div>;

  return (
    <div className="flex flex-col gap-6 max-w-[1400px]">
      <div>
        <h2 className="font-display font-semibold text-ink-900 text-xl">Decisions & Actions Audit Log</h2>
        <p className="text-sm text-ink-500 mt-1">Full 3-step decision breakdown: 1) Problem Detected, 2) Context & Trigger, 3) Action Executed & Verified Impact.</p>
      </div>

      {/* Decision Table */}
      <div className="bg-white border border-ink-100 rounded-xl shadow-panel overflow-x-auto thin-scroll">
        <table className="w-full text-sm min-w-[850px]">
          <thead>
            <tr className="text-left text-xs font-semibold text-ink-500 uppercase tracking-wider border-b border-ink-100 bg-slate-50">
              <th className="px-4 py-3.5 font-medium">Timestamp</th>
              <th className="px-4 py-3.5 font-medium">1. Problem / Trigger</th>
              <th className="px-4 py-3.5 font-medium">2. Operating Context</th>
              <th className="px-4 py-3.5 font-medium">3. Action Executed</th>
              <th className="px-4 py-3.5 font-medium">Peak Reduction</th>
              <th className="px-4 py-3.5 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {records.map((d) => {
              const opportunity = d.raw?.Opportunity || 'NORMAL_OPERATION';
              const problemText = opportunity !== 'NORMAL_OPERATION' ? opportunity.replace(/_/g, ' ') : 'Nominal Operation';
              const actionText = d.selected || 'Do Nothing';
              const impact = formatNumber(d.expectedImpact || 0);

              return (
                <tr
                  key={d.id}
                  className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  onClick={() => setSelected(d)}
                >
                  <td className="px-4 py-3.5 text-ink-500 tabular font-medium text-xs whitespace-nowrap">{d.time}</td>
                  <td className="px-4 py-3.5 max-w-xs truncate">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
                      opportunity !== 'NORMAL_OPERATION' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {problemText}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-ink-700 max-w-sm truncate text-xs">{d.situation}</td>
                  <td className="px-4 py-3.5 font-semibold text-ink-900">{actionText}</td>
                  <td className="px-4 py-3.5 text-emerald-600 font-bold tabular">{impact} MW</td>
                  <td className="px-4 py-3.5"><StatusBadge status={d.status} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Decision Detail Modal (3-Part Narrative Breakdown) */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="3-Step Decision Narrative & Verification">
        {selected && (
          <div className="flex flex-col gap-4 text-sm">
            {/* Step 1: The Problem */}
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-800 uppercase tracking-wider mb-1">
                <AlertCircle size={15} /> Step 1: Problem / Opportunity Detected
              </div>
              <div className="text-base font-bold text-amber-950">
                {selected.raw?.Opportunity ? selected.raw.Opportunity.replace(/_/g, ' ') : 'Nominal Operational State'}
              </div>
              <p className="text-xs text-amber-900/80 mt-1">{selected.raw?.Opportunity_Reason || 'Continuous grid telemetry and campus demand evaluated as nominal.'}</p>
            </div>

            {/* Step 2: What Happened / Context */}
            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
              <div className="flex items-center gap-2 text-xs font-bold text-blue-800 uppercase tracking-wider mb-1">
                <Info size={15} /> Step 2: Operating Context & What Happened
              </div>
              <p className="text-sm font-medium text-blue-950">{selected.situation}</p>
              <div className="grid grid-cols-2 gap-3 mt-3 text-xs text-blue-900/80">
                <div>Tariff Window: <strong>{selected.raw?.Tariff || 'Normal'}</strong></div>
                <div>Occupancy: <strong>{formatNumber(selected.raw?.Occupancy || 0, 0)}%</strong></div>
                <div>Outdoor Temp: <strong>{formatNumber(selected.raw?.Temperature_C || 20, 1)}°C</strong></div>
                <div>Regional Demand: <strong>{formatNumber(selected.raw?.Reference_Demand_MW || 0)} MW</strong></div>
              </div>
            </div>

            {/* Step 3: Action Taken & Impact */}
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 uppercase tracking-wider mb-1">
                <CheckCircle2 size={15} /> Step 3: Action Executed & Verified Impact
              </div>
              <div className="flex items-center justify-between mt-1">
                <div className="text-base font-bold text-emerald-950">{selected.selected}</div>
                <div className="text-base font-bold text-emerald-700 tabular">Saved {formatNumber(selected.expectedImpact)} MW</div>
              </div>

              <div className="mt-3 pt-3 border-t border-emerald-500/20 flex items-center justify-between text-xs text-emerald-900">
                <div>Load Before: <strong>{formatNumber(selected.simulationResult.before)} MW</strong></div>
                <ArrowRight size={14} className="text-emerald-600" />
                <div>Load After: <strong>{formatNumber(selected.simulationResult.after)} MW</strong></div>
              </div>
            </div>

            {/* Explanation & Verification */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">AI Recommendation Reasoning</div>
              <p className="text-xs text-slate-700 leading-relaxed">{selected.explanation}</p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-100 border border-slate-200">
                <div className="text-slate-500 font-semibold mb-0.5">Execution Status</div>
                <div className="font-bold text-slate-900">{selected.raw?.Execution_Status || selected.status}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-100 border border-slate-200">
                <div className="text-slate-500 font-semibold mb-0.5">Data Provenance</div>
                <div className="font-bold text-slate-900">{selected.raw?.Execution_Provenance || selected.raw?.Provenance || 'SIMULATED'}</div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
