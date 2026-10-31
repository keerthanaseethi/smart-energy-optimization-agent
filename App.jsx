import { useEffect, useRef, useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { Bot } from 'lucide-react';
import { useSimulation } from './context/SimulationContext.jsx';
import Sidebar from './components/Sidebar.jsx';
import Header from './components/Header.jsx';
import Dashboard from './pages/Dashboard.jsx';
import LiveMonitoring from './pages/LiveMonitoring.jsx';
import AIAgent from './pages/AIAgent.jsx';
import DigitalTwin from './pages/DigitalTwin.jsx';
import Analytics from './pages/Analytics.jsx';
import Decisions from './pages/Decisions.jsx';
import Settings from './pages/Settings.jsx';
import VirtualEnvironment from './pages/VirtualEnvironment.jsx';

// Maps each route to the page title shown in the header, so the two
// stay in sync without every page needing to set its own title.
const TITLES = {
  '/': 'Dashboard',
  '/live-monitoring': 'Live Monitoring',
  '/ai-agent': 'AI Agent',
  '/digital-twin': 'Digital Twin',
  '/analytics': 'Energy Analytics',
  '/decisions': 'Decisions & Actions',
  '/settings': 'Settings',
  '/virtual-environment': 'Virtual Environment',
};

export default function App() {
  // Sidebar collapse (desktop) and mobile slide-over are separate
  // pieces of state because they solve different layout problems:
  // collapse narrows a persistent rail, mobile toggles visibility.
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const title = TITLES[location.pathname] ?? 'KAIRA';

  return (
    <div className="flex h-screen bg-ink-50 dark:bg-ink-900 transition-colors">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} onOpenMobileMenu={() => setMobileOpen(true)} />

        <main className="flex-1 overflow-y-auto thin-scroll p-4 sm:p-6 dark:bg-ink-900 dark:text-ink-100 transition-colors">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live-monitoring" element={<LiveMonitoring />} />
            <Route path="/ai-agent" element={<AIAgent />} />
            <Route path="/digital-twin" element={<DigitalTwin />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/decisions" element={<Decisions />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/virtual-environment" element={<VirtualEnvironment />} />
          </Routes>
        </main>
        <AgentGhost />
      </div>
    </div>
  );
}

function AgentGhost() {
  const { current, agentControlEnabled } = useSimulation();
  const ghostRef = useRef(null);
  const dragRef = useRef(null);
  const [position, setPosition] = useState(null);
  const decision = current?.decision;
  const action = decision?.action?.action ?? 'Monitor the selected replay';
  const reason = decision?.opportunity?.reason ?? 'I am watching the selected energy context for the next decision.';
  const fullMessage = agentControlEnabled
    ? `I selected ${action}. ${reason}`
    : `I recommend ${action}, but agent control is OFF, so I will not execute it.`;
  const [message, setMessage] = useState('');
  const previousMessage = useRef('');
  useEffect(() => {
    if (fullMessage === previousMessage.current) return;
    previousMessage.current = fullMessage;
    setMessage('');
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setMessage(fullMessage.slice(0, index));
      if (index >= fullMessage.length) window.clearInterval(timer);
    }, 18);
    return () => window.clearInterval(timer);
  }, [fullMessage]);
  const startDrag = (event) => {
    if (event.button !== 0 || event.target.closest('a,button')) return;
    const rect = ghostRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragRef.current = { offsetX: event.clientX - rect.left, offsetY: event.clientY - rect.top };
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const drag = (event) => {
    if (!dragRef.current) return;
    const width = ghostRef.current?.offsetWidth ?? 352;
    const height = ghostRef.current?.offsetHeight ?? 140;
    setPosition({
      left: Math.max(8, Math.min(window.innerWidth - width - 8, event.clientX - dragRef.current.offsetX)),
      top: Math.max(8, Math.min(window.innerHeight - height - 8, event.clientY - dragRef.current.offsetY)),
    });
  };
  const stopDrag = () => { dragRef.current = null; };
  return (
    <aside
      ref={ghostRef}
      className="agent-ghost"
      style={position ? { left: `${position.left}px`, top: `${position.top}px`, right: 'auto', bottom: 'auto' } : undefined}
      onPointerDown={startDrag}
      onPointerMove={drag}
      onPointerUp={stopDrag}
      onPointerCancel={stopDrag}
      aria-label="Draggable KAIRA agent"
    >
      <div className="agent-ghost-avatar"><Bot size={22} /></div>
      <div className="min-w-0">
        <div className="agent-ghost-title"><strong>KAIRA agent</strong><span>{agentControlEnabled ? 'ACTIVE' : 'RECOMMENDATION'}</span></div>
        <p>{message}</p>
        <span className="agent-ghost-status">Continuous decision feed · SIMULATED</span>
      </div>
    </aside>
  );
}
