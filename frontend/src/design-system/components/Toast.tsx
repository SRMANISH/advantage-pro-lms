import { AnimatePresence, motion } from "framer-motion";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "../utils/cn";

type ToastTone = "success" | "error" | "info";
interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  show: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

// Module-level bridge so non-React code (e.g. the axios interceptor) can raise toasts.
let globalShow: ToastContextValue["show"] | null = null;

/** Show a toast from anywhere (no hook needed). No-op before the provider mounts. */
export function toast(message: string, tone: ToastTone = "info") {
  globalShow?.(message, tone);
}

const DISMISS_MS = 3500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const show = (message: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
  };
  globalShow = show;

  // Auto-dismiss owned by an effect rather than fired and forgotten inside show(). The old
  // version left a live setTimeout holding a setState closure after unmount — on a route
  // change or a hot reload that fires into a dead tree, which React warns about and which
  // leaks the timer. Keying off `toasts` also means each toast gets exactly one timer even
  // if show() is called twice in the same tick.
  useEffect(() => {
    const pending = timers.current;
    for (const t of toasts) {
      if (pending.has(t.id)) continue;
      pending.set(
        t.id,
        setTimeout(() => {
          pending.delete(t.id);
          setToasts((prev) => prev.filter((x) => x.id !== t.id));
        }, DISMISS_MS),
      );
    }
  }, [toasts]);

  // Unmount: drop every outstanding timer, and release the module-level bridge so a stale
  // provider cannot keep receiving toasts after a remount.
  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach(clearTimeout);
      pending.clear();
      globalShow = null;
    };
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ type: "spring", stiffness: 320, damping: 26 }}
              className={cn(
                "pointer-events-auto rounded-xl border bg-surface px-4 py-3 text-sm shadow-lift",
                t.tone === "success"
                  ? "border-success/30 text-success"
                  : t.tone === "error"
                    ? "border-danger/30 text-danger"
                    : "border-brdr text-ink",
              )}
            >
              {t.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}
