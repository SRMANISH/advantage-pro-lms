import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input, SectionHeading, TableShell, THead } from "../../design-system";
import { api } from "../../lib/api";
import { PortalLayout } from "../portal/PortalLayout";

interface Channel {
  kind: string;
  adapter: string;
  dev_stub: boolean;
  editable: boolean;
  provider: string;
  config: Record<string, unknown>;
  secret_set: boolean;
}

export function ChannelsPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const channels = useQuery({
    queryKey: ["channels"],
    queryFn: async () =>
      (await api.get<{ channels: Channel[] }>("/settings/channels/")).data.channels,
  });

  const [form, setForm] = useState({ channel: "sms", to: "", message: "Test from Advantage Pro" });
  const test = useMutation({ mutationFn: () => api.post("/settings/channels/test/", form) });

  const editable = channels.data?.filter((c) => c.editable) ?? [];

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Notification channels"
        subtitle="Each channel runs behind a swappable adapter — console stubs in dev, real providers at deploy. Edit the third-party connection for each below."
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
                    <Badge tone="warning">Dev stub</Badge>
                  ) : (
                    <Badge tone="success">Live</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      </Card>

      <Card className="mb-6">
        <h2 className="mb-1 text-base font-medium text-ink">Third-party connections</h2>
        <p className="mb-4 text-sm text-muted">
          Credentials are stored server-side and used by the matching provider adapter. Secret
          values are write-only — we show whether one is set, never the value itself.
        </p>
        <div className="grid gap-4">
          {editable.map((c) => (
            <ConnectionCard
              key={c.kind}
              channel={c}
              onSaved={() => qc.invalidateQueries({ queryKey: ["channels"] })}
            />
          ))}
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
          <Button
            className="w-fit"
            onClick={() => test.mutate()}
            disabled={!form.to || test.isPending}
          >
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

// Which config keys each channel's adapter reads (the secret is separate, below).
const CONFIG_KEYS: Record<string, string> = {
  email:
    '{ "host": "smtp…", "port": 587, "username": "…", "use_tls": true, "from_email": "…" } · secret = password',
  sms: '{ "sender_id": "ADVPRO", "route": "4", "country": "91" } · secret = MSG91 auth key',
  whatsapp:
    '{ "phone_number_id": "…", "template_name": "", "template_lang": "en" } · secret = access token',
  storage: "provider-specific",
};

function ConnectionCard({ channel, onSaved }: { channel: Channel; onSaved: () => void }) {
  const [provider, setProvider] = useState(channel.provider);
  const [configText, setConfigText] = useState(JSON.stringify(channel.config ?? {}, null, 2));
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      let config: unknown = {};
      try {
        config = configText.trim() ? JSON.parse(configText) : {};
      } catch {
        throw new Error("Config must be valid JSON.");
      }
      await api.put("/settings/channels/", { channel: channel.kind, provider, config, secret });
    },
    onSuccess: () => {
      setSecret("");
      setError(null);
      onSaved();
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Could not save."),
  });

  return (
    <div className="rounded-xl border border-brdr p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold capitalize text-ink">{channel.kind}</span>
        {channel.secret_set ? (
          <Badge tone="success">Secret set</Badge>
        ) : (
          <Badge tone="neutral">No secret</Badge>
        )}
      </div>
      <div className="grid gap-3">
        <div>
          <label
            htmlFor={`prov-${channel.kind}`}
            className="mb-1 block text-xs font-medium text-muted"
          >
            Provider
          </label>
          <Input
            id={`prov-${channel.kind}`}
            placeholder="Example: smtp, msg91, whatsapp_cloud, s3"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          />
        </div>
        <div>
          <label
            htmlFor={`cfg-${channel.kind}`}
            className="mb-1 block text-xs font-medium text-muted"
          >
            Config (JSON) — keys: {CONFIG_KEYS[channel.kind] ?? "non-secret settings"}
          </label>
          <textarea
            id={`cfg-${channel.kind}`}
            className="min-h-24 w-full rounded-lg border border-brdr bg-surface p-2 font-mono text-xs"
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
          />
        </div>
        <div>
          <label
            htmlFor={`sec-${channel.kind}`}
            className="mb-1 block text-xs font-medium text-muted"
          >
            Secret / API key {channel.secret_set && "(leave blank to keep the current one)"}
          </label>
          <Input
            id={`sec-${channel.kind}`}
            type="password"
            autoComplete="new-password"
            placeholder={channel.secret_set ? "•••••••• (unchanged)" : "Enter API key / password"}
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save connection"}
          </Button>
          {save.isSuccess && <span className="text-sm text-success">✓ Saved</span>}
          {error && <span className="text-sm text-danger">{error}</span>}
        </div>
      </div>
    </div>
  );
}
