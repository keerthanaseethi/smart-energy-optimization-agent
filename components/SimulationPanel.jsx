import { PlayCircle, Loader2, ArrowRight, FlaskConical } from 'lucide-react';

// Digital Twin simulation panel (brief section 10). Running the
// simulation is intentionally a distinct, explicit user action rather
// than something that happens automatically, since the brief requires
// clearly labeling this as a simulation and not a live device command.
export default function SimulationPanel({ before, action, reduction, result, onRun }) {
  const status = result?.status ?? 'idle';

  const handleRun = async () => {
    await onRun({ before, action, reduction });
  };

  return (
    <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FlaskConical size={18} className="text-agent-dark" />
          <h3 className="font-display font-semibold text-ink-900">Digital Twin Simulation</h3>
        </div>
        <span className="text-xs font-medium px-2.5 py-1 rounded-md bg-warn-light text-warn-dark">
          SIMULATED / WHAT-IF ONLY
        </span>
      </div>

      <p className="text-sm text-ink-500 mb-4">
        This evaluates the deterministic agent's selected action against the virtual building model. It does not execute the action or send any command to a real device.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className="rounded-md bg-ink-50 p-3">
          <div className="text-xs text-ink-500 mb-1">Current simulated load</div>
          <div className="font-display text-xl font-semibold text-ink-900 tabular">{before} MW</div>
        </div>
        <div className="rounded-md bg-agent-light p-3">
          <div className="text-xs text-agent-dark mb-1">AI Action</div>
          <div className="text-sm font-medium text-ink-900 leading-tight">{action}</div>
        </div>
        <div className="rounded-md bg-energy-light p-3">
          <div className="text-xs text-energy-dark mb-1">What-if load</div>
          <div className="font-display text-xl font-semibold text-ink-900 tabular">
            {status === 'done' ? `${result.after} MW` : '—'}
          </div>
        </div>
      </div>

      {status === 'idle' && (
        <button
          onClick={handleRun}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-agent text-white text-sm font-medium hover:bg-agent-dark transition-colors"
        >
          <PlayCircle size={17} /> Run What-if Evaluation
        </button>
      )}

      {status === 'running' && (
        <div className="flex items-center gap-2 text-sm text-ink-500 py-2">
          <Loader2 size={16} className="animate-spin text-agent" />
          Running backend what-if evaluation...
        </div>
      )}

      {status === 'done' && (
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-sm tabular">
            <span className="text-ink-900 font-medium">{result.before} MW</span>
            <ArrowRight size={14} className="text-ink-500" />
            <span className="text-energy-dark font-semibold">{result.after} MW</span>
          </div>
          <span className="text-sm font-medium text-energy-dark tabular">
            −{result.reduction} MW estimated current-period impact
          </span>
          <button
            onClick={() => onRun({ before, action: 'Do Nothing', reduction: 0 })}
            className="ml-auto text-sm font-medium text-ink-500 hover:text-ink-900"
          >
            Run again
          </button>
        </div>
      )}
    </div>
  );
}
