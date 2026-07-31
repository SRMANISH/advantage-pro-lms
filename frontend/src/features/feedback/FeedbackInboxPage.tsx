import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Card,
  EmptyState,
  ListSkeleton,
  Paginator,
  QueryError,
  SectionHeading,
} from "../../design-system";
import { useServerTable } from "../../lib/useServerTable";
import { PortalLayout } from "../portal/PortalLayout";
import { feedbackApi, type FeedbackRow } from "./api";

/** Super Admin's private feedback inbox (req 20). No other role can reach this. */
export function FeedbackInboxPage({ role }: { role: RoleDef }) {
  const rows = useServerTable<FeedbackRow>({
    key: ["feedback-inbox"],
    fetcher: (p) => feedbackApi.inbox(p),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Feedback to management"
        subtitle="Private messages from students. Only you can see these."
      />
      {rows.isLoading ? (
        <ListSkeleton items={4} />
      ) : rows.isError ? (
        <QueryError onRetry={() => rows.refetch()} />
      ) : rows.rows.length > 0 ? (
        <div className="grid gap-3">
          {rows.rows.map((f) => (
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
      <Paginator
        page={rows.page}
        pageCount={rows.pageCount}
        onPage={rows.setPage}
        total={rows.total}
      />
    </PortalLayout>
  );
}
