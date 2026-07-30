import { CalendarCheck, ClipboardList, FileText, Flame } from "lucide-react";

import {
  Badge,
  Card,
  EmptyState,
  SectionHeading,
  Sparkline,
  StatCard,
} from "../../../design-system";
import type { DashboardData } from "../../dashboard/api";
import { Field, Hero, KpiGrid, TrendCard, UpNext } from "./shared";

export function StudentDashboard({
  data,
  name,
  slug,
}: {
  data: DashboardData;
  name: string;
  slug: string;
}) {
  const k = data.kpis ?? {};
  const v = data.videos ?? { completed: 0, total: 0 };
  const videoPct = v.total ? Math.round((v.completed / v.total) * 100) : 0;
  const trendValues = (data.trend ?? []).map((t) => t.value);

  return (
    <div className="grid gap-6">
      <Hero
        eyebrow="Student portal"
        title={`Welcome back, ${name.split(" ")[0] || name}`}
        subtitle="Keep your streak going — your batch content is below."
        ctaLabel="Continue learning"
        ctaTo={`/${slug}/videos`}
        highlight={{
          label: "Videos completed",
          value: `${videoPct}%`,
          percent: videoPct,
          sub: `${v.completed} of ${v.total} videos watched`,
        }}
      />
      <KpiGrid>
        <StatCard
          label="Attendance"
          value={k.attendance_pct ?? 0}
          suffix="%"
          icon={CalendarCheck}
          tone="green"
          footer={<Sparkline data={trendValues} />}
        />
        <StatCard label="Pending tasks" value={k.pending_tasks ?? 0} icon={FileText} tone="amber" />
        <StatCard
          label="Upcoming tests"
          value={k.upcoming_tests ?? 0}
          icon={ClipboardList}
          tone="violet"
        />
        <StatCard
          label="Login streak"
          value={k.streak_days ?? 0}
          suffix=" days"
          icon={Flame}
          tone="rose"
          delta={k.streak_days && k.streak_days >= 3 ? "keep it up!" : undefined}
        />
      </KpiGrid>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrendCard
            data={data.trend}
            title="Your activity"
            subtitle="How many days you signed in, week by week (last 6 weeks)"
            explain="What this shows: each point is the number of days you logged in that week. Every login day counts toward your attendance — so taller weeks mean better attendance."
          />
        </div>
        <UpNext items={data.up_next} />
      </div>
      <StudentBatches data={data} />
    </div>
  );
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
                  tone={
                    b.state === "active" ? "success" : b.state === "completed" ? "info" : "neutral"
                  }
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
