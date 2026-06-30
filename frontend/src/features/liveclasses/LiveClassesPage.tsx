import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input } from "../../design-system";
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
      <h1 className="mb-4 text-xl font-medium text-ink">Live classes</h1>

      {canSchedule && (
        <Card className="mb-6">
          <h2 className="mb-3 text-base font-medium text-ink">Schedule a class</h2>
          <div className="flex flex-col gap-2">
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
            <div className="flex gap-2">
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
            </div>
            <Input
              placeholder="Meeting link (https://…)"
              value={form.meeting_link}
              onChange={(e) => setForm({ ...form, meeting_link: e.target.value })}
            />
            <Button
              className="w-fit"
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
          <p className="text-sm text-muted">No live classes scheduled.</p>
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
  const when = new Date(live.scheduled_at).toLocaleString();
  const cancelled = live.status === "cancelled";
  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${cancelled ? "text-muted line-through" : "text-ink"}`}>
            {live.title}
          </span>
          {cancelled && <Badge>cancelled</Badge>}
        </div>
        <div className="text-xs text-muted">
          {live.batch_code} · {when} · {live.platform}
          {cancelled && live.cancel_reason ? ` · ${live.cancel_reason}` : ""}
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
