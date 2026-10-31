import {
  Car, Fan, Droplets, Lightbulb, Sun, BatteryMedium, Gauge, Box,
} from 'lucide-react';
import StatusBadge from './StatusBadge.jsx';

// Maps backend device icon names to Lucide components.
const ICON_MAP = { Car, Fan, Droplets, Lightbulb, Sun, BatteryMedium, Gauge };

export default function DeviceCard({ device, onClick }) {
  const Icon = ICON_MAP[device.icon] ?? Box;

  return (
    <button
      onClick={() => onClick(device)}
      className="text-left bg-white border border-ink-100 rounded-lg shadow-panel p-4 hover:border-agent/40 hover:shadow-md transition-all w-full"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="w-9 h-9 rounded-md bg-iot-light flex items-center justify-center">
          <Icon size={18} className="text-iot-dark" />
        </div>
        <StatusBadge status={device.status} />
      </div>
      <div className="font-medium text-ink-900">{device.name}</div>
      <div className="text-xs text-ink-500 mb-2">{device.type}</div>
      <div className="font-display text-xl font-semibold text-ink-900 tabular">
        {device.power} <span className="text-sm font-medium text-ink-500">{device.unit ?? 'MW'}</span>
      </div>
      <div className="text-[10px] font-bold text-ink-400 mt-2">{device.provenance}</div>
    </button>
  );
}
