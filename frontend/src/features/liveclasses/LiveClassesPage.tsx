import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, EmptyState, Input, SectionHeading } from "../../design-system";
import { useAuth } from "../auth/auth";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { liveApi, type LiveClass } from "./api";

// Faculty schedule (and cancel) their own batches' classes under the updated procedure.
const SCHEDULE_ROLES = new Set(["faculty"]);

export function LiveClassesPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canSchedule = SCHEDULE_ROLES.has(user?.role ?? "");
  const isStudent = user?.role === "student";

  const classes = useQuery({ queryKey: ["liveclasses"], queryFn: () => liveApi.list() });
  const batches = useQuery({
    queryKey: ["batches"],
    queryFn: batchesApi.listBatches,
    enabled: canSchedule,
  });

  const [form, setForm] = useState({
    batch: "",
    title: "",
    scheduled_at: "",
    platform: "Google Meet",
    meeting_link: "",
  });
  const create = useMutation({
    mutationFn: () =>
      liveApi.create({
        ...form,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
      }),
    onSuccess: () => {
      setForm({ batch: "", title: "", scheduled_at: "", platform: "Google Meet", meeting_link: "" });
      qc.invalidateQueries({ queryKey: ["liveclasses"] });
    },
  });
  const checkIn = useMutation({
    mutationFn: (id: string) => liveApi.checkIn(id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["liveclasses"] });
      if (data.meeting_link) window.open(data.meeting_link, "_blank", "noopener");
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => liveApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["liveclasses"] }),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading title="Live classes" subtitle="Scheduled sessions with reminders and check-in." />

      {canSchedule && (
        <Card className="mb-6">
          <h2 className="mb-3 text-base font-medium text-ink">Schedule a class</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <select
              className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
              value={form.batch}
              onChange={(e) => setForm({ ...form, batch: e.target.value })}
            >
              <option value="">Select batch…</option>
              {batches.data?.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.code} — {b.name}
                </option>
              ))}
            </select>
            <Input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Input
              type="datetime-local"
              value={form.scheduled_at}
              onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
            />
            <Input
              placeholder="Platform"
              value={form.platform}
              onChange={(e) => setForm({ ...form, platform: e.target.value })}
            />
            <Input
              className="sm:col-span-2"
              placeholder="Meeting link (https://…)"
              value={form.meeting_link}
              onChange={(e) => setForm({ ...form, meeting_link: e.target.value })}
            />
            <Button
              className="w-fit sm:col-span-2"
              onClick={() => create.mutate()}
              disabled={
                !form.batch || !form.title || !form.scheduled_at || !form.meeting_link || create.isPending
              }
            >
              {create.isPending ? "Scheduling…" : "Schedule + notify"}
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Schedule</h2>
        {classes.data && classes.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {classes.data.map((c) => (
              <Row
                key={c.id}
                live={c}
                isStudent={isStudent}
                canSchedule={canSchedule}
                onJoin={() => checkIn.mutate(c.id)}
                onCancel={() => cancel.mutate(c.id)}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No live classes scheduled" />
        )}
      </Card>
    </PortalLayout>
  );
}

function Row({
  live,
  isStudent,
  canSchedule,
  onJoin,
  onCancel,
}: {
  live: LiveClass;
  isStudent: boolean;
  canSchedule: boolean;
  onJoin: () => void;
  onCancel: () => void;
}) {
  const dt = new Date(live.scheduled_at);
  const time = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const cancelled = live.status === "cancelled";
  const past = !cancelled && dt.getTime() < Date.now();
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="flex min-w-0 items-center gap-4">
        <div
          className={`flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl ${
            cancelled ? "bg-appbg text-muted" : past ? "bg-sky text-navy" : "bg-brand/10 text-brand-strong"
          }`}
        >
          <span className="text-lg font-bold leading-none">{dt.getDate()}</span>
          <span className="text-[10px] font-medium uppercase">
            {dt.toLocaleString([], { month: "short" })}
          </span>
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`text-sm font-semibold ${cancelled ? "text-muted line-through" : "text-ink"}`}>
              {live.title}
            </span>
            {cancelled ? (
              <Badge tone="danger">cancelled</Badge>
            ) : past ? (
              <Badge tone="neutral">completed</Badge>
            ) : (
              <Badge tone="success">upcoming</Badge>
            )}
          </div>
          <div className="truncate text-xs text-muted">
            {live.batch_code} · {time} · {live.platform}
            {cancelled && live.cancel_reason ? ` · ${live.cancel_reason}` : ""}
          </div>
        </div>
      </div>
      {cancelled ? null : isStudent ? (
        live.checked_in ? (
          <div className="flex items-center gap-2">
            <Badge>checked in</Badge>
            <a href={live.meeting_link} target="_blank" rel="noreferrer" className="text-sm text-brand-strong underline">
              Join
            </a>
          </div>
        ) : (
          <Button onClick={onJoin}>Join &amp; check in</Button>
        )
      ) : (
        <div className="flex items-center gap-2">
          <a href={live.meeting_link} target="_blank" rel="noreferrer" className="text-sm text-brand-strong underline">
            Open link
          </a>
          {canSchedule && (
            <Button variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
