import { useEffect, useState } from 'react';
import { Menu, Bell, CircleUserRound } from 'lucide-react';
import { useSimulation } from '../context/SimulationContext.jsx';

// Formats the live clock shown in the header. Extracted so the
// formatting logic isn't duplicated if another page ever needs it.
function formatDateTime(date) {
  const dateStr = date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
  const timeStr = date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  return `${dateStr} · ${timeStr}`;
}

export default function Header({ title, onOpenMobileMenu }) {
  const { alerts = [] } = useSimulation();
  const notificationCount = alerts.filter((alert) => !alert.resolved).length;
  // A ticking clock reinforces that this is a live-monitoring system,
  // not a static mockup - it costs nothing and matches the brief's
  // "current date/time" requirement in the header.
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between h-16 px-4 sm:px-6 bg-white border-b border-ink-100">
      <div className="flex items-center gap-3 min-w-0">
        <button
          className="lg:hidden text-ink-500 hover:text-ink-900 shrink-0"
          onClick={onOpenMobileMenu}
          aria-label="Open menu"
        >
          <Menu size={22} />
        </button>
        <h1 className="font-display font-semibold text-ink-900 text-lg truncate">{title}</h1>
      </div>

      <div className="flex items-center gap-3 sm:gap-5 shrink-0">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md bg-energy-light">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-energy-dark opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-energy-dark" />
          </span>
          <span className="text-sm font-medium text-energy-dark">Replay ready</span>
        </div>

        <span className="hidden sm:inline text-sm text-ink-500 tabular">{formatDateTime(now)}</span>

        <button
          className="relative text-ink-500 hover:text-ink-900"
          aria-label={`${notificationCount} notifications`}
        >
          <Bell size={20} />
          {notificationCount > 0 && (
            <span className="absolute -top-1 -right-1 flex items-center justify-center w-4 h-4 rounded-full bg-alert text-white text-[10px] font-semibold">
              {notificationCount}
            </span>
          )}
        </button>

        <button className="text-ink-500 hover:text-ink-900" aria-label="User profile">
          <CircleUserRound size={24} />
        </button>
      </div>
    </header>
  );
}
