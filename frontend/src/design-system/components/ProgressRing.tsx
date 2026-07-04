import { useEffect, useState } from "react";

import { cn } from "../utils/cn";

interface ProgressRingProps {
  value: number; // 0–100
  size?: number;
  stroke?: number;
  label?: string;
  className?: string;
}

/** Animated SVG progress ring — sweeps from 0 to `value` on mount (CSS transition). */
export function ProgressRing({ value, size = 112, stroke = 10, label, className }: ProgressRingProps) {
  const pct = Math.max(0, Math.min(100, value));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [sweep, setSweep] = useState(0);

  useEffect(() => {
    const id = requestAnimationFrame(() => setSweep(pct));
    return () => cancelAnimationFrame(id);
  }, [pct]);

  const tone =
    pct >= 75 ? "rgb(var(--color-success))" : pct >= 50 ? "rgb(var(--color-brand))" : "rgb(var(--color-danger))";

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} role="img"
      aria-label={`${label ?? "Progress"}: ${pct}%`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke}
          stroke="rgb(var(--color-sky))" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke={tone}
          strokeDasharray={c}
          strokeDashoffset={c - (sweep / 100) * c}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tracking-tight text-ink">{Math.round(pct)}%</span>
        {label && <span className="text-[11px] text-muted">{label}</span>}
      </div>
    </div>
  );
}
