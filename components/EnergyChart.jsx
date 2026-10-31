import { useState } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatNumber, shortTime } from '../utils/backendMappers.js';

const RANGES = ['6H', '12H', '24H'];

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-ink-100 rounded-md shadow-panel px-3 py-2 text-sm">
      <div className="font-medium text-ink-900 mb-1">{shortTime(label)}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2 text-ink-500">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span>{entry.name}</span>
          <span className="ml-auto font-medium text-ink-900 tabular">{formatNumber(entry.value, 1)} MW</span>
        </div>
      ))}
    </div>
  );
}

export default function EnergyChart({ data }) {
  const [range, setRange] = useState('12H');
  const visible = data?.slice(range === '6H' ? -6 : range === '12H' ? -12 : -24) ?? [];

  return (
    <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div>
          <h3 className="font-display font-semibold text-ink-900">Regional demand context</h3>
          <p className="text-sm text-ink-500 mt-0.5">REAL_HISTORICAL AEP reference and DERIVED XGBoost forecast, not campus telemetry</p>
        </div>
        <div className="flex bg-ink-50 rounded-md p-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                range === r ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-900'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={visible} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="campusFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2E6FE0" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#2E6FE0" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 12, fill: '#64748B' }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} width={48} unit=" MW" />
            <Tooltip content={<ChartTooltip />} />
            <Area type="monotone" dataKey="loadAfterMW" name="Simulated campus" stroke="#2E6FE0" strokeWidth={2} fill="url(#campusFill)" />
            <Line type="monotone" dataKey="forecastMW" name="Derived forecast" stroke="#7C4FE0" strokeWidth={2} strokeDasharray="4 3" dot={false} />
            <Line type="monotone" dataKey="referenceDemandMW" name="AEP reference" stroke="#1C9B6E" strokeWidth={1.5} dot={false} strokeDasharray="2 4" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-5 mt-3 text-xs text-ink-500 flex-wrap">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-1 rounded-full bg-iot inline-block" /> SIMULATED campus</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-1 rounded-full bg-agent inline-block" /> DERIVED forecast</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-1 rounded-full bg-energy inline-block" /> REAL_HISTORICAL AEP</span>
      </div>
    </div>
  );
}
