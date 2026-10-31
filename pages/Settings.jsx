import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext.jsx';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex flex-col gap-5 max-w-2xl">
      <div>
        <h2 className="font-display font-semibold text-ink-900 text-lg">Settings</h2>
        <p className="text-sm text-ink-500 mt-1">Local dashboard preferences. Deterministic decisions and simulated controls remain backend-owned.</p>
      </div>

      <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5">
        <h3 className="font-display font-semibold text-ink-900 mb-3">Appearance</h3>
        <div className="flex items-center justify-between py-2">
          <div className="text-sm text-ink-900">Theme</div>
          <div className="flex bg-ink-50 rounded-md p-1">
            <button
              onClick={() => theme !== 'light' && toggleTheme()}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                theme === 'light' ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500'
              }`}
            >
              <Sun size={14} /> Light
            </button>
            <button
              onClick={() => theme !== 'dark' && toggleTheme()}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                theme === 'dark' ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500'
              }`}
            >
              <Moon size={14} /> Dark
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white border border-ink-100 rounded-lg shadow-panel p-4 sm:p-5">
        <h3 className="font-display font-semibold text-ink-900 mb-1">Control boundary</h3>
        <p className="text-sm text-ink-700 leading-relaxed">
          AI Control and simulated operating controls are managed from the Virtual Environment page and are persisted by the Python
          runtime. When disabled, the deterministic agent can recommend an action but cannot
          execute it in the simulated environment.
        </p>
        <p className="text-xs text-ink-500 leading-relaxed mt-3">
          All operational controls are SIMULATED. No physical device command is sent.
        </p>
      </div>
    </div>
  );
}
