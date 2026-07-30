import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  BatchSelect,
  Button,
  Card,
  EmptyState,
  Paginator,
  SectionHeading,
  TableSkeleton,
} from "../../design-system";
import { api, fetchPage } from "../../lib/api";
import { useServerTable } from "../../lib/useServerTable";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";

interface RunResult {
  test_reminders: number;
  attendance_alerts: number;
}

interface EscalationRow {
  id: string;
  kind: string;
  student_name: string;
  registration_number: string;
  batch_code: string;
  reference_id: string;
  created_at: string;
}

const KIND_LABEL: Record<string, string> = {
  test_incomplete: "Incomplete test",
  low_attendance: "Low attendance",
};

export function EscalationsPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const [batchId, setBatchId] = useState("");
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const escalations = useServerTable<EscalationRow>({
    key: ["escalations"],
    params: { batch: batchId || undefined },
    fetcher: (p) => fetchPage<EscalationRow>("/escalations/", p),
  });

  const run = useMutation({
    mutationFn: async (): Promise<RunResult> => (await api.post("/escalations/run/")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["escalations"] }),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Escalations"
        subtitle="Incomplete-test reminders and the 50%-attendance rule. Runs on a schedule in production — trigger manually here."
      />

      <Card>
        <Button onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? "Running…" : "Run checks now"}
        </Button>
        {run.isSuccess && run.data && (
          <p className="mt-3 text-sm text-success">
            ✓ Sent {run.data.test_reminders} test reminder(s) and {run.data.attendance_alerts}{" "}
            attendance alert(s).
          </p>
        )}
      </Card>

      <Card className="mt-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-medium text-ink">Raised escalations</h2>
          <div className="w-full sm:w-64">
            <BatchSelect
              id="escalations-batch"
              label="Filter escalations by batch"
              hideLabel
              placeholder="All batches"
              value={batchId}
              onChange={setBatchId}
              batches={batches.data}
            />
          </div>
        </div>
        {escalations.isLoading ? (
          <TableSkeleton rows={4} cols={4} />
        ) : escalations.rows.length > 0 ? (
          <>
            <div className="overflow-x-auto rounded-lg border border-brdr">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Type</th>
                    <th className="px-3 py-2 text-left">Student</th>
                    <th className="px-3 py-2 text-left">Batch</th>
                    <th className="px-3 py-2 text-left">Raised</th>
                  </tr>
                </thead>
                <tbody>
                  {escalations.rows.map((e) => (
                    <tr key={e.id} className="border-t border-brdr">
                      <td className="px-3 py-2">
                        <Badge tone={e.kind === "low_attendance" ? "warning" : "info"}>
                          {KIND_LABEL[e.kind] ?? e.kind}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-ink">{e.student_name}</span>{" "}
                        <span className="text-muted">({e.registration_number})</span>
                      </td>
                      <td className="px-3 py-2 text-muted">{e.batch_code || "—"}</td>
                      <td className="px-3 py-2 text-muted">
                        {new Date(e.created_at).toLocaleDateString([], {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginator
              page={escalations.page}
              pageCount={escalations.pageCount}
              onPage={escalations.setPage}
              total={escalations.total}
            />
          </>
        ) : (
          <EmptyState title="No escalations raised" hint="Run the checks or wait for the schedule." />
        )}
      </Card>

      <Card className="mt-4">
        <h2 className="mb-1 text-base font-medium text-ink">Certificate reminders</h2>
        <p className="text-sm text-muted">
          Students in completed batches who haven&apos;t entered their Certificate ID are
          reminded <span className="font-medium text-ink">automatically every week</span> — no
          manual trigger needed. Track progress on the Certificate follow-up page.
        </p>
      </Card>
    </PortalLayout>
  );
}
