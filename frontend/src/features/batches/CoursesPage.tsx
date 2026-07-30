import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  SectionHeading,
  useToast,
} from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { batchesApi } from "./api";

const empty = { code: "", name: "", description: "", duration: "", fees: "" };

/** Super Admin defines courses — including duration and fees (updated procedure). */
export function CoursesPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const courses = useQuery({ queryKey: ["courses"], queryFn: batchesApi.listCourses });
  const [form, setForm] = useState(empty);

  const create = useMutation({
    mutationFn: () =>
      batchesApi.createCourse({
        code: form.code,
        name: form.name,
        description: form.description || undefined,
        duration: form.duration || undefined,
        fees: form.fees || undefined,
      }),
    onSuccess: () => {
      setForm(empty);
      qc.invalidateQueries({ queryKey: ["courses"] });
      toast.show("Course created.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Courses"
        subtitle="Define courses with their duration and fees. Admin builds batches from these."
      />

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">New course</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input
            placeholder="Code (e.g. FS)"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          <Input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            placeholder="Duration (e.g. 3 months)"
            value={form.duration}
            onChange={(e) => setForm({ ...form, duration: e.target.value })}
          />
          <Input
            placeholder="Fees (e.g. 45000)"
            inputMode="decimal"
            value={form.fees}
            onChange={(e) => setForm({ ...form, fees: e.target.value })}
          />
        </div>
        <Input
          className="mt-2"
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <Button
          className="mt-3"
          onClick={() => create.mutate()}
          disabled={!form.code || !form.name || create.isPending}
        >
          {create.isPending ? "Creating…" : "Create course"}
        </Button>
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">All courses</h2>
        {courses.isLoading ? (
          <ListSkeleton items={3} />
        ) : courses.data && courses.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {courses.data.map((c) => (
              <div
                key={c.id}
                className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-ink">{c.code}</span>
                  <span className="text-muted"> · {c.name}</span>
                </div>
                <div className="text-xs text-muted">
                  {c.duration || "duration not set"}
                  {c.fees != null && c.fees !== "" && ` · ₹${c.fees}`}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No courses yet" />
        )}
      </Card>
    </PortalLayout>
  );
}
