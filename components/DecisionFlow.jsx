import { Radio, Cpu, TrendingUp, ListTree, CheckCircle2, Boxes, ShieldCheck } from 'lucide-react';

// Static description of every stage in the agentic workflow. `activeIndex`
// (passed in by the caller) determines which stage is currently
// highlighted, so this same component can represent either a live
// state or a fixed illustrative diagram.
const STAGES = [
  { label: 'Context', desc: 'Replay row + device state', icon: Radio },
  { label: 'Forecast', desc: 'Existing XGBoost model', icon: TrendingUp },
  { label: 'Opportunity', desc: 'Mismatch is detected', icon: Cpu },
  { label: 'Safety gate', desc: 'Rules validate action', icon: ShieldCheck },
  { label: 'What-if', desc: 'Impact is estimated', icon: ListTree },
  { label: 'Simulate', desc: 'Virtual adapter executes', icon: Boxes },
  { label: 'Verify', desc: 'Readback is confirmed', icon: CheckCircle2 },
];

export default function DecisionFlow({ activeIndex = 4 }) {
  return (
    <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5">
      <h3 className="font-display font-semibold text-ink-900 mb-4">Decision Flow</h3>

      {/* Horizontal scroll on small screens, full row on larger ones */}
      <div className="flex overflow-x-auto thin-scroll gap-0 -mx-1 px-1 pb-1">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          const isActive = i === activeIndex;
          const isDone = i < activeIndex;
          return (
            <div key={stage.label} className="flex items-center shrink-0">
              <div className="flex flex-col items-center w-32 text-center">
                <div
                  className={`w-11 h-11 rounded-full flex items-center justify-center border-2 mb-2 transition-colors ${
                    isActive
                      ? 'border-agent bg-agent-light'
                      : isDone
                      ? 'border-energy bg-energy-light'
                      : 'border-ink-200 bg-ink-50'
                  }`}
                >
                  <Icon
                    size={18}
                    className={isActive ? 'text-agent-dark' : isDone ? 'text-energy-dark' : 'text-ink-500'}
                  />
                </div>
                <div className={`text-xs font-medium ${isActive ? 'text-agent-dark' : 'text-ink-900'}`}>
                  {stage.label}
                </div>
                <div className="text-[11px] text-ink-500 mt-0.5 leading-tight">{stage.desc}</div>
              </div>
              {i < STAGES.length - 1 && (
                <div className={`h-0.5 w-6 sm:w-10 shrink-0 ${isDone ? 'bg-energy' : 'bg-ink-200'}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
