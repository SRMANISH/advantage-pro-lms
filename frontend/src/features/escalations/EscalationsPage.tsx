import { useMutation } from "@tanstack/react-query";

import type { RoleDef } from "../../app/roles";
import { Button, Card, SectionHeading } from "../../design-system";
import { api } from "../../lib/api";
import { certificationApi } from "../certification/api";
import { PortalLayout } from "../portal/PortalLayout";

interface RunResult {
  test_reminders: number;
  attendance_alerts: number;
}

export function EscalationsPage({ role }: { role: RoleDef }) {
  const run = useMutation({
    mutationFn: async (): Promise<RunResult> => (await api.post("/escalations/run/")).data,
  });
  const certRemind = useMutation({ mutationFn: () => certificationApi.remind() });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Escalations"
        subtitle="Incomplete-test reminders and the 50%-attendance rule. Runs on a schedule in production — trigger manually here."
      />

      <Card>
        <Button onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? "Running…" : "Run checks now"}
        </Button>
        {run.isSuccess && run.data && (
          <p className="mt-3 text-sm text-success">
            ✓ Sent {run.data.test_reminders} test reminder(s) and {run.data.attendance_alerts}{" "}
            attendance alert(s).
          </p>
        )}
      </Card>

      <Card className="mt-4">
        <h2 className="mb-1 text-base font-medium text-ink">Certificate reminders</h2>
        <p className="mb-3 text-sm text-muted">
          Remind students in completed batches who haven't entered their Certificate ID.
        </p>
        <Button variant="soft" onClick={() => certRemind.mutate()} disabled={certRemind.isPending}>
          {certRemind.isPending ? "Sending…" : "Send certificate reminders"}
        </Button>
        {certRemind.isSuccess && (
          <p className="mt-3 text-sm text-success">
            ✓ Sent {certRemind.data.reminded} certificate reminder(s).
          </p>
        )}
      </Card>
    </PortalLayout>
  );
}
