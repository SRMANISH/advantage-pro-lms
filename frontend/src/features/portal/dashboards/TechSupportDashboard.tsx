import { AlertTriangle, CheckCircle2, Flame, MessagesSquare, Smartphone } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, SectionHeading, StatCard, LazyChart } from "../../../design-system";
import type { DashboardData } from "../../dashboard/api";
import { BRAND, Hero, KpiGrid } from "./shared";

export function TechSupportDashboard({ data, slug }: { data: DashboardData; slug: string }) {
  const k = data.kpis ?? {};
  const deviceRequests = data.attention?.device_requests ?? 0;

  return (
    <div className="grid gap-6">
      <Hero
        eyebrow="Tech support"
        title="Doubt-clearing monitor"
        subtitle="Answer what you can and keep faculty on the response window."
        ctaLabel="Open doubt monitor"
        ctaTo={`/${slug}/monitor`}
        highlight={{ label: "Overdue", value: String(k.overdue ?? 0), icon: Flame }}
      />
      {deviceRequests > 0 && (
        <Link
          to={`/${slug}/devices`}
          className="flex items-center justify-between rounded-2xl border border-amber/40 bg-amber/10 px-5 py-4 transition hover:bg-amber/15"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber/20 text-amber-700">
              <Smartphone size={18} aria-hidden />
            </span>
            <div>
              <div className="text-sm font-semibold text-ink">
                {deviceRequests} device change {deviceRequests === 1 ? "request" : "requests"}{" "}
                waiting
              </div>
              <div className="text-xs text-muted">
                Outside-class device changes are yours to approve — review the queue.
              </div>
            </div>
          </div>
          <span aria-hidden className="text-sm font-semibold text-navy">
            Review →
          </span>
        </Link>
      )}
      <KpiGrid>
        <StatCard label="Open" value={k.open ?? 0} icon={MessagesSquare} tone="azure" />
        <StatCard
          label="Unanswered"
          value={k.unanswered ?? 0}
          icon={AlertTriangle}
          tone="amber"
          deltaTone={k.unanswered ? "down" : "up"}
        />
        <StatCard
          label="Overdue"
          value={k.overdue ?? 0}
          icon={Flame}
          tone="rose"
          deltaTone={k.overdue ? "down" : "up"}
        />
        <StatCard
          label="Resolved"
          value={k.resolved ?? 0}
          icon={CheckCircle2}
          tone="green"
          deltaTone="up"
        />
      </KpiGrid>
      <Card>
        <SectionHeading title="Forum status" subtitle="Every doubt, by its current stage" />
        {data.forum_status && data.forum_status.some((s) => s.value > 0) ? (
          <>
            <LazyChart
              kind="bar"
              data={data.forum_status}
              xKey="name"
              series={[{ key: "value", label: "Doubts", color: BRAND }]}
              height={220}
            />
            <p className="mt-2 rounded-lg bg-sky/50 px-3 py-2 text-xs leading-relaxed text-navy">
              Open = waiting for a first reply · Answered = replied, not yet closed · Escalated =
              pushed to faculty · Resolved = done. Your goal: keep Open near zero within the
              response window.
            </p>
          </>
        ) : (
          <p className="py-6 text-center text-sm text-muted">No doubts yet.</p>
        )}
      </Card>
    </div>
  );
}
