import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Card, EmptyState, SectionHeading, TableSkeleton } from "../../design-system";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { engagementApi } from "./api";

export function EngagementReportPage({ role }: { role: RoleDef }) {
  const [batchId, setBatchId] = useState("");
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const scope = batchId || undefined;
  const linkedin = useQuery({
    queryKey: ["eng-linkedin", batchId],
    queryFn: () => engagementApi.linkedinReport(scope),
  });
  const google = useQuery({
    queryKey: ["eng-google", batchId],
    queryFn: () => engagementApi.googleReport(scope),
  });
  const plans = useQuery({
    queryKey: ["eng-plans", batchId],
    queryFn: () => engagementApi.nextPlans(scope),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Engagement"
        subtitle="LinkedIn follow, Google reviews and next-plan responses."
      />

      <Card className="mb-6">
        <label htmlFor="eng-batch" className="mb-1 block text-sm text-muted">
          Filter by batch
        </label>
        <select
          id="eng-batch"
          className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm sm:max-w-sm"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
        >
          <option value="">All batches</option>
          {batches.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.code} — {b.name}
            </option>
          ))}
        </select>
      </Card>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-base font-medium text-ink">LinkedIn follow</h2>
          <p className="text-sm text-muted">
            {linkedin.data?.confirmed ?? 0} confirmed · {linkedin.data?.pending ?? 0} pending
          </p>
        </Card>
        <Card>
          <h2 className="mb-2 text-base font-medium text-ink">Google review</h2>
          <p className="text-sm text-muted">
            {google.data?.submitted ?? 0} submitted · {google.data?.pending ?? 0} pending
          </p>
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Course next-plan responses</h2>
        {plans.isLoading ? (
          <TableSkeleton rows={4} cols={6} />
        ) : plans.data && plans.data.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-brdr">
            <table className="w-full text-sm">
              <thead className="bg-sky text-navy">
                <tr>
                  <th className="px-3 py-2 text-left">Registration ID</th>
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Interested course</th>
                  <th className="px-3 py-2 text-left">Timing</th>
                  <th className="px-3 py-2 text-left">Goal</th>
                  <th className="px-3 py-2 text-left">Contact time</th>
                </tr>
              </thead>
              <tbody>
                {plans.data.map((p, i) => (
                  <tr key={i} className="border-t border-brdr">
                    <td className="px-3 py-2">{p.registration_number}</td>
                    <td className="px-3 py-2">{p.student_name}</td>
                    <td className="px-3 py-2">{p.interested_course || "—"}</td>
                    <td className="px-3 py-2 text-muted">{p.expected_timing || "—"}</td>
                    <td className="px-3 py-2 text-muted">{p.goal || "—"}</td>
                    <td className="px-3 py-2 text-muted">{p.preferred_contact_time || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No next-plan responses yet" />
        )}
      </Card>
    </PortalLayout>
  );
}
