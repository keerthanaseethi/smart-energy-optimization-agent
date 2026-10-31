import { createContext, useContext, useEffect, useState } from 'react';

// Global theme context. Kept intentionally tiny - just a boolean and
// a setter - since the brief only asks for dark/light mode "if it can
// be implemented cleanly". Toggling the `dark` class on <html> lets
// Tailwind's `dark:` variants take over without any per-component logic.
const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
