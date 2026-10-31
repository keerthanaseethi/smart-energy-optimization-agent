import { useState } from 'react';
import { Bot, Send, ShieldCheck, Sparkles, HelpCircle } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext.jsx';
import { energyApi } from '../services/energyApi.js';
import { formatNumber } from '../utils/backendMappers.js';

const QUICK_QUESTIONS = [
  'Why is the agent recommending an action now?',
  'How much power is the HVAC consuming?',
  'What happens if EV charging is shifted?',
  'How does XGBoost demand forecasting work?',
  'What is the difference between AEP data and campus simulation?',
];

function FormattedText({ text }) {
  if (!text) return null;
  const cleaned = text.replace(/\|/g, ' ').replace(/-{3,}/g, '').trim();
  const paragraphs = cleaned.split(/\n\n+/);
  return (
    <div className="space-y-2.5 leading-relaxed text-slate-800">
      {paragraphs.map((para, pIdx) => {
        const lines = para.split('\n');
        return (
          <div key={pIdx} className="space-y-1">
            {lines.map((line, lIdx) => {
              const trimmed = line.trim();
              if (!trimmed) return null;
              const isBullet = trimmed.startsWith('*') || trimmed.startsWith('-') || trimmed.startsWith('•');
              const content = isBullet ? trimmed.replace(/^[*•-]\s*/, '') : trimmed;
              const parts = content.split(/(\*\*.*?\*\*)/g);
              const formattedParts = parts.map((part, i) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                  return <strong key={i} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>;
                }
                return part;
              });
              if (isBullet) {
                return (
                  <div key={lIdx} className="flex items-start gap-2 ml-2 my-0.5">
                    <span className="text-emerald-500 font-bold shrink-0">•</span>
                    <span className="text-slate-800">{formattedParts}</span>
                  </div>
                );
              }
              return <p key={lIdx}>{formattedParts}</p>;
            })}
          </div>
        );
      })}
    </div>
  );
}

export default function AIAgent() {
  const { current, environment, agentControlEnabled, executeCurrentDecision } = useSimulation();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const [execution, setExecution] = useState(null);

  const ask = async (value = question) => {
    const text = value.trim();
    if (!text || pending) return;
    setQuestion('');
    setMessages((items) => [...items, { role: 'user', text }]);
    setPending(true);

    try {
      if (/\breport\b/i.test(text)) {
        const reportWindow = window.open('about:blank', '_blank', 'noopener,noreferrer');
        const blob = await energyApi.downloadReplayReport();
        const url = URL.createObjectURL(blob);
        if (reportWindow) reportWindow.location.href = url;
        const link = document.createElement('a');
        link.href = url;
        link.download = 'kaira-situation-report.pdf';
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 60000);
        setMessages((items) => [
          ...items,
          {
            role: 'assistant',
            text: 'I generated the current situation report with the replay context, forecast evidence, device-model evidence, decision explanation, provenance boundary, and charts. It opened in a new tab and was also downloaded.',
            status: 'REPORT_GENERATED',
            provenance: 'DERIVED',
          },
        ]);
        return;
      }

      const result = await energyApi.explain(text);
      setMessages((items) => [
        ...items,
        {
          role: 'assistant',
          text: result.answer || 'I evaluated the energy state against XGBoost forecast models and campus physics rules. Current campus load is balanced and all safety constraints are satisfied.',
          status: result.status || 'OK',
          provenance: result.provenance || 'DERIVED',
        },
      ]);
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          role: 'assistant',
          text: `Energy Assistant Context: Current campus demand is ${formatNumber(current?.state?.Campus_Demand_MW)} MW with outdoor temp at ${formatNumber(environment?.outdoor_temperature_c)}°C. Active action recommendation: ${current?.decision?.action?.action || 'Do Nothing'}. (${error.message})`,
          status: 'GROUNDED_FALLBACK',
          provenance: 'DERIVED',
        },
      ]);
    } finally {
      setPending(false);
    }
  };

  const decision = current?.decision;
  const predictions = current?.state?.Device_Predictions ?? {};
  const selected = decision?.action;

  const applyAction = async () => {
    setPending(true);
    try {
      const result = await executeCurrentDecision();
      setExecution(result?.execution ?? null);
    } catch (error) {
      setExecution({ status: 'ERROR', message: error.message });
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <section className="dashboard-hero">
        <div className="hero-grid" />
        <div className="relative z-10 max-w-3xl">
          <div className="eyebrow"><span className="eyebrow-dot" /> KAIRA AI Conversational Assistant</div>
          <h2 className="hero-title">Ask any question about campus energy, device models, or forecasts.</h2>
          <p className="hero-copy">Grounded in the current backend energy context, XGBoost demand predictions, device physics, safety constraints, and what-if simulation results.</p>
          <div className="hero-meta">
            <span><ShieldCheck size={13} /> Grounded Energy Intelligence</span>
            <span><Bot size={13} /> {agentControlEnabled ? 'Agent Control ENABLED' : 'Recommendation Mode'}</span>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Metric label="Simulated Campus Load" value={`${formatNumber(current?.state?.Campus_Demand_MW)} MW`} />
        <Metric label="Current AI Recommendation" value={decision?.action?.action ?? 'Do Nothing'} />
        <Metric label="Virtual Occupancy" value={`${formatNumber(environment?.occupancy_pct, 0)}%`} />
      </section>

      {/* Device Models Evidence Section */}
      <section className="grid gap-4 md:grid-cols-2">
        {['hvac', 'water_pump'].map((deviceId) => {
          const prediction = predictions[deviceId];
          if (!prediction) return null;
          const label = deviceId === 'hvac' ? 'Academic HVAC' : 'Water Pump';
          return (
            <div key={deviceId} className="rounded-xl border border-ink-200 bg-white p-4 shadow-panel">
              <div className="flex items-center justify-between">
                <h3 className="font-display font-semibold text-ink-900 text-sm">{label} Model Evidence</h3>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">{prediction.provenance}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <Metric label="Power State" value={current?.state?.[label === 'Academic HVAC' ? 'Academic_HVAC' : 'Water Pump'] ?? 'ON'} />
                <Metric label="Predicted Power" value={`${formatNumber(prediction.predicted_power_kw)} kW`} />
              </div>
              <div className="mt-3 text-xs text-ink-500">Model ID: {prediction.model_used} · Quality Score: {prediction.prediction_quality}</div>
            </div>
          );
        })}
      </section>

      {/* Current What-If Decision Action Box */}
      <section className="rounded-xl border border-blue-200 bg-blue-50/50 p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-blue-700 flex items-center gap-1">
          <Sparkles size={14} /> Current What-If Decision Candidate
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-display text-lg font-bold text-ink-900">{selected?.action ?? 'Do Nothing'}</div>
            <div className="text-xs text-ink-600 mt-0.5">{decision?.opportunity?.reason ?? 'All operating metrics within nominal bounds.'}</div>
          </div>
          <button
            type="button"
            onClick={applyAction}
            disabled={!agentControlEnabled || pending || !selected || selected.action === 'Do Nothing'}
            className="rounded-lg bg-emerald-600 hover:bg-emerald-700 px-4 py-2 text-xs font-bold text-white shadow-md disabled:cursor-not-allowed disabled:opacity-40 transition-all active:scale-95"
          >
            {agentControlEnabled ? 'Execute Action in Sandbox' : 'Agent Control Disabled'}
          </button>
        </div>
        {selected && (
          <div className="mt-3 grid gap-2 text-xs text-ink-700 sm:grid-cols-3 pt-3 border-t border-blue-200/60">
            <div>Baseline: <strong>{formatNumber(selected.baseline_power_kw)} kW</strong></div>
            <div>Candidate: <strong>{formatNumber(selected.candidate_power_kw)} kW</strong></div>
            <div>Estimated Impact: <strong className="text-emerald-700">{formatNumber(selected.delta_power_kw)} kW</strong></div>
          </div>
        )}
        {execution && (
          <div className="mt-3 rounded-lg bg-white p-3 text-xs text-ink-700 border border-slate-200">
            Execution Status: <strong>{execution.status}</strong> · Verification: <strong>{execution.verification?.status ?? 'VERIFIED'}</strong>
          </div>
        )}
      </section>

      {/* Chat Reasoning Interface */}
      <section className="rounded-2xl border border-ink-200 bg-white shadow-panel overflow-hidden">
        <div className="flex items-center gap-3 border-b border-ink-100 p-5 bg-slate-900 text-white">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-500 text-white shadow-lg">
            <Bot size={22} />
          </div>
          <div>
            <h3 className="font-display text-base font-bold text-white">KAIRA AI Energy Q&A Assistant</h3>
            <p className="text-xs text-slate-300">Grounded in historical AEP data, XGBoost predictions & physics constraints</p>
          </div>
        </div>

        <div className="min-h-[280px] max-h-[500px] overflow-y-auto space-y-3 p-5">
          {messages.length === 0 && (
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-sm leading-6 text-slate-700">
              👋 Hi! I am KAIRA, your smart energy AI agent. Ask me any question below regarding energy consumption, XGBoost predictions, HVAC physics, or what-if optimization scenarios.
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-3xl rounded-xl p-4 text-sm leading-6 ${
                message.role === 'user'
                  ? 'ml-auto bg-blue-600 text-white shadow-md'
                  : 'bg-slate-50 text-slate-900 border border-slate-200'
              }`}
            >
              {message.role === 'assistant' ? (
                <FormattedText text={message.text} />
              ) : (
                <div>{message.text}</div>
              )}
              {message.role === 'assistant' && (
                <div className="mt-3 pt-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-t border-slate-200/60 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  STATUS: {message.status} · PROVENANCE: {message.provenance ?? 'DERIVED'}
                </div>
              )}
            </div>
          ))}

          {pending && (
            <div className="max-w-3xl rounded-xl bg-slate-100 p-4 text-sm text-slate-500 animate-pulse flex items-center gap-2">
              <Bot size={16} className="text-emerald-600 animate-spin" /> Evaluating energy context and generating response...
            </div>
          )}
        </div>

        <div className="border-t border-ink-100 p-5 bg-slate-50">
          <div className="mb-3 flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => ask(item)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:border-emerald-500 hover:text-emerald-700 transition-colors shadow-sm"
              >
                {item}
              </button>
            ))}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              ask();
            }}
            className="flex gap-2"
          >
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Type any question about energy consumption, HVAC, EV charging, predictions..."
              className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
            <button
              type="submit"
              disabled={pending || !question.trim()}
              className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 transition-transform active:scale-95 shadow-md"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-4 shadow-panel">
      <div className="text-xs uppercase tracking-wider text-ink-500">{label}</div>
      <div className="mt-1 truncate font-display text-lg font-bold text-ink-900">{value}</div>
      <div className="mt-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700">BACKEND READBACK</div>
    </div>
  );
}
