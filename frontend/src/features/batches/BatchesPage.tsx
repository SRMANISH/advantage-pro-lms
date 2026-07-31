import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  QueryError,
  SectionHeading,
  Select,
  useToast,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import {
  batchesApi,
  WEEKDAYS,
  type Batch,
  type BatchState,
  type FacultyBrief,
  type Weekday,
} from "./api";

const DAY_LABEL: Record<Weekday, string> = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun",
};

function serverDetail(e: unknown, fallback: string): string {
  return (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;
}

// Batch creation, lifecycle, and faculty assignment are Admin-only under the updated
// procedure. MIS/Faculty can view batches but not manage them.
const CAN_MANAGE = new Set(["admin"]);
const NEXT_STATE: Record<BatchState, BatchState | null> = {
  draft: "active",
  active: "completed",
  completed: null,
};
const NEXT_LABEL: Record<string, string> = { active: "Activate", completed: "Complete" };

const emptyBatch = {
  code: "",
  name: "",
  course: "",
  start_date: "",
  end_date: "",
  class_days: [] as Weekday[],
  class_start_time: "",
  class_end_time: "",
};

export function BatchesPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const canManage = CAN_MANAGE.has(user?.role ?? "");

  const courses = useQuery({ queryKey: ["courses"], queryFn: batchesApi.listCourses });
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const faculty = useQuery({ queryKey: ["faculty"], queryFn: batchesApi.listFaculty });

  const refetchBatches = () => qc.invalidateQueries({ queryKey: ["batches"] });
  const [createError, setCreateError] = useState("");
  const createBatch = useMutation({
    mutationFn: batchesApi.createBatch,
    onSuccess: () => {
      setCreateError("");
      refetchBatches();
    },
    onError: (e) => setCreateError(serverDetail(e, "Could not create batch — check the fields.")),
  });
  const transition = useMutation({
    mutationFn: (v: { id: string; to: BatchState }) => batchesApi.transition(v.id, v.to),
    onSuccess: refetchBatches,
  });
  const assign = useMutation({
    mutationFn: (v: { id: string; primary?: string; soft?: string }) =>
      batchesApi.assignFaculty(v.id, {
        ...(v.primary ? { primary_faculty: v.primary } : {}),
        ...(v.soft ? { faculty_ids: [v.soft] } : {}),
      }),
    onSuccess: () => {
      refetchBatches();
      toast.show("Faculty assigned.", "success");
    },
    onError: (e) => toast.show(serverDetail(e, "Could not assign faculty."), "error"),
  });

  const [b, setB] = useState(emptyBatch);
  const toggleDay = (d: Weekday) =>
    setB((prev) => ({
      ...prev,
      class_days: prev.class_days.includes(d)
        ? prev.class_days.filter((x) => x !== d)
        : [...prev.class_days, d],
    }));

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Batches"
        subtitle={
          canManage
            ? "Create batches, assign faculty, and track every cohort."
            : "Your assigned cohorts."
        }
      />

      {canManage && (
        <div className="mb-6 grid gap-4">
          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">New batch</h2>
            <form
              className="flex flex-col gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createBatch.mutate(b, { onSuccess: () => setB(emptyBatch) });
              }}
            >
              <div className="grid gap-2 sm:grid-cols-2">
                <Input
                  placeholder="Batch ID (e.g. FS-2026A)"
                  value={b.code}
                  onChange={(e) => setB({ ...b, code: e.target.value })}
                />
                <Input
                  placeholder="Name"
                  value={b.name}
                  onChange={(e) => setB({ ...b, name: e.target.value })}
                />
              </div>
              <Select value={b.course} onChange={(e) => setB({ ...b, course: e.target.value })}>
                <option value="">Select course…</option>
                {courses.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </Select>
              <div className="flex flex-wrap gap-2">
                <label htmlFor="batch-start" className="flex-1 text-xs text-muted">
                  Start date
                  <Input
                    id="batch-start"
                    type="date"
                    value={b.start_date}
                    onChange={(e) => setB({ ...b, start_date: e.target.value })}
                  />
                </label>
                <label htmlFor="batch-end" className="flex-1 text-xs text-muted">
                  End date
                  <Input
                    id="batch-end"
                    type="date"
                    value={b.end_date}
                    onChange={(e) => setB({ ...b, end_date: e.target.value })}
                  />
                </label>
              </div>

              {/* Weekly class schedule — required (req 14). */}
              <div className="rounded-lg border border-brdr bg-sky/30 p-3">
                <div className="mb-2 text-xs font-medium text-navy">Class schedule (required)</div>
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {WEEKDAYS.map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => toggleDay(d)}
                      className={
                        b.class_days.includes(d)
                          ? "rounded-lg bg-brand px-2.5 py-1 text-xs font-medium text-white"
                          : "rounded-lg border border-brdr bg-surface px-2.5 py-1 text-xs text-ink hover:bg-sky"
                      }
                    >
                      {DAY_LABEL[d]}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <label htmlFor="class-from" className="flex-1 text-xs text-muted">
                    From
                    <Input
                      id="class-from"
                      type="time"
                      value={b.class_start_time}
                      onChange={(e) => setB({ ...b, class_start_time: e.target.value })}
                    />
                  </label>
                  <label htmlFor="class-to" className="flex-1 text-xs text-muted">
                    To
                    <Input
                      id="class-to"
                      type="time"
                      value={b.class_end_time}
                      onChange={(e) => setB({ ...b, class_end_time: e.target.value })}
                    />
                  </label>
                </div>
              </div>

              <Button
                type="submit"
                disabled={
                  !b.code ||
                  !b.name ||
                  !b.course ||
                  !b.start_date ||
                  !b.end_date ||
                  b.class_days.length === 0 ||
                  !b.class_start_time ||
                  !b.class_end_time ||
                  createBatch.isPending
                }
              >
                Create batch
              </Button>
              {createError && (
                <p className="text-sm text-red-600" role="alert">
                  {createError}
                </p>
              )}
            </form>
          </Card>
        </div>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">
          {user?.role === "faculty" ? "Your batches" : "All batches"}
        </h2>
        {batches.isLoading ? (
          <ListSkeleton items={3} />
        ) : batches.isError ? (
          <QueryError onRetry={() => batches.refetch()} />
        ) : batches.data && batches.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {batches.data.map((batch) => (
              <BatchRow
                key={batch.id}
                batch={batch}
                facultyOptions={faculty.data ?? []}
                canManage={canManage}
                onTransition={(to) => transition.mutate({ id: batch.id, to })}
                onAssignPrimary={(fid) => assign.mutate({ id: batch.id, primary: fid })}
                onAssignSoft={(fid) => assign.mutate({ id: batch.id, soft: fid })}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No batches yet" />
        )}
      </Card>
    </PortalLayout>
  );
}

function facultyLabel(f: FacultyBrief): string {
  const name = f.full_name || f.username;
  return f.skills ? `${name} — ${f.skills}` : name;
}

function BatchRow({
  batch,
  facultyOptions,
  canManage,
  onTransition,
  onAssignPrimary,
  onAssignSoft,
}: {
  batch: Batch;
  facultyOptions: FacultyBrief[];
  canManage: boolean;
  onTransition: (to: BatchState) => void;
  onAssignPrimary: (facultyId: string) => void;
  onAssignSoft: (facultyId: string) => void;
}) {
  const next = NEXT_STATE[batch.state];
  const assigned = new Set(batch.faculty);
  const available = facultyOptions.filter((f) => !assigned.has(f.id));
  const soft = batch.faculty_detail.filter((f) => f.id !== batch.primary_faculty);
  const days = batch.class_days.map((d) => DAY_LABEL[d]).join(" ");
  const time =
    batch.class_start_time && batch.class_end_time
      ? `${batch.class_start_time.slice(0, 5)}–${batch.class_end_time.slice(0, 5)}`
      : "";

  return (
    <div className="flex flex-wrap items-center gap-3 py-3">
      <div className="min-w-40 flex-1">
        <div className="text-sm font-medium text-ink">
          {batch.code} · {batch.name}
        </div>
        <div className="text-xs text-muted">
          {batch.course_detail.code} · {batch.start_date} → {batch.end_date}
          {days && ` · ${days} ${time}`}
        </div>
        {batch.primary_faculty_detail && (
          <div className="mt-1 text-xs text-muted">
            <span className="text-navy">★ Primary:</span>{" "}
            {batch.primary_faculty_detail.full_name || batch.primary_faculty_detail.username}
            {soft.length > 0 &&
              ` · Support: ${soft.map((f) => f.full_name || f.username).join(", ")}`}
          </div>
        )}
      </div>

      <Badge>{batch.state}</Badge>

      {canManage && next && (
        <Button variant="soft" onClick={() => onTransition(next)}>
          {NEXT_LABEL[next]}
        </Button>
      )}

      {canManage && (
        <div className="flex flex-col gap-1.5 sm:flex-row">
          <Select
            className="w-48"
            aria-label={`Set primary faculty for ${batch.code}`}
            value=""
            onChange={(e) => e.target.value && onAssignPrimary(e.target.value)}
          >
            <option value="">Set primary faculty…</option>
            {facultyOptions.map((f) => (
              <option key={f.id} value={f.id}>
                {facultyLabel(f)}
              </option>
            ))}
          </Select>
          <Select
            className="w-48"
            aria-label={`Add support faculty for ${batch.code}`}
            value=""
            onChange={(e) => e.target.value && onAssignSoft(e.target.value)}
          >
            <option value="">Add support faculty…</option>
            {available.map((f) => (
              <option key={f.id} value={f.id}>
                {facultyLabel(f)}
              </option>
            ))}
          </Select>
        </div>
      )}
    </div>
  );
}
