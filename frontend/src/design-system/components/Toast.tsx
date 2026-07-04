import { AnimatePresence, motion } from "framer-motion";
import { createContext, useContext, useState, type ReactNode } from "react";

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

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const show = (message: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  };
  globalShow = show;

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
