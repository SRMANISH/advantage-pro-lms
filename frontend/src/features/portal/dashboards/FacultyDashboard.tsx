import { ClipboardCheck, GraduationCap, MessagesSquare, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Card, SectionHeading, StatCard } from "../../../design-system";
import type { DashboardData } from "../../dashboard/api";
import { Hero, KpiGrid, TrendCard, UpNext } from "./shared";

export function FacultyDashboard({
  data,
  name,
  slug,
}: {
  data: DashboardData;
  name: string;
  slug: string;
}) {
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
        highlight={{ label: "Assigned batches", value: String(t.batches ?? 0), icon: Users }}
      />
      <KpiGrid>
        <StatCard label="Batches" value={t.batches ?? 0} icon={Users} tone="azure" />
        <StatCard label="Students" value={t.students ?? 0} icon={GraduationCap} tone="navy" />
        <StatCard
          label="Unanswered doubts"
          value={a.unanswered_doubts ?? 0}
          icon={MessagesSquare}
          tone="amber"
          deltaTone={a.unanswered_doubts ? "down" : "up"}
        />
        <StatCard label="To grade" value={a.submissions_to_grade ?? 0} icon={ClipboardCheck} tone="violet" />
      </KpiGrid>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TrendCard
            data={data.trend}
            title="Batch activity"
            subtitle="Student login-days across your batches, week by week"
            explain="What this shows: how often your students signed in each week. A falling line means rising absentees — worth a look at the Attendance page."
          />
        </div>
        <UpNext items={data.up_next} />
      </div>
      <FacultyBatches data={data} slug={slug} />
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
