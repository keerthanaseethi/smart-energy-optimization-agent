import { ArrowUp, ArrowDown } from 'lucide-react';

// A single KPI metric card. Kept as one reusable component (per the
// brief's component structure) so the dashboard and analytics pages
// can render the same visual design from different data.
//
// `tone` picks the accent color and must map to one of the semantic
// meanings in the design system - it is never chosen for decoration.
const TONES = {
  iot: { bg: 'bg-iot-light', text: 'text-iot-dark' },
  agent: { bg: 'bg-agent-light', text: 'text-agent-dark' },
  energy: { bg: 'bg-energy-light', text: 'text-energy-dark' },
  alert: { bg: 'bg-alert-light', text: 'text-alert-dark' },
  neutral: { bg: 'bg-ink-100', text: 'text-ink-700' },
};

export default function KPICard({ icon: Icon, label, value, unit, trend, tone = 'neutral' }) {
  const toneStyle = TONES[tone] ?? TONES.neutral;
  const isPositiveTrend = trend?.direction === 'up';

  return (
    <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className={`w-9 h-9 rounded-md flex items-center justify-center ${toneStyle.bg}`}>
          <Icon size={18} className={toneStyle.text} strokeWidth={2} />
        </div>
        {trend && (
          <div
            className={`flex items-center gap-0.5 text-xs font-medium ${
              trend.good ? 'text-energy-dark' : 'text-alert-dark'
            }`}
          >
            {isPositiveTrend ? <ArrowUp size={13} /> : <ArrowDown size={13} />}
            {trend.value}
          </div>
        )}
      </div>

      <div>
        <div className="font-display text-2xl font-semibold text-ink-900 tabular">
          {value}
          {unit && <span className="text-base font-medium text-ink-500 ml-1">{unit}</span>}
        </div>
        <div className="text-sm text-ink-500 mt-0.5">{label}</div>
      </div>
    </div>
  );
}
