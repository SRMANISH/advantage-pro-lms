import { AlertTriangle, CheckCircle2, GraduationCap, Users } from "lucide-react";

import { StatCard } from "../../../design-system";
import type { DashboardData } from "../../dashboard/api";
import { Hero, KpiGrid, TrendCard } from "./shared";

export function CounselorDashboard({ data, slug }: { data: DashboardData; slug: string }) {
  const k = data.kpis ?? {};

  return (
    <div className="grid gap-6">
      <Hero
        eyebrow="Counsellor portal"
        title="Attendance & follow-up"
        subtitle="Spot absentees early and keep learners on track with MIS."
        ctaLabel="Review attendance"
        ctaTo={`/${slug}/attendance`}
        highlight={{
          label: "Absentees today",
          value: String(k.absentees_today ?? 0),
          icon: AlertTriangle,
        }}
      />
      <KpiGrid>
        <StatCard label="Active students" value={k.active_students ?? 0} icon={GraduationCap} tone="azure" />
        <StatCard label="Logged in today" value={k.logged_in_today ?? 0} icon={CheckCircle2} tone="green" />
        <StatCard
          label="Absentees today"
          value={k.absentees_today ?? 0}
          icon={AlertTriangle}
          tone="rose"
          deltaTone={k.absentees_today ? "down" : "up"}
        />
        <StatCard label="Batches" value={data.totals?.batches ?? 0} icon={Users} tone="navy" />
      </KpiGrid>
      <TrendCard
        data={data.trend}
        title="Login trend"
        subtitle="Student login-days per week — your follow-up radar"
        explain="What this shows: how many days students signed in each week. Falling weeks mean growing absentees — those students are your follow-up list."
      />
    </div>
  );
}
