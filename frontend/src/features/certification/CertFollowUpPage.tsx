import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import {
  CERT_FOLLOW_UP_STATUSES,
  certificationApi,
  type CertFollowUpStatus,
} from "./api";

export function CertFollowUpPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const rows = useQuery({ queryKey: ["cert-followup"], queryFn: certificationApi.followUpList });
  const remind = useMutation({
    mutationFn: () => certificationApi.remind(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cert-followup"] }),
  });
  const setStatus = useMutation({
    mutationFn: ({ enrollment, status }: { enrollment: string; status: CertFollowUpStatus }) =>
      certificationApi.setFollowUpStatus(enrollment, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cert-followup"] }),
  });

  const data = rows.data ?? [];
  const pending = data.filter((r) => !r.certified).length;

  return (
    <PortalLayout role={role}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-medium text-ink">Certificate follow-up</h1>
        <Button variant="soft" onClick={() => remind.mutate()} disabled={remind.isPending}>
          {remind.isPending ? "Sending…" : "Send weekly reminders"}
        </Button>
      </div>
      <p className="mb-4 text-sm text-muted">
        {data.length} completed-course student(s) · {pending} certificate pending.
      </p>

      <Card>
        {rows.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : data.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-brdr">
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
                {data.map((r) => (
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
        ) : (
          <p className="text-sm text-muted">No completed-course students yet.</p>
        )}
      </Card>
    </PortalLayout>
  );
}
