import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { staggerItem } from "../motion";
import { cn } from "../utils/cn";
import { CountUp } from "./CountUp";

type Tone = "azure" | "navy" | "violet" | "green" | "amber" | "rose";

const TONES: Record<Tone, string> = {
  azure: "bg-brand/10 text-brand-strong",
  navy: "bg-navy/10 text-navy",
  violet: "bg-violet/10 text-violet",
  green: "bg-success/10 text-success",
  amber: "bg-warning/12 text-warning",
  rose: "bg-danger/10 text-danger",
};

interface StatCardProps {
  label: string;
  value: number | string;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  delta?: string;
  deltaTone?: "up" | "down" | "neutral";
  hint?: string;
  footer?: ReactNode;
  icon?: LucideIcon;
  tone?: Tone;
  className?: string;
}

export function StatCard({
  label,
  value,
  decimals = 0,
  suffix = "",
  prefix = "",
  delta,
  deltaTone = "up",
  hint,
  footer,
  icon: Icon,
  tone = "azure",
  className,
}: StatCardProps) {
  const isNum = typeof value === "number";
  return (
    <motion.div
      variants={staggerItem}
      whileHover={{ y: -3 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={cn("rounded-2xl border border-brdr bg-surface p-5 shadow-card", className)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <span
              className={cn("flex h-9 w-9 items-center justify-center rounded-xl", TONES[tone])}
            >
              <Icon size={17} aria-hidden />
            </span>
          )}
          <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
        </div>
        {hint && <span className="text-[11px] text-muted">{hint}</span>}
      </div>
      <div className="mt-3 flex items-end gap-2">
        <span className="text-3xl font-semibold tracking-tight text-ink">
          {isNum ? (
            <CountUp value={value} decimals={decimals} suffix={suffix} prefix={prefix} />
          ) : (
            <>
              {prefix}
              {value}
              {suffix}
            </>
          )}
        </span>
        {delta && (
          <span
            className={cn(
              "mb-1 text-xs font-medium",
              deltaTone === "up"
                ? "text-success"
                : deltaTone === "down"
                  ? "text-danger"
                  : "text-muted",
            )}
          >
            {delta}
          </span>
        )}
      </div>
      {footer && <div className="mt-3">{footer}</div>}
    </motion.div>
  );
}
