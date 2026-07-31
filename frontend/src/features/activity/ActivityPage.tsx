import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  Paginator,
  QueryError,
  SectionHeading,
} from "../../design-system";
import { useServerTable } from "../../lib/useServerTable";
import { PortalLayout } from "../portal/PortalLayout";
import { activityApi, type ActivityRow } from "./api";

const prettyAction = (a: string) => a.replace(/_/g, " ");

export function ActivityPage({ role }: { role: RoleDef }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  // The audit log grows without bound and is the one screen that reads it, so it has to
  // page rather than fetch a fixed slice. Changing either date resets to page 1.
  const rows = useServerTable<ActivityRow>({
    key: ["activity"],
    params: { from: from || undefined, to: to || undefined },
    fetcher: (p) => activityApi.list(p),
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
          <Input
            id="activity-from"
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="h-9 w-auto"
          />
          <label className="text-muted" htmlFor="activity-to">
            To
          </label>
          <Input
            id="activity-to"
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="h-9 w-auto"
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
        ) : rows.isError ? (
          <QueryError onRetry={() => rows.refetch()} />
        ) : rows.rows.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {rows.rows.map((r) => (
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
        <Paginator
          page={rows.page}
          pageCount={rows.pageCount}
          onPage={rows.setPage}
          total={rows.total}
        />
      </Card>
    </PortalLayout>
  );
}
