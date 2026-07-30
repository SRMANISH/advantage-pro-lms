import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Paginator,
  SectionHeading,
  TableSkeleton,
  useToast,
} from "../../design-system";
import { fetchPage } from "../../lib/api";
import { useServerTable } from "../../lib/useServerTable";
import { PortalLayout } from "../portal/PortalLayout";
import { welcomeApi, type GoodiesRow } from "./api";

/** Admin/MIS register (reqs 16/17): student addresses + goodies received/sent flags. */
export function GoodiesPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const table = useServerTable<GoodiesRow>({
    key: ["goodies-register"],
    fetcher: (p) => fetchPage<GoodiesRow>("/welcome/register/", p),
  });

  const setSent = useMutation({
    mutationFn: (vars: { enrollment: string; sent: boolean }) =>
      welcomeApi.setGoodiesSent(vars.enrollment, vars.sent),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goodies-register"] });
      toast.show("Updated.", "success");
    },
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Addresses & goodies"
        subtitle="Student addresses collected at welcome, and whether their Advantage Pro goodies have been sent."
      />
      <Card>
        {table.isLoading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : table.rows.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-sky text-navy">
                  <tr>
                    <th className="px-3 py-2 text-left">Registration ID</th>
                    <th className="px-3 py-2 text-left">Name</th>
                    <th className="px-3 py-2 text-left">Batch</th>
                    <th className="px-3 py-2 text-left">Address</th>
                    <th className="px-3 py-2 text-left">Received?</th>
                    <th className="px-3 py-2 text-left">Sent</th>
                  </tr>
                </thead>
                <tbody>
                  {table.rows.map((r) => (
                    <tr key={r.enrollment} className="border-t border-brdr">
                      <td className="px-3 py-2 font-medium text-ink">{r.registration_number}</td>
                      <td className="px-3 py-2">{r.student_name}</td>
                      <td className="px-3 py-2">{r.batch_code}</td>
                      <td className="max-w-xs px-3 py-2 text-muted">
                        {r.address || <span className="italic">Not provided</span>}
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={r.goodies_received ? "success" : "neutral"}>
                          {r.goodies_received ? "yes" : "no"}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        {r.goodies_sent ? (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              setSent.mutate({ enrollment: r.enrollment, sent: false })
                            }
                          >
                            ✓ Sent
                          </Button>
                        ) : (
                          <Button
                            variant="soft"
                            onClick={() => setSent.mutate({ enrollment: r.enrollment, sent: true })}
                          >
                            Mark sent
                          </Button>
                        )}
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
          <EmptyState title="No enrolments yet" />
        )}
      </Card>
    </PortalLayout>
  );
}
