import { useEffect } from 'react';
import { X } from 'lucide-react';

// Generic modal shell reused by the "View Reasoning" panel and the
// decision-detail / device-detail modals. Keeping one implementation
// means focus handling and the escape-to-close behavior only need to
// be written (and fixed) once.
export default function Modal({ open, onClose, title, children }) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-ink-900/40" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative bg-white w-full sm:max-w-lg sm:rounded-lg rounded-t-lg shadow-panel max-h-[85vh] overflow-y-auto thin-scroll"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-ink-100 sticky top-0 bg-white">
          <h3 className="font-display font-semibold text-ink-900">{title}</h3>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-900" aria-label="Close">
            <X size={20} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
