import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Card,
  EmptyState,
  LazyChart,
  SectionHeading,
  Skeleton,
  Sparkline,
  StatCard,
  staggerContainer,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { dashboardApi, type DashboardData, type UpNextItem } from "../dashboard/api";
import { PortalLayout } from "./PortalLayout";

const BRAND = "#00A0E0";

export function PortalPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const name = user?.full_name || user?.username || "";
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: dashboardApi.get });

  return (
    <PortalLayout role={role}>
      {isLoading || !data ? (
        <DashboardSkeleton />
      ) : (
        <Dashboard role={role} data={data} name={name} />
      )}
    </PortalLayout>
  );
}

/* ---------- shared building blocks ---------- */

function Hero({
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
  highlight?: { label: string; value: string };
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-navyDeep to-navy p-7 text-white shadow-lift"
    >
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-brand/25 blur-3xl" />
      </div>
      <div className="relative flex flex-wrap items-center justify-between gap-6">
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
          <div className="rounded-2xl border border-white/15 bg-white/5 px-6 py-5 text-right backdrop-blur">
            <div className="text-[11px] uppercase tracking-wider text-white/55">
              {highlight.label}
            </div>
            <div className="mt-1 text-4xl font-semibold">{highlight.value}</div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function KpiGrid({ children }: { children: ReactNode }) {
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

function TrendCard({ data, title }: { data: DashboardData["trend"]; title: string }) {
  if (!data || data.length === 0) return null;
  return (
    <Card>
      <SectionHeading title={title} subtitle="Distinct login-days per week" />
      <LazyChart
        kind="area"
        data={data}
        xKey="label"
        series={[{ key: "value", label: "Logins", color: BRAND }]}
        height={240}
      />
    </Card>
  );
}

function UpNext({ items }: { items?: UpNextItem[] }) {
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

/* ---------- role dashboards ---------- */

function Dashboard({ role, data, name }: { role: RoleDef; data: DashboardData; name: string }) {
  const slug = role.slug;
  const trendValues = (data.trend ?? []).map((t) => t.value);

  if (data.role === "student") {
    const k = data.kpis ?? {};
    const v = data.videos ?? { completed: 0, total: 0 };
    const videoPct = v.total ? Math.round((v.completed / v.total) * 100) : 0;
    return (
      <div className="grid gap-6">
        <Hero
          eyebrow="Student portal"
          title={`Welcome back, ${name.split(" ")[0] || name}`}
          subtitle="Keep your streak going — your batch content is below."
          ctaLabel="Continue learning"
          ctaTo={`/${slug}/videos`}
          highlight={{ label: "Videos completed", value: `${videoPct}%` }}
        />
        <KpiGrid>
          <StatCard
            label="Attendance"
            value={k.attendance_pct ?? 0}
            suffix="%"
            footer={<Sparkline data={trendValues} />}
          />
          <StatCard label="Pending tasks" value={k.pending_tasks ?? 0} />
          <StatCard label="Upcoming tests" value={k.upcoming_tests ?? 0} />
          <StatCard label="Login streak" value={k.streak_days ?? 0} suffix=" days" />
        </KpiGrid>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <TrendCard data={data.trend} title="Your activity" />
          </div>
          <UpNext items={data.up_next} />
        </div>
        <StudentBatches data={data} />
      </div>
    );
  }

  if (data.role === "faculty") {
    const t = data.totals ?? {};
    const a = data.attention ?? {};
    return (
      <div className="grid gap-6">
        <Hero
          eyebrow="Faculty portal"
          title={`Welcome, ${name.split(" ")[0] || name}`}
          subtitle="Your batches, doubts and live classes at a glance."
          ctaLabel="Open batches"
          ctaTo={`/${slug}/batches`}
          highlight={{ label: "Assigned batches", value: String(t.batches ?? 0) }}
        />
        <KpiGrid>
          <StatCard label="Batches" value={t.batches ?? 0} />
          <StatCard label="Students" value={t.students ?? 0} />
          <StatCard
            label="Unanswered doubts"
            value={a.unanswered_doubts ?? 0}
            deltaTone={a.unanswered_doubts ? "down" : "up"}
          />
          <StatCard label="To grade" value={a.submissions_to_grade ?? 0} />
        </KpiGrid>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <TrendCard data={data.trend} title="Batch activity" />
          </div>
          <UpNext items={data.up_next} />
        </div>
        <FacultyBatches data={data} slug={slug} />
      </div>
    );
  }

  if (data.role === "super_admin" || data.role === "admin" || data.role === "mis") {
    const t = data.totals ?? {};
    const a = data.attention ?? {};
    const cta =
      data.role === "admin"
        ? { label: "Create a batch", to: `/${slug}/batches` }
        : data.role === "mis"
          ? { label: "Certificate follow-up", to: `/${slug}/certificates` }
          : { label: "System channels", to: `/${slug}/channels` };
    return (
      <div className="grid gap-6">
        <Hero
          eyebrow="Institute operations"
          title="Operations at a glance"
          subtitle="Live view of batches, learners and follow-ups across the institute."
          ctaLabel={cta.label}
          ctaTo={cta.to}
          highlight={{ label: "Active batches", value: String(t.active_batches ?? 0) }}
        />
        <KpiGrid>
          <StatCard label="Total students" value={t.students ?? 0} />
          <StatCard label="Active batches" value={t.active_batches ?? 0} />
          <StatCard label="Courses" value={t.courses ?? 0} />
          <StatCard
            label="Certificates pending"
            value={a.certificate_pending ?? 0}
            deltaTone={a.certificate_pending ? "down" : "up"}
          />
        </KpiGrid>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <TrendCard data={data.trend} title="Platform activity" />
          </div>
          <Card>
            <SectionHeading title="Batch states" />
            {data.batch_states && data.batch_states.some((s) => s.value > 0) ? (
              <LazyChart kind="donut" data={data.batch_states} height={240} />
            ) : (
              <p className="py-6 text-center text-sm text-muted">No batches yet.</p>
            )}
          </Card>
        </div>
      </div>
    );
  }

  if (data.role === "counselor") {
    const k = data.kpis ?? {};
    return (
      <div className="grid gap-6">
        <Hero
          eyebrow="Counsellor portal"
          title="Attendance & follow-up"
          subtitle="Spot absentees early and keep learners on track with MIS."
          ctaLabel="Review attendance"
          ctaTo={`/${slug}/attendance`}
          highlight={{ label: "Absentees today", value: String(k.absentees_today ?? 0) }}
        />
        <KpiGrid>
          <StatCard label="Active students" value={k.active_students ?? 0} />
          <StatCard label="Logged in today" value={k.logged_in_today ?? 0} />
          <StatCard
            label="Absentees today"
            value={k.absentees_today ?? 0}
            deltaTone={k.absentees_today ? "down" : "up"}
          />
          <StatCard label="Batches" value={data.totals?.batches ?? 0} />
        </KpiGrid>
        <TrendCard data={data.trend} title="Platform activity" />
      </div>
    );
  }

  if (data.role === "tech_support") {
    const k = data.kpis ?? {};
    return (
      <div className="grid gap-6">
        <Hero
          eyebrow="Tech support"
          title="Doubt-clearing monitor"
          subtitle="Answer what you can and keep faculty on the response window."
          ctaLabel="Open doubt monitor"
          ctaTo={`/${slug}/monitor`}
          highlight={{ label: "Overdue", value: String(k.overdue ?? 0) }}
        />
        <KpiGrid>
          <StatCard label="Open" value={k.open ?? 0} />
          <StatCard
            label="Unanswered"
            value={k.unanswered ?? 0}
            deltaTone={k.unanswered ? "down" : "up"}
          />
          <StatCard
            label="Overdue"
            value={k.overdue ?? 0}
            deltaTone={k.overdue ? "down" : "up"}
          />
          <StatCard label="Resolved" value={k.resolved ?? 0} deltaTone="up" />
        </KpiGrid>
        <Card>
          <SectionHeading title="Forum status" />
          {data.forum_status && data.forum_status.some((s) => s.value > 0) ? (
            <LazyChart
              kind="bar"
              data={data.forum_status}
              xKey="name"
              series={[{ key: "value", label: "Threads", color: BRAND }]}
              height={240}
            />
          ) : (
            <p className="py-6 text-center text-sm text-muted">No doubts yet.</p>
          )}
        </Card>
      </div>
    );
  }

  return <EmptyState title="Your dashboard is being prepared." />;
}

function StudentBatches({ data }: { data: DashboardData }) {
  return (
    <div>
      <SectionHeading title="My batches" />
      {data.batches && data.batches.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {data.batches.map((b) => (
            <Card key={b.id}>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-base font-medium text-ink">{b.name}</h3>
                <Badge
                  tone={b.state === "active" ? "success" : b.state === "completed" ? "info" : "neutral"}
                >
                  {b.state}
                </Badge>
              </div>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <Field label="Course" value={b.course} />
                <Field label="Batch ID" value={b.code} />
                <Field label="Faculty" value={(b.faculty ?? []).join(", ") || "—"} />
                <Field label="Dates" value={`${b.start_date} → ${b.end_date}`} />
              </dl>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="You are not enrolled in a batch yet." />
      )}
    </div>
  );
}

function FacultyBatches({ data, slug }: { data: DashboardData; slug: string }) {
  return (
    <Card>
      <SectionHeading
        title="Your batches"
        action={
          <Link to={`/${slug}/batches`} className="text-sm font-medium text-brand-strong hover:underline">
            Open batches
          </Link>
        }
      />
      {data.batches && data.batches.length > 0 ? (
        <div className="flex flex-col divide-y divide-brdr">
          {data.batches.map((b) => (
            <div key={b.id} className="flex items-center justify-between py-3">
              <div>
                <div className="text-sm font-medium text-ink">
                  {b.code} · {b.name}
                </div>
                <div className="text-xs text-muted">
                  {b.course} · {b.student_count ?? 0} student(s)
                </div>
              </div>
              <Badge tone={b.state === "active" ? "success" : "neutral"}>{b.state}</Badge>
            </div>
          ))}
        </div>
      ) : (
        <p className="py-6 text-center text-sm text-muted">No batches assigned yet.</p>
      )}
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-ink">{value}</dd>
    </div>
  );
}

function DashboardSkeleton() {
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
