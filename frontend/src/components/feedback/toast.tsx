import { createContext, useCallback, useContext, useMemo, useState, type ReactElement, type ReactNode } from 'react';

type ToastVariant = 'success' | 'error' | 'info';

export interface ToastInput {
  title: string;
  detail?: string;
  variant?: ToastVariant;
  durationMs?: number;
}

interface ToastRecord extends ToastInput {
  id: string;
  variant: ToastVariant;
}

type NotifyFn = (input: ToastInput) => void;

const ToastContext = createContext<NotifyFn>(() => {});

function toastStyles(variant: ToastVariant): string {
  if (variant === 'success') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-100';
  }
  if (variant === 'error') {
    return 'border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-700 dark:bg-rose-900/30 dark:text-rose-100';
  }
  return 'border-cyan-200 bg-cyan-50 text-cyan-900 dark:border-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-100';
}

export function ToastProvider({ children }: { children: ReactNode }): ReactElement {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);

  const notify = useCallback((input: ToastInput) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const durationMs = Math.max(2000, Math.min(input.durationMs || 4200, 12000));
    const nextToast: ToastRecord = {
      ...input,
      id,
      variant: input.variant || 'info',
    };

    setToasts((previous) => [...previous, nextToast]);

    window.setTimeout(() => {
      setToasts((previous) => previous.filter((item) => item.id !== id));
    }, durationMs);
  }, []);

  const value = useMemo(() => notify, [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 mx-auto flex w-full max-w-xl flex-col gap-2 px-4">
        {toasts.map((toast) => (
          <article
            key={toast.id}
            role="status"
            className={`pointer-events-auto rounded-xl border px-4 py-3 shadow-lg ${toastStyles(toast.variant)}`}
          >
            <p className="text-sm font-semibold">{toast.title}</p>
            {toast.detail ? <p className="mt-1 text-xs opacity-90">{toast.detail}</p> : null}
          </article>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): NotifyFn {
  return useContext(ToastContext);
}
