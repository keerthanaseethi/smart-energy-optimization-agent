import { AlertTriangle, AlertCircle, CheckCircle2, Check } from 'lucide-react';

// Severity drives both the icon and the accent color - red for high
// demand/abnormal conditions, amber for warnings, green once resolved
// or for a positive optimization event. No severity uses a color
// outside this mapping.
const SEVERITY = {
  high: { icon: AlertCircle, ring: 'border-alert/30 bg-alert-light', text: 'text-alert-dark' },
  warning: { icon: AlertTriangle, ring: 'border-warn/30 bg-warn-light', text: 'text-warn-dark' },
  optimized: { icon: CheckCircle2, ring: 'border-energy/30 bg-energy-light', text: 'text-energy-dark' },
};

export default function AlertCard({ alert, onResolve, onSelect }) {
  const severity = SEVERITY[alert.severity] ?? SEVERITY.warning;
  const Icon = severity.icon;

  return (
    <div className={`border rounded-lg p-4 flex items-start gap-3 ${severity.ring} ${alert.resolved ? 'opacity-60' : ''}`}>
      <Icon size={18} className={`${severity.text} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onSelect(alert)}>
        <div className="flex items-center justify-between gap-2">
          <span className={`font-medium text-sm ${severity.text}`}>{alert.title}</span>
          <span className="text-xs text-ink-500 tabular shrink-0">{alert.time}</span>
        </div>
        <p className="text-sm text-ink-700 mt-1">{alert.description}</p>
      </div>
      {!alert.resolved && (
        <button
          onClick={() => onResolve(alert.id)}
          className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-white border border-ink-200 text-xs font-medium text-ink-700 hover:border-ink-300"
        >
          <Check size={13} /> Resolve
        </button>
      )}
    </div>
  );
}
