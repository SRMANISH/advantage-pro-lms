import { useQuery } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { Card, EmptyState, SectionHeading } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { activityApi } from "./api";

const prettyAction = (a: string) => a.replace(/_/g, " ");

export function ActivityPage({ role }: { role: RoleDef }) {
  const rows = useQuery({ queryKey: ["activity"], queryFn: activityApi.list });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Activity"
        subtitle={`Recent actions${role.value === "faculty" ? " for your batches" : " across the platform"}.`}
      />
      <Card>
        {rows.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : rows.data && rows.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {rows.data.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <span className="font-medium capitalize text-ink">{prettyAction(r.action)}</span>
                  {r.target_type && <span className="text-muted"> · {r.target_type}</span>}
                </div>
                <div className="shrink-0 text-xs text-muted">
                  {r.actor_name} · {r.created_at.slice(0, 16).replace("T", " ")}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No activity yet" />
        )}
      </Card>
    </PortalLayout>
  );
}
