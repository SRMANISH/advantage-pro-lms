import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Card, EmptyState, ListSkeleton, SectionHeading } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { activityApi } from "./api";

const prettyAction = (a: string) => a.replace(/_/g, " ");

export function ActivityPage({ role }: { role: RoleDef }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const rows = useQuery({
    queryKey: ["activity", from, to],
    queryFn: () => activityApi.list(from || undefined, to || undefined),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Activity"
        subtitle={`Recent actions${role.value === "faculty" ? " for your batches" : " across the platform"}.`}
      />
      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <label className="text-muted" htmlFor="activity-from">
            From
          </label>
          <input
            id="activity-from"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="h-9 rounded-lg border border-brdr bg-surface px-2 text-sm"
          />
          <label className="text-muted" htmlFor="activity-to">
            To
          </label>
          <input
            id="activity-to"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="h-9 rounded-lg border border-brdr bg-surface px-2 text-sm"
          />
          {(from || to) && (
            <button
              className="text-xs text-brand-strong underline"
              onClick={() => {
                setFrom("");
                setTo("");
              }}
            >
              Clear
            </button>
          )}
        </div>
        {rows.isLoading ? (
          <ListSkeleton items={4} />
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
          <EmptyState title="No activity in this window" />
        )}
      </Card>
    </PortalLayout>
  );
}
