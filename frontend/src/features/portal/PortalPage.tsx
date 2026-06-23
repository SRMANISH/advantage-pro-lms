import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Badge, Card } from "../../design-system";
import { useAuth } from "../auth/auth";
import { dashboardApi, type DashboardData } from "../dashboard/api";
import { PortalLayout } from "./PortalLayout";

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg bg-sky px-4 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-2xl font-medium text-navy">{value}</div>
    </div>
  );
}

export function PortalPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const name = user?.full_name || user?.username;
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: dashboardApi.get });

  return (
    <PortalLayout role={role}>
      <h1 className="mb-1 text-xl font-medium text-ink">Welcome, {name}</h1>
      <p className="mb-6 text-sm text-muted">{role.label} portal</p>

      {isLoading || !data ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <DashboardBody role={role} data={data} />
      )}
    </PortalLayout>
  );
}

function DashboardBody({ role, data }: { role: RoleDef; data: DashboardData }) {
  if (data.role === "student") {
    return (
      <div className="grid gap-4">
        {data.batches && data.batches.length > 0 ? (
          data.batches.map((b) => (
            <Card key={b.id}>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-base font-medium text-ink">{b.name}</h2>
                <Badge>{b.state}</Badge>
              </div>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <Field label="Course" value={b.course} />
                <Field label="Batch ID" value={b.code} />
                <Field label="Faculty" value={(b.faculty ?? []).join(", ") || "—"} />
                <Field label="Dates" value={`${b.start_date} → ${b.end_date}`} />
              </dl>
              <p className="mt-3 text-xs text-muted">
                Videos, tests, tasks, attendance and the forum appear here as those modules go live.
              </p>
            </Card>
          ))
        ) : (
          <Card>
            <p className="text-sm text-muted">You are not enrolled in a batch yet.</p>
          </Card>
        )}
      </div>
    );
  }

  if (data.role === "faculty") {
    return (
      <div className="grid gap-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Batches" value={data.totals?.batches ?? 0} />
          <Stat label="Students" value={data.totals?.students ?? 0} />
        </div>
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-medium text-ink">Your batches</h2>
            <Link to={`/${role.slug}/batches`} className="text-sm text-brand-strong underline">
              Open batches
            </Link>
          </div>
          {data.batches && data.batches.length > 0 ? (
            <div className="flex flex-col divide-y divide-brdr">
              {data.batches.map((b) => (
                <div key={b.id} className="flex items-center justify-between py-2">
                  <div>
                    <div className="text-sm font-medium text-ink">
                      {b.code} · {b.name}
                    </div>
                    <div className="text-xs text-muted">
                      {b.course} · {b.student_count} student(s)
                    </div>
                  </div>
                  <Badge>{b.state}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">No batches assigned yet.</p>
          )}
        </Card>
      </div>
    );
  }

  if (data.role === "super_admin" || data.role === "admin" || data.role === "mis") {
    return (
      <div className="grid gap-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Batches" value={data.totals?.batches ?? 0} />
          <Stat label="Active batches" value={data.totals?.active_batches ?? 0} />
          <Stat label="Students" value={data.totals?.students ?? 0} />
          <Stat label="Courses" value={data.totals?.courses ?? 0} />
        </div>
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Quick actions</h2>
          <div className="flex flex-wrap gap-3">
            <Link
              to={`/${role.slug}/batches`}
              className="rounded-lg bg-sky px-4 py-2 text-sm font-medium text-navy hover:bg-brand/10"
            >
              Manage batches
            </Link>
            <Link
              to={`/${role.slug}/enrolment`}
              className="rounded-lg bg-sky px-4 py-2 text-sm font-medium text-navy hover:bg-brand/10"
            >
              Enrol students
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  if (data.role === "counselor") {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Students" value={data.totals?.students ?? 0} />
        <Stat label="Batches" value={data.totals?.batches ?? 0} />
      </div>
    );
  }

  return (
    <Card>
      <p className="text-sm text-muted">
        Your tools appear here as their modules go live (e.g. the doubt forum for Tech Support).
      </p>
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
