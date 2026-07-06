import { Award, BookOpen, GraduationCap, Users } from "lucide-react";

import { Card, LazyChart, SectionHeading, StatCard } from "../../../design-system";
import type { DashboardData } from "../../dashboard/api";
import { Hero, KpiGrid, TrendCard } from "./shared";

/** Super Admin, Admin and MIS share this operations-overview dashboard shape. */
export function OpsDashboard({ data, slug }: { data: DashboardData; slug: string }) {
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
        highlight={{ label: "Active batches", value: String(t.active_batches ?? 0), icon: Users }}
      />
      <KpiGrid>
        <StatCard label="Total students" value={t.students ?? 0} icon={GraduationCap} tone="azure" />
        <StatCard label="Active batches" value={t.active_batches ?? 0} icon={Users} tone="green" />
        <StatCard label="Courses" value={t.courses ?? 0} icon={BookOpen} tone="violet" />
        <StatCard
          label="Certificates pending"
          value={a.certificate_pending ?? 0}
          icon={Award}
          tone="amber"
          deltaTone={a.certificate_pending ? "down" : "up"}
        />
      </KpiGrid>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrendCard
            data={data.trend}
            title="Platform activity"
            subtitle="Student login-days across all batches, week by week"
            explain="What this shows: total days students signed in per week, platform-wide. Steady or rising = healthy engagement; a drop is your early warning."
          />
        </div>
        <Card>
          <SectionHeading title="Batch states" subtitle="Where every batch is in its lifecycle" />
          {data.batch_states && data.batch_states.some((s) => s.value > 0) ? (
            <>
              <LazyChart kind="donut" data={data.batch_states} height={220} />
              <p className="mt-2 rounded-lg bg-sky/50 px-3 py-2 text-xs leading-relaxed text-navy">
                Draft = being set up · Active = running now · Completed = finished (video
                access closed, certificates in follow-up).
              </p>
            </>
          ) : (
            <p className="py-6 text-center text-sm text-muted">No batches yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
