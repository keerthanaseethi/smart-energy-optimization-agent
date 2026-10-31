// Small colored pill used everywhere a device, decision, or alert
// status needs to be shown. Centralizing the color mapping here is
// what keeps color usage meaningful (section 3 of the brief) instead
// of each page inventing its own status colors.
const STYLES = {
  active: 'bg-energy-light text-energy-dark',
  charging: 'bg-agent-light text-agent-dark',
  generating: 'bg-energy-light text-energy-dark',
  reporting: 'bg-iot-light text-iot-dark',
  idle: 'bg-ink-100 text-ink-500',
  offline: 'bg-ink-100 text-ink-500',
  simulated: 'bg-agent-light text-agent-dark',
  completed: 'bg-energy-light text-energy-dark',
  resolved: 'bg-energy-light text-energy-dark',
  high: 'bg-alert-light text-alert-dark',
  warning: 'bg-warn-light text-warn-dark',
  low: 'bg-warn-light text-warn-dark',
  optimized: 'bg-energy-light text-energy-dark',
};

export default function StatusBadge({ status }) {
  const key = status?.toLowerCase() ?? '';
  const style = STYLES[key] ?? 'bg-ink-100 text-ink-500';

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}
