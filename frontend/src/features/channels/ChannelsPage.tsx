import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input } from "../../design-system";
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
      <h1 className="mb-1 text-xl font-medium text-ink">Notification channels</h1>
      <p className="mb-4 text-sm text-muted">
        Every channel runs behind a swappable adapter. In development these are local/console stubs;
        Hostinger email and the SMS/WhatsApp provider plug in here later with no code changes.
      </p>

      <Card className="mb-6">
        <h2 className="mb-3 text-base font-medium text-ink">Configured providers</h2>
        <div className="overflow-hidden rounded-lg border border-brdr">
          <table className="w-full text-sm">
            <thead className="bg-sky text-navy">
              <tr>
                <th className="px-3 py-2 text-left">Channel</th>
                <th className="px-3 py-2 text-left">Adapter</th>
                <th className="px-3 py-2 text-left">Mode</th>
              </tr>
            </thead>
            <tbody>
              {channels.data?.map((c) => (
                <tr key={c.kind} className="border-t border-brdr">
                  <td className="px-3 py-2 font-medium text-ink">{c.kind}</td>
                  <td className="px-3 py-2 font-mono text-xs text-muted">{c.adapter}</td>
                  <td className="px-3 py-2">
                    {c.dev_stub ? <Badge>dev stub</Badge> : <Badge>live</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
            <p className="text-sm text-[color:var(--color-text-success,#1E8E5A)]">
              ✓ Sent via the {form.channel} adapter (logged to the server console in dev).
            </p>
          )}
        </div>
      </Card>
    </PortalLayout>
  );
}
