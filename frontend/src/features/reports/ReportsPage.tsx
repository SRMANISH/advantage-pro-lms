import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { BatchSelect, Button, Card, SectionHeading } from "../../design-system";
import { attendanceApi } from "../attendance/api";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";

const STUDENT_EXPORT_ROLES = new Set(["super_admin", "admin", "mis", "faculty"]);

export function ReportsPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  const batches = useQuery({ queryKey: ["review-batches"], queryFn: attendanceApi.reviewBatches });
  const [batchId, setBatchId] = useState("");
  const canStudents = STUDENT_EXPORT_ROLES.has(user?.role ?? "");

  // Stays an anchor (via Button's href form) so the browser downloads natively.
  const DownloadLink = ({ path, label }: { path: string; label: string }) => (
    <Button variant="soft" href={`/api/v1/reports/${path}/?batch=${batchId}`}>
      Download {label} (CSV)
    </Button>
  );

  return (
    <PortalLayout role={role}>
      <SectionHeading title="Reports & exports" subtitle="Download per-batch CSVs." />

      <Card className="mb-6">
        <BatchSelect
          id="reports-batch"
          value={batchId}
          onChange={setBatchId}
          batches={batches.data}
        />
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
