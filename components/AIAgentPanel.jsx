import { useState } from 'react';
import { BrainCircuit, Wind, Car, Droplets, Check, CheckCircle2, AlertCircle, Sparkles, Activity } from 'lucide-react';
import Modal from './Modal.jsx';

const OPTION_ICONS = [Wind, Car, Droplets];

export default function AIAgentPanel({ decision, status = 'Live Monitoring' }) {
  const [reasoningOpen, setReasoningOpen] = useState(false);

  // Parse decision data safely
  const situation = decision?.situation || 'Continuously monitoring grid telemetry and virtual campus loads.';
  const options = decision?.options || [];
  const selectedAction = decision?.selected || 'Do Nothing';
  const expectedImpact = decision?.expectedImpact || 0;
  const duration = decision?.duration || 'Current hour';
  const explanation = decision?.explanation || 'All operational constraints are satisfied. Campus demand aligns with baseline predictions.';

  const isNominal = selectedAction === 'Do Nothing' || !selectedAction;

  return (
    <div className="bg-white border border-ink-100 rounded-xl shadow-panel p-4 sm:p-5 relative overflow-hidden transition-all duration-300">
      {/* Dynamic Header Badge */}
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-agent-light flex items-center justify-center text-agent-dark">
            <BrainCircuit size={20} className="animate-pulse" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-ink-900 text-base">KAIRA Autonomous AI Agent</h3>
            <div className="text-xs text-ink-500">Continuous real-time recommendation engine</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wide">{status}</span>
          </div>
        </div>
      </div>

      {/* Live Situation Stream */}
      <div className="mb-4 p-3.5 rounded-lg bg-slate-50 border border-slate-200/80">
        <div className="flex items-center gap-2 text-xs font-bold text-ink-500 uppercase tracking-wider mb-1">
          <Activity size={14} className="text-blue-500" /> Real-Time Situation Analysis
        </div>
        <p className="text-sm font-medium text-ink-900 leading-relaxed">{situation}</p>
      </div>

      {/* Evaluated Action Candidates / Stream */}
      {!isNominal && options.length > 0 ? (
        <div className="mb-4">
          <div className="text-xs font-bold text-ink-500 uppercase tracking-wider mb-2">Evaluated Action Candidates</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {options.map((option, i) => {
              const Icon = OPTION_ICONS[i % OPTION_ICONS.length];
              const isSelected = option.label === selectedAction;
              return (
                <div
                  key={option.label}
                  className={`rounded-lg border p-3 transition-all ${
                    isSelected 
                      ? 'border-emerald-500 bg-emerald-50/60 shadow-sm ring-1 ring-emerald-400' 
                      : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <Icon size={16} className={isSelected ? 'text-emerald-700' : 'text-slate-400'} />
                    {isSelected && <Check size={16} className="text-emerald-600 font-bold" />}
                  </div>
                  <div className="text-sm font-semibold text-ink-900 leading-tight">{option.label}</div>
                  <div className="text-xs font-bold text-emerald-700 mt-1 tabular">{option.impact}</div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="mb-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5">
          <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs text-emerald-800">
            <strong>Optimal Operational State:</strong> No demand shedding or load shifts required. Campus electrical loads and environmental setpoints match baseline expectations.
          </div>
        </div>
      )}

      {/* Selected Action Banner */}
      <div className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
        !isNominal 
          ? 'bg-gradient-to-r from-emerald-900 to-teal-900 text-white border-emerald-500 shadow-md' 
          : 'bg-slate-900 text-white border-slate-800'
      }`}>
        <div className="flex-1">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-300 uppercase tracking-wider mb-1">
            <Sparkles size={14} /> Agent Decision Recommendation
          </div>
          <div className="font-display font-bold text-lg text-white">{selectedAction}</div>
          <div className="text-xs text-slate-300 mt-1">
            Window: <strong className="text-slate-100">{duration}</strong> · Estimated load reduction:{' '}
            <span className="text-emerald-300 font-bold tabular">{Math.abs(expectedImpact)} MW</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setReasoningOpen(true)}
          className="shrink-0 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold transition-all shadow-md active:scale-95"
        >
          View Agent Reasoning
        </button>
      </div>

      {/* Reasoning Modal */}
      <Modal open={reasoningOpen} onClose={() => setReasoningOpen(false)} title="KAIRA Agent Decision Reasoning">
        <div className="space-y-4 text-sm">
          <div className="p-3 bg-slate-100 rounded-lg border border-slate-200">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Recommendation</div>
            <div className="text-base font-bold text-slate-900 mt-0.5">{selectedAction}</div>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Explanation</div>
            <p className="text-slate-700 leading-relaxed bg-white p-3 rounded-lg border border-slate-200">{explanation}</p>
          </div>
          <div className="pt-2 text-xs text-slate-500 border-t border-slate-200">
            Grounded in the current backend energy context and deterministic optimization constraints.
          </div>
        </div>
      </Modal>
    </div>
  );
}
