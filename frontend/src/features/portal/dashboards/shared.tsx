import { motion } from "framer-motion";
import { type LucideIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import {
  Card,
  CountUp,
  LazyChart,
  SectionHeading,
  Skeleton,
  staggerContainer,
} from "../../../design-system";
import type { DashboardData, UpNextItem } from "../../dashboard/api";

export const BRAND = "#00A0E0";

/** White-on-gradient progress ring for the hero highlight (percent values). */
export function HeroRing({ percent }: { percent: number }) {
  const size = 116;
  const stroke = 9;
  const pct = Math.max(0, Math.min(100, percent));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [sweep, setSweep] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setSweep(pct));
    return () => cancelAnimationFrame(id);
  }, [pct]);
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          stroke="rgba(255,255,255,0.22)"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke="white"
          strokeDasharray={c}
          strokeDashoffset={c - (sweep / 100) * c}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <span className="absolute text-2xl font-semibold">{Math.round(pct)}%</span>
    </div>
  );
}

export function Hero({
  eyebrow,
  title,
  subtitle,
  ctaLabel,
  ctaTo,
  highlight,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  ctaLabel?: string;
  ctaTo?: string;
  highlight?: { label: string; value: string; percent?: number; sub?: string; icon?: LucideIcon };
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="ap-hero relative overflow-hidden rounded-3xl p-7 text-white shadow-lift"
    >
      <div aria-hidden className="pointer-events-none absolute inset-0">
        {/* A warm glow sits behind the highlight so bold white text has depth to sit on. */}
        <div className="absolute -right-16 -top-20 h-80 w-80 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-28 -left-10 h-64 w-64 rounded-full bg-violet/25 blur-3xl" />
        {/* Subtle dot-grid texture for tactility */}
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage: "radial-gradient(rgba(255,255,255,0.9) 1px, transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        />
      </div>
      <div className="relative flex flex-wrap items-stretch justify-between gap-6">
        <div className="max-w-xl">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
            {eyebrow}
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-white/70">{subtitle}</p>
          {ctaLabel && ctaTo && (
            <Link
              to={ctaTo}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-navy transition hover:bg-white/90"
            >
              {ctaLabel} <span aria-hidden>→</span>
            </Link>
          )}
        </div>
        {highlight && (
          <div className="flex items-center gap-6">
            <span aria-hidden className="hidden h-16 w-px bg-white/20 sm:block" />
            {highlight.percent != null ? (
              <div className="flex flex-col items-center">
                <HeroRing percent={highlight.percent} />
                <div className="mt-1.5 text-[11px] font-medium uppercase tracking-wider text-white/75">
                  {highlight.label}
                </div>
                {highlight.sub && (
                  <div className="mt-0.5 text-xs text-white/60">{highlight.sub}</div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-start">
                {highlight.icon && (
                  <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-white">
                    <highlight.icon size={17} aria-hidden />
                  </span>
                )}
                <div className="text-[11px] font-semibold uppercase tracking-wider text-white/60">
                  {highlight.label}
                </div>
                <div className="mt-0.5 text-[2.75rem] font-bold leading-none tracking-tight text-white">
                  {Number.isFinite(Number(highlight.value)) ? (
                    <CountUp value={Number(highlight.value)} />
                  ) : (
                    highlight.value
                  )}
                </div>
                {highlight.sub && (
                  <div className="mt-1.5 text-xs text-white/60">{highlight.sub}</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function KpiGrid({ children }: { children: ReactNode }) {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 gap-4 lg:grid-cols-4"
    >
      {children}
    </motion.div>
  );
}

export function TrendCard({
  data,
  title,
  subtitle,
  explain,
}: {
  data: DashboardData["trend"];
  title: string;
  subtitle: string;
  explain: string;
}) {
  if (!data || data.length === 0) return null;
  return (
    <Card>
      <SectionHeading title={title} subtitle={subtitle} />
      <LazyChart
        kind="area"
        data={data}
        xKey="label"
        series={[{ key: "value", label: "Login days", color: BRAND }]}
        height={240}
      />
      <p className="mt-2 rounded-lg bg-sky/50 px-3 py-2 text-xs leading-relaxed text-navy">
        {explain}
      </p>
    </Card>
  );
}

export function UpNext({ items }: { items?: UpNextItem[] }) {
  return (
    <Card>
      <SectionHeading title="Up next" subtitle="Scheduled live classes" />
      {items && items.length > 0 ? (
        <div className="flex flex-col divide-y divide-brdr">
          {items.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-3">
              <div>
                <div className="text-sm font-medium text-ink">{c.title}</div>
                <div className="text-xs text-muted">{c.batch_code}</div>
              </div>
              <div className="text-xs text-muted">
                {new Date(c.scheduled_at).toLocaleString([], {
                  day: "2-digit",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="py-6 text-center text-sm text-muted">No upcoming classes.</p>
      )}
    </Card>
  );
}

export function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="grid gap-6">
      <Skeleton className="h-40 rounded-3xl" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-2xl" />
        ))}
      </div>
      <Skeleton className="h-72 rounded-2xl" />
    </div>
  );
}
