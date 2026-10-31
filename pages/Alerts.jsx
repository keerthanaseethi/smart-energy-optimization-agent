import { useMemo, useState } from 'react';
import AlertCard from '../components/AlertCard.jsx';
import { useSimulation } from '../context/SimulationContext.jsx';
import Modal from '../components/Modal.jsx';

const FILTERS = ['All', 'High', 'Warning', 'Optimized'];

export default function Alerts() {
  const [filter, setFilter] = useState('All');
  const [selected, setSelected] = useState(null);
  const { alerts, resolveAlert, loading, error } = useSimulation();

  const filtered = useMemo(() => {
    if (filter === 'All') return alerts;
    return alerts.filter((a) => a.severity === filter.toLowerCase());
  }, [alerts, filter]);

  const handleResolve = (id) => resolveAlert(id);
  if (loading && !alerts.length) return <div className="text-sm text-ink-500">Loading backend alerts...</div>;
  if (error) return <div className="text-sm text-alert-dark bg-alert-light rounded-md p-4">Backend unavailable: {error}</div>;

  return (
    <div className="flex flex-col gap-5 max-w-[1400px]">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-display font-semibold text-ink-900 text-lg">Alerts</h2>
          <p className="text-sm text-ink-500 mt-1">Demand, device, and optimization events across the system.</p>
        </div>
        <div className="flex bg-ink-50 rounded-md p-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                filter === f ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-900'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {filtered.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onResolve={handleResolve} onSelect={setSelected} />
        ))}
        {filtered.length === 0 && (
          <div className="text-center text-sm text-ink-500 py-10 bg-white border border-ink-100 rounded-lg">
            No alerts in this category.
          </div>
        )}
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.title ?? ''}>
        {selected && (
          <div className="flex flex-col gap-3 text-sm">
            <p className="text-ink-700 leading-relaxed">{selected.description}</p>
            <div className="flex items-center justify-between pt-3 border-t border-ink-100">
              <span className="text-ink-500">Reported</span>
              <span className="text-ink-900 font-medium tabular">{selected.time}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-500">Status</span>
              <span className="text-ink-900 font-medium">{selected.resolved ? 'Resolved' : 'Active'}</span>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
