import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, EmptyState, SectionHeading } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { forumApi } from "./api";

export function MonitorPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const monitor = useQuery({ queryKey: ["forum-monitor"], queryFn: forumApi.monitor });
  const [reminded, setReminded] = useState<Set<string>>(new Set());
  const remind = useMutation({
    mutationFn: (id: string) => forumApi.remind(id),
    onSuccess: (_d, id) => {
      setReminded((prev) => new Set(prev).add(id));
      qc.invalidateQueries({ queryKey: ["forum-monitor"] });
    },
  });

  const window = monitor.data?.window_hours ?? 3;

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Doubt monitor"
        subtitle={`Unanswered doubts — anything waiting over ${window}h is overdue.`}
      />

      <Card>
        {monitor.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : monitor.data && monitor.data.threads.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {monitor.data.threads.map((t) => (
              <div key={t.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-ink">
                    {t.title}
                    {t.overdue && <Badge tone="danger">overdue</Badge>}
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
      </Card>
    </PortalLayout>
  );
}
