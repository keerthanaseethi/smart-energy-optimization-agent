import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Activity,
  BrainCircuit,
  Boxes,
  LineChart,
  ListChecks,
  Settings as SettingsIcon,
  SlidersHorizontal,
  ChevronsLeft,
  ChevronsRight,
  Zap,
  X,
} from 'lucide-react';

// Every nav item maps 1:1 to a page component. Keeping this as data
// (rather than JSX repeated per item) means adding a page later is a
// one-line change here instead of touching markup in multiple places.
const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/live-monitoring', label: 'Live Monitoring', icon: Activity },
  { to: '/ai-agent', label: 'AI Agent', icon: BrainCircuit },
  { to: '/digital-twin', label: 'Digital Twin', icon: Boxes },
  { to: '/analytics', label: 'Energy Analytics', icon: LineChart },
  { to: '/decisions', label: 'Decisions & Actions', icon: ListChecks },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
  { to: '/virtual-environment', label: 'Virtual Environment', icon: SlidersHorizontal },
];

export default function Sidebar({ collapsed, onToggle, mobileOpen, onCloseMobile }) {
  return (
    <>
      {/* Backdrop for the mobile slide-over menu */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-ink-900/40 z-30 lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          flex flex-col bg-white border-r border-ink-100
          transition-all duration-200 ease-out
          ${collapsed ? 'lg:w-[76px]' : 'lg:w-64'}
          w-64
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-ink-100 shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-8 h-8 rounded-md bg-agent flex items-center justify-center shrink-0">
              <Zap size={18} className="text-white" strokeWidth={2.25} />
            </div>
            {!collapsed && (
              <span className="font-display font-semibold text-ink-900 text-sm whitespace-nowrap">
                KAIRA
              </span>
            )}
          </div>
          <button
            className="lg:hidden text-ink-500 hover:text-ink-900"
            onClick={onCloseMobile}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto thin-scroll py-3 px-2">
          <ul className="space-y-0.5">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  onClick={onCloseMobile}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                      isActive
                        ? 'bg-agent-light text-agent-dark font-medium'
                        : 'text-ink-500 hover:bg-ink-50 hover:text-ink-900'
                    }`
                  }
                  title={collapsed ? label : undefined}
                >
                  <Icon size={18} className="shrink-0" strokeWidth={2} />
                  {!collapsed && <span className="truncate">{label}</span>}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="p-2 border-t border-ink-100 hidden lg:block">
          <button
            onClick={onToggle}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-ink-500 hover:bg-ink-50 hover:text-ink-900 transition-colors"
          >
            {collapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
