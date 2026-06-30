import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { Button, Card, EmptyState, SectionHeading, useToast } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { devicesApi } from "./api";

export function DevicesPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const requests = useQuery({ queryKey: ["device-requests"], queryFn: devicesApi.listRequests });
  const decide = useMutation({
    mutationFn: (v: { id: string; decision: "approve" | "reject" }) =>
      devicesApi.decide(v.id, v.decision),
    onSuccess: (_d, v) => {
      qc.invalidateQueries({ queryKey: ["device-requests"] });
      toast.show(v.decision === "approve" ? "Device approved." : "Request rejected.", "success");
    },
    onError: () => toast.show("Could not action this request.", "error"),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Device requests"
        subtitle="Faculty approve a change during a live class; MIS approve outside class hours."
      />

      <Card>
        {requests.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : requests.data && requests.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {requests.data.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-ink">{r.student_name}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] ${
                        r.during_class ? "bg-sky text-navy" : "bg-appbg text-muted"
                      }`}
                    >
                      {r.during_class ? `During class${r.class_context ? `: ${r.class_context}` : ""}` : "Outside class"}
                    </span>
                  </div>
                  <div className="text-xs text-muted">
                    {r.registration_number} · requested {r.created_at.slice(0, 16).replace("T", " ")}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => decide.mutate({ id: r.id, decision: "approve" })}>
                    Approve
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => decide.mutate({ id: r.id, decision: "reject" })}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No pending device requests" />
        )}
      </Card>
    </PortalLayout>
  );
}
