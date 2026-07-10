import { useQuery } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { Badge, Card, EmptyState, ListSkeleton, SectionHeading } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { feedbackApi } from "./api";

/** Super Admin's private feedback inbox (req 20). No other role can reach this. */
export function FeedbackInboxPage({ role }: { role: RoleDef }) {
  const rows = useQuery({ queryKey: ["feedback-inbox"], queryFn: feedbackApi.inbox });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Feedback to management"
        subtitle="Private messages from students. Only you can see these."
      />
      {rows.isLoading ? (
        <ListSkeleton items={4} />
      ) : rows.data && rows.data.length > 0 ? (
        <div className="grid gap-3">
          {rows.data.map((f) => (
            <Card key={f.id}>
              <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">{f.subject}</h3>
                <span className="text-xs text-muted">
                  {new Date(f.created_at).toLocaleString([], {
                    day: "2-digit",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <div className="mb-2 flex flex-wrap gap-1.5 text-xs">
                <Badge>{f.student_name}</Badge>
                {f.registration_number && <Badge tone="info">{f.registration_number}</Badge>}
                {f.batch_code && <Badge tone="info">{f.batch_code}</Badge>}
                {f.course_name && <span className="text-muted">{f.course_name}</span>}
              </div>
              <p className="whitespace-pre-wrap text-sm text-ink">{f.message}</p>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="No feedback yet" />
      )}
    </PortalLayout>
  );
}
