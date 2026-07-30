import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
  SectionHeading,
} from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { certificationApi, type CertRow } from "./api";

export function CertificatePage({ role }: { role: RoleDef }) {
  const rows = useQuery({ queryKey: ["certification-me"], queryFn: certificationApi.me });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Certification"
        subtitle="Enter your Certificate ID after a course ends to complete certification and stop reminders."
      />

      {rows.isLoading ? (
        <ListSkeleton items={2} />
      ) : rows.data && rows.data.length > 0 ? (
        <div className="grid gap-4">
          {rows.data.map((r) => (
            <CertCard key={r.enrollment} row={r} />
          ))}
        </div>
      ) : (
        <EmptyState title="No completed courses yet" />
      )}
    </PortalLayout>
  );
}

function CertCard({ row }: { row: CertRow }) {
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const submit = useMutation({
    mutationFn: () => certificationApi.submit(row.enrollment, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["certification-me"] }),
  });

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-medium text-ink">{row.batch_name}</h2>
        {row.certified ? (
          <Badge tone="success">Certified</Badge>
        ) : (
          <Badge tone="warning">Pending</Badge>
        )}
      </div>
      {row.certified ? (
        <p className="text-sm text-ink">Certificate ID: {row.certificate_id}</p>
      ) : (
        <div className="flex gap-2">
          <Input
            placeholder="Enter your Certificate ID"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button onClick={() => submit.mutate()} disabled={!value || submit.isPending}>
            {submit.isPending ? "Saving…" : "Submit"}
          </Button>
        </div>
      )}
    </Card>
  );
}
