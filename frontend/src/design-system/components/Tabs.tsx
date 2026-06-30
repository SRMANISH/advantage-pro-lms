import { motion } from "framer-motion";

import { cn } from "../utils/cn";

interface Tab {
  value: string;
  label: string;
}

export function Tabs({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: Tab[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center gap-1 rounded-xl border border-brdr bg-surface p-1",
        className,
      )}
    >
      {tabs.map((t) => {
        const active = t.value === value;
        return (
          <button
            key={t.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(t.value)}
            className={cn(
              "relative rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active ? "text-white" : "text-muted hover:text-navy",
            )}
          >
            {active && (
              <motion.span
                layoutId="ap-tab-pill"
                className="absolute inset-0 rounded-lg bg-brand-strong"
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
              />
            )}
            <span className="relative z-10">{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}
