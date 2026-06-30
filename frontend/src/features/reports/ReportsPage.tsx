import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Card, SectionHeading } from "../../design-system";
import { attendanceApi } from "../attendance/api";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";

const STUDENT_EXPORT_ROLES = new Set(["super_admin", "admin", "mis", "faculty"]);

export function ReportsPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const batches = useQuery({ queryKey: ["review-batches"], queryFn: attendanceApi.reviewBatches });
  const [batchId, setBatchId] = useState("");
  const canStudents = STUDENT_EXPORT_ROLES.has(user?.role ?? "");

  const DownloadLink = ({ path, label }: { path: string; label: string }) => (
    <a
      href={`/api/v1/reports/${path}/?batch=${batchId}`}
      className="rounded-lg bg-sky px-4 py-2 text-sm font-medium text-navy hover:bg-brand/10"
    >
      Download {label} (CSV)
    </a>
  );

  return (
    <PortalLayout role={role}>
      <SectionHeading title="Reports & exports" subtitle="Download per-batch CSVs." />

      <Card className="mb-6">
        <label className="mb-1 block text-sm text-muted">Batch</label>
        <select
          className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
        >
          <option value="">Select a batch…</option>
          {batches.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.code} — {b.name}
            </option>
          ))}
        </select>
      </Card>

      {batchId && (
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Exports</h2>
          <div className="flex flex-wrap gap-3">
            {canStudents && <DownloadLink path="students" label="students" />}
            <DownloadLink path="attendance" label="attendance" />
            <DownloadLink path="performance" label="performance" />
          </div>
        </Card>
      )}
    </PortalLayout>
  );
}
