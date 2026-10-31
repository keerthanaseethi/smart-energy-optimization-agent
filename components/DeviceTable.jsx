import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import StatusBadge from './StatusBadge.jsx';

// Toggle switch used for the "AI Control" column. Local, uncontrolled
// styling only - actual enable/disable logic is passed in via onToggle
// so the table stays a presentation component.
function ToggleSwitch({ checked, onChange, label }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onChange}
      className={`relative w-9 h-5 rounded-full transition-colors ${checked ? 'bg-agent' : 'bg-ink-200'}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

export default function DeviceTable({ devices, onSelect, onToggleControl, onSetDeviceState, onSetDeviceParameters }) {
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('All');

  const types = useMemo(() => ['All', ...new Set(devices.map((d) => d.type))], [devices]);

  const filtered = useMemo(() => {
    return devices.filter((d) => {
      const matchesQuery = d.name.toLowerCase().includes(query.toLowerCase());
      const matchesType = typeFilter === 'All' || d.type === typeFilter;
      return matchesQuery && matchesType;
    });
  }, [devices, query, typeFilter]);

  return (
    <div className="bg-white border border-ink-100 rounded-lg shadow-panel">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 border-b border-ink-100">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" />
          <input
            type="text"
            placeholder="Search devices..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-md border border-ink-200 focus:border-agent outline-none"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-md border border-ink-200 focus:border-agent outline-none bg-white"
        >
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Horizontally scrollable on small screens rather than collapsing
          into cards, since column alignment matters for comparing devices. */}
      <div className="overflow-x-auto thin-scroll">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="text-left text-xs text-ink-500 border-b border-ink-100">
              <th className="px-4 py-3 font-medium">Device</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Current Power</th>
              <th className="px-4 py-3 font-medium">Operating Parameter</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Simulated Device Control</th>
              <th className="px-4 py-3 font-medium">AI Control</th>
              <th className="px-4 py-3 font-medium">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => (
              <tr
                key={d.id}
                className="border-b border-ink-100 last:border-0 hover:bg-ink-50 cursor-pointer"
                onClick={() => onSelect(d)}
              >
                <td className="px-4 py-3 font-medium text-ink-900">{d.name}</td>
                <td className="px-4 py-3 text-ink-500">{d.type}</td>
                <td className="px-4 py-3 tabular text-ink-900">{d.power} {d.unit ?? 'MW'}</td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  {d.id === 'hvac' && (
                    <label className="flex items-center gap-2 text-xs text-ink-600">
                      <span>Setpoint</span>
                      <input
                        type="number"
                        min="16"
                        max="30"
                        step="0.5"
                        defaultValue={d.parameters?.setpoint_c}
                        onBlur={(e) => onSetDeviceParameters(d.id, { setpoint_c: Number(e.target.value) })}
                        className="w-16 px-1 py-1 rounded border border-ink-200"
                        aria-label={`HVAC setpoint for ${d.name}`}
                      />
                      °C
                    </label>
                  )}
                  {d.id === 'lighting' && (
                    <label className="flex items-center gap-2 text-xs text-ink-600">
                      <span>Brightness</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        defaultValue={d.parameters?.brightness_pct}
                        onChange={(e) => onSetDeviceParameters(d.id, { brightness_pct: Number(e.target.value) })}
                        aria-label={`Lighting brightness for ${d.name}`}
                      />
                      <span className="tabular w-8">{Math.round(d.parameters?.brightness_pct ?? 0)}%</span>
                    </label>
                  )}
                  {d.id !== 'hvac' && d.id !== 'lighting' && <span className="text-xs text-ink-400">State only</span>}
                </td>
                <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  {d.id === 'ev_charging' || d.id === 'hvac' || d.id === 'lighting' || d.id === 'water_pump' ? (
                    <select
                      value={d.rawState}
                      aria-label={`Simulated state for ${d.name}`}
                      onChange={(e) => onSetDeviceState(d.id, e.target.value)}
                      className="px-2 py-1 text-xs rounded border border-ink-200 bg-white"
                    >
                      {(d.id === 'hvac'
                        ? ['ON', 'ECO', 'OFF']
                        : d.id === 'ev_charging'
                          ? ['ON', 'OFF', 'SHIFTED']
                          : ['ON', 'OFF']).map((state) => (
                        <option key={state} value={state}>{state}</option>
                      ))}
                    </select>
                  ) : 'Unavailable'}
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <ToggleSwitch
                    checked={d.aiControl}
                    onChange={() => onToggleControl(d.id)}
                    label={`Toggle AI control for ${d.name}`}
                  />
                </td>
                <td className="px-4 py-3 text-ink-500 tabular">{d.lastUpdated}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-ink-500">
                  No devices match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
