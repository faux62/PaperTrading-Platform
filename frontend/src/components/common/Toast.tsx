/**
 * Toast Component
 */
import { clsx } from 'clsx';
import { X, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import type { Toast as ToastType } from '../../types';

const ToastIcon = ({ type }: { type: ToastType['type'] }) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-success-400" />,
    error: <XCircle className="w-5 h-5 text-danger-400" />,
    warning: <AlertTriangle className="w-5 h-5 text-warning-400" />,
    info: <Info className="w-5 h-5 text-primary-400" />,
  };
  return icons[type];
};

interface ToastItemProps {
  toast: ToastType;
  onRemove: (id: string) => void;
}

const ToastItem = ({ toast, onRemove }: ToastItemProps) => {
  const backgrounds = {
    success: 'bg-success-500/10 border-success-500/30',
    error: 'bg-danger-500/10 border-danger-500/30',
    warning: 'bg-warning-500/10 border-warning-500/30',
    info: 'bg-primary-500/10 border-primary-500/30',
  };

  return (
    <div
      className={clsx(
        'flex items-start gap-3 p-4 rounded-lg border backdrop-blur-sm',
        'animate-slide-up shadow-lg',
        backgrounds[toast.type]
      )}
    >
      <ToastIcon type={toast.type} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{toast.title}</p>
        {toast.message && (
          <p className="text-sm text-surface-400 mt-0.5">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="p-1 rounded text-surface-400 hover:text-white hover:bg-surface-700 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

const ToastContainer = () => {
  const { toasts, removeToast } = useUIStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
};

// Hook for easy toast usage
export const useToast = () => {
  const addToast = useUIStore((state) => state.addToast);

  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message }),
  };
};

export default ToastContainer;
