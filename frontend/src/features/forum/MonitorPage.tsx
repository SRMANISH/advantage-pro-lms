import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ListSkeleton,
  Paginator,
  QueryError,
  SectionHeading,
} from "../../design-system";
import { useServerTable } from "../../lib/useServerTable";
import { PortalLayout } from "../portal/PortalLayout";
import { forumApi, type MonitorResult, type MonitorThread } from "./api";

export function MonitorPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const monitor = useServerTable<MonitorThread, MonitorResult>({
    key: ["forum-monitor"],
    fetcher: (p) => forumApi.monitor(p),
  });
  const [reminded, setReminded] = useState<Set<string>>(new Set());
  const remind = useMutation({
    mutationFn: (id: string) => forumApi.remind(id),
    onSuccess: (_d, id) => {
      setReminded((prev) => new Set(prev).add(id));
      qc.invalidateQueries({ queryKey: ["forum-monitor"] });
    },
  });

  // Whole-dataset context, so it stays correct on page 2.
  const window = monitor.data?.window_hours ?? 3;

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Doubt monitor"
        subtitle={`Unanswered doubts — anything waiting over ${window}h is overdue.`}
      />

      <Card>
        {monitor.isLoading ? (
          <ListSkeleton items={4} />
        ) : monitor.isError ? (
          <QueryError onRetry={() => monitor.refetch()} />
        ) : monitor.rows.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {monitor.rows.map((t) => (
              <div key={t.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-ink">
                    {t.title}
                    {t.overdue && <Badge tone="danger">Overdue</Badge>}
                  </div>
                  <div className="text-xs text-muted">
                    {t.batch_code} · {t.author_name} · waiting {t.hours_waiting}h
                  </div>
                </div>
                {reminded.has(t.id) ? (
                  <span className="text-xs text-success">Reminded ✓</span>
                ) : (
                  <Button variant="soft" onClick={() => remind.mutate(t.id)}>
                    Remind faculty
                  </Button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No unanswered doubts" hint="Faculty are on top of it." />
        )}
        <Paginator
          page={monitor.page}
          pageCount={monitor.pageCount}
          onPage={monitor.setPage}
          total={monitor.total}
        />
      </Card>
    </PortalLayout>
  );
}
