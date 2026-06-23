import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Button, Card } from "../../design-system";
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
      <h1 className="mb-1 text-xl font-medium text-ink">Doubt monitor</h1>
      <p className="mb-4 text-sm text-muted">
        Unanswered doubts. Anything waiting longer than {window}h is overdue — nudge the faculty.
      </p>

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
                    {t.overdue && (
                      <span className="rounded-full bg-[color:var(--color-bg-danger,#FCEBEB)] px-2 py-0.5 text-xs text-red-600">
                        overdue
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-muted">
                    {t.batch_code} · {t.author_name} · waiting {t.hours_waiting}h
                  </div>
                </div>
                {reminded.has(t.id) ? (
                  <span className="text-xs text-[color:var(--color-text-success,#1E8E5A)]">
                    Reminded ✓
                  </span>
                ) : (
                  <Button variant="soft" onClick={() => remind.mutate(t.id)}>
                    Remind faculty
                  </Button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No unanswered doubts.</p>
        )}
      </Card>
    </PortalLayout>
  );
}
