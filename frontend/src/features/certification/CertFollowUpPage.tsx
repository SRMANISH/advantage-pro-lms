import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Card,
  EmptyState,
  Paginator,
  SectionHeading,
  TableSkeleton,
} from "../../design-system";
import { fetchPage } from "../../lib/api";
import { useServerTable } from "../../lib/useServerTable";
import { PortalLayout } from "../portal/PortalLayout";
import {
  CERT_FOLLOW_UP_STATUSES,
  certificationApi,
  type CertFollowUpRow,
  type CertFollowUpStatus,
} from "./api";

export function CertFollowUpPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const table = useServerTable<CertFollowUpRow>({
    key: ["cert-followup"],
    fetcher: (p) => fetchPage<CertFollowUpRow>("/certification/follow-up/", p),
  });
  const setStatus = useMutation({
    mutationFn: ({ enrollment, status }: { enrollment: string; status: CertFollowUpStatus }) =>
      certificationApi.setFollowUpStatus(enrollment, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cert-followup"] }),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Certificate follow-up"
        subtitle={`${table.total} completed-course student(s). Weekly reminders send automatically.`}
      />

      <Card>
        {table.isLoading ? (
          <TableSkeleton rows={5} cols={6} />
        ) : table.rows.length > 0 ? (
          <>
            <div className="overflow-x-auto rounded-lg border border-brdr">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Registration ID</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Batch</th>
                    <th className="px-3 py-2 text-left">Certificate</th>
                    <th className="px-3 py-2 text-left">Reminders</th>
                    <th className="px-3 py-2 text-left">Follow-up</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((r) => (
                    <tr key={r.enrollment} className="border-t border-brdr">
                      <td className="px-3 py-2">{r.registration_number}</td>
                      <td className="px-3 py-2">{r.student_name}</td>
                      <td className="px-3 py-2">{r.batch_code}</td>
                      <td className="px-3 py-2">
                        {r.certified ? (
                          <Badge>{r.certificate_id}</Badge>
                        ) : (
                          <span className="text-red-600">pending</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-muted">{r.reminder_count}</td>
                      <td className="px-3 py-2">
                        <select
                          className="h-9 rounded-lg border border-brdr bg-surface px-2 text-sm"
                          value={r.follow_up_status}
                          disabled={r.certified}
                          onChange={(e) =>
                            setStatus.mutate({
                              enrollment: r.enrollment,
                              status: e.target.value as CertFollowUpStatus,
                            })
                          }
                        >
                          {CERT_FOLLOW_UP_STATUSES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginator
              page={table.page}
              pageCount={table.pageCount}
              onPage={table.setPage}
              total={table.total}
            />
          </>
        ) : (
          <EmptyState title="No completed-course students yet" />
        )}
      </Card>
    </PortalLayout>
  );
}
