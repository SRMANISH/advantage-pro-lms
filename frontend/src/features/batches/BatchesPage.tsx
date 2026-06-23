import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input, Select } from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { batchesApi, type Batch, type BatchState } from "./api";

const CAN_MANAGE = new Set(["super_admin", "admin", "mis"]);
const NEXT_STATE: Record<BatchState, BatchState | null> = {
  draft: "active",
  active: "completed",
  completed: null,
};
const NEXT_LABEL: Record<string, string> = { active: "Activate", completed: "Complete" };

export function BatchesPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canManage = CAN_MANAGE.has(user?.role ?? "");

  const courses = useQuery({ queryKey: ["courses"], queryFn: batchesApi.listCourses });
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const faculty = useQuery({ queryKey: ["faculty"], queryFn: batchesApi.listFaculty });

  const refetchBatches = () => qc.invalidateQueries({ queryKey: ["batches"] });
  const createCourse = useMutation({
    mutationFn: batchesApi.createCourse,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["courses"] }),
  });
  const createBatch = useMutation({ mutationFn: batchesApi.createBatch, onSuccess: refetchBatches });
  const transition = useMutation({
    mutationFn: (v: { id: string; to: BatchState }) => batchesApi.transition(v.id, v.to),
    onSuccess: refetchBatches,
  });
  const assign = useMutation({
    mutationFn: (v: { id: string; fid: string }) => batchesApi.assignFaculty(v.id, [v.fid]),
    onSuccess: refetchBatches,
  });

  const [cCode, setCCode] = useState("");
  const [cName, setCName] = useState("");
  const [b, setB] = useState({ code: "", name: "", course: "", start_date: "", end_date: "" });

  return (
    <PortalLayout role={role}>
      <h1 className="mb-4 text-xl font-medium text-ink">Batches</h1>

      {canManage && (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">New course</h2>
            <form
              className="flex flex-col gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createCourse.mutate(
                  { code: cCode, name: cName },
                  { onSuccess: () => (setCCode(""), setCName("")) },
                );
              }}
            >
              <Input placeholder="Code (e.g. FS)" value={cCode} onChange={(e) => setCCode(e.target.value)} />
              <Input placeholder="Name" value={cName} onChange={(e) => setCName(e.target.value)} />
              <Button type="submit" variant="soft" disabled={!cCode || !cName || createCourse.isPending}>
                Add course
              </Button>
            </form>
          </Card>

          <Card>
            <h2 className="mb-3 text-base font-medium text-ink">New batch</h2>
            <form
              className="flex flex-col gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createBatch.mutate(b, {
                  onSuccess: () =>
                    setB({ code: "", name: "", course: "", start_date: "", end_date: "" }),
                });
              }}
            >
              <Input placeholder="Batch ID (e.g. FS-2026A)" value={b.code} onChange={(e) => setB({ ...b, code: e.target.value })} />
              <Input placeholder="Name" value={b.name} onChange={(e) => setB({ ...b, name: e.target.value })} />
              <Select value={b.course} onChange={(e) => setB({ ...b, course: e.target.value })}>
                <option value="">Select course…</option>
                {courses.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.name}
                  </option>
                ))}
              </Select>
              <div className="flex gap-2">
                <Input type="date" value={b.start_date} onChange={(e) => setB({ ...b, start_date: e.target.value })} />
                <Input type="date" value={b.end_date} onChange={(e) => setB({ ...b, end_date: e.target.value })} />
              </div>
              <Button
                type="submit"
                disabled={
                  !b.code || !b.name || !b.course || !b.start_date || !b.end_date || createBatch.isPending
                }
              >
                Create batch
              </Button>
              {createBatch.isError && (
                <p className="text-sm text-red-600" role="alert">
                  Could not create batch — check the batch ID is unique and dates are valid.
                </p>
              )}
            </form>
          </Card>
        </div>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">
          {canManage ? "All batches" : "Your batches"}
        </h2>
        {batches.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : batches.data && batches.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {batches.data.map((batch) => (
              <BatchRow
                key={batch.id}
                batch={batch}
                facultyOptions={faculty.data ?? []}
                canManage={canManage}
                onTransition={(to) => transition.mutate({ id: batch.id, to })}
                onAssign={(fid) => assign.mutate({ id: batch.id, fid })}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No batches yet.</p>
        )}
      </Card>
    </PortalLayout>
  );
}

function BatchRow({
  batch,
  facultyOptions,
  canManage,
  onTransition,
  onAssign,
}: {
  batch: Batch;
  facultyOptions: { id: string; full_name: string; username: string }[];
  canManage: boolean;
  onTransition: (to: BatchState) => void;
  onAssign: (facultyId: string) => void;
}) {
  const next = NEXT_STATE[batch.state];
  const assigned = new Set(batch.faculty);
  const available = facultyOptions.filter((f) => !assigned.has(f.id));

  return (
    <div className="flex flex-wrap items-center gap-3 py-3">
      <div className="min-w-40 flex-1">
        <div className="text-sm font-medium text-ink">
          {batch.code} · {batch.name}
        </div>
        <div className="text-xs text-muted">
          {batch.course_detail.code} · {batch.start_date} → {batch.end_date}
        </div>
        {batch.faculty_detail.length > 0 && (
          <div className="mt-1 text-xs text-muted">
            Faculty: {batch.faculty_detail.map((f) => f.full_name || f.username).join(", ")}
          </div>
        )}
      </div>

      <Badge>{batch.state}</Badge>

      {canManage && next && (
        <Button variant="soft" onClick={() => onTransition(next)}>
          {NEXT_LABEL[next]}
        </Button>
      )}

      <Select
        className="w-44"
        value=""
        onChange={(e) => e.target.value && onAssign(e.target.value)}
      >
        <option value="">Assign faculty…</option>
        {available.map((f) => (
          <option key={f.id} value={f.id}>
            {f.full_name || f.username}
          </option>
        ))}
      </Select>
    </div>
  );
}
