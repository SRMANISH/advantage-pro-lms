import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input, SectionHeading, TableShell, THead } from "../../design-system";
import { api } from "../../lib/api";
import { PortalLayout } from "../portal/PortalLayout";

interface Channel {
  kind: string;
  adapter: string;
  dev_stub: boolean;
}

export function ChannelsPage({ role }: { role: RoleDef }) {
  const channels = useQuery({
    queryKey: ["channels"],
    queryFn: async () => (await api.get<{ channels: Channel[] }>("/settings/channels/")).data.channels,
  });

  const [form, setForm] = useState({ channel: "sms", to: "", message: "Test from Advantage Pro" });
  const test = useMutation({
    mutationFn: () => api.post("/settings/channels/test/", form),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Notification channels"
        subtitle="Each channel runs behind a swappable adapter — console stubs in dev, real providers at deploy."
      />

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">Configured providers</h2>
        <TableShell>
          <THead>
            <tr>
              <th className="px-3 py-2">Channel</th>
              <th className="px-3 py-2">Adapter</th>
              <th className="px-3 py-2">Mode</th>
            </tr>
          </THead>
          <tbody>
            {channels.data?.map((c) => (
              <tr key={c.kind} className="border-t border-brdr">
                <td className="px-3 py-2 font-medium text-ink">{c.kind}</td>
                <td className="px-3 py-2 font-mono text-xs text-muted">{c.adapter}</td>
                <td className="px-3 py-2">
                  {c.dev_stub ? (
                    <Badge tone="warning">dev stub</Badge>
                  ) : (
                    <Badge tone="success">live</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Send a test message</h2>
        <div className="flex flex-col gap-2">
          <select
            className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
            value={form.channel}
            onChange={(e) => setForm({ ...form, channel: e.target.value })}
          >
            <option value="email">Email</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
          <Input
            placeholder="To (email or phone)"
            value={form.to}
            onChange={(e) => setForm({ ...form, to: e.target.value })}
          />
          <Input
            placeholder="Message"
            value={form.message}
            onChange={(e) => setForm({ ...form, message: e.target.value })}
          />
          <Button className="w-fit" onClick={() => test.mutate()} disabled={!form.to || test.isPending}>
            {test.isPending ? "Sending…" : "Send test"}
          </Button>
          {test.isSuccess && (
            <p className="text-sm text-success">
              ✓ Sent via the {form.channel} adapter (logged to the server console in dev).
            </p>
          )}
        </div>
      </Card>
    </PortalLayout>
  );
}
