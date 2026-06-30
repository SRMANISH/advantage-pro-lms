import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input } from "../../design-system";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { forumApi, type ThreadStatus } from "./api";

const RESPONDERS = new Set(["faculty", "tech_support", "mis"]);

function StatusBadge({ status }: { status: ThreadStatus }) {
  return <Badge>{status}</Badge>;
}

export function ForumPage({ role }: { role: RoleDef }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <PortalLayout role={role}>
      <h1 className="mb-4 text-xl font-medium text-ink">Doubt forum</h1>
      {selected ? (
        <ThreadView id={selected} onBack={() => setSelected(null)} />
      ) : (
        <ThreadList onOpen={setSelected} />
      )}
    </PortalLayout>
  );
}

function ThreadList({ onOpen }: { onOpen: (id: string) => void }) {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const threads = useQuery({ queryKey: ["threads", q], queryFn: () => forumApi.list(q || undefined) });
  const batches = useQuery({ queryKey: ["forum-batches"], queryFn: forumApi.batches });

  const [form, setForm] = useState({ batch: "", title: "", body: "" });
  const create = useMutation({
    mutationFn: () => forumApi.create(form),
    onSuccess: () => {
      setForm({ batch: "", title: "", body: "" });
      qc.invalidateQueries({ queryKey: ["threads"] });
    },
  });

  const canPost = (batches.data?.length ?? 0) > 0;

  return (
    <div className="grid gap-4">
      {canPost && (
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">Ask a doubt</h2>
          <div className="flex flex-col gap-2">
            <select
              className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
              value={form.batch}
              onChange={(e) => setForm({ ...form, batch: e.target.value })}
            >
              <option value="">Select batch…</option>
              {batches.data?.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.code} — {b.name}
                </option>
              ))}
            </select>
            <Input
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <textarea
              className="min-h-20 rounded-lg border border-brdr bg-surface p-2 text-sm"
              placeholder="Describe your doubt…"
              value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })}
            />
            <Button
              className="w-fit"
              onClick={() => create.mutate()}
              disabled={!form.batch || !form.title || !form.body || create.isPending}
            >
              {create.isPending ? "Posting…" : "Post doubt"}
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <Input
          className="mb-3"
          placeholder="Search doubts…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {threads.data && threads.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {threads.data.map((t) => (
              <button
                key={t.id}
                onClick={() => onOpen(t.id)}
                className="flex items-center justify-between py-3 text-left hover:bg-sky"
              >
                <div>
                  <div className="text-sm font-medium text-ink">{t.title}</div>
                  <div className="text-xs text-muted">
                    {t.batch_code} · {t.author_name} · {t.reply_count} repl{t.reply_count === 1 ? "y" : "ies"}
                  </div>
                </div>
                <StatusBadge status={t.status} />
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No doubts found.</p>
        )}
      </Card>
    </div>
  );
}

function ThreadView({ id, onBack }: { id: string; onBack: () => void }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const thread = useQuery({ queryKey: ["thread", id], queryFn: () => forumApi.get(id) });
  const [body, setBody] = useState("");

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["thread", id] });
    qc.invalidateQueries({ queryKey: ["threads"] });
  };
  const reply = useMutation({
    mutationFn: () => forumApi.reply(id, body),
    onSuccess: () => {
      setBody("");
      invalidate();
    },
  });
  const resolve = useMutation({ mutationFn: () => forumApi.resolve(id), onSuccess: invalidate });
  const escalate = useMutation({ mutationFn: () => forumApi.escalate(id), onSuccess: invalidate });

  if (thread.isLoading || !thread.data) return <p className="text-sm text-muted">Loading…</p>;
  const t = thread.data;
  const canEscalate = RESPONDERS.has(user?.role ?? "") && t.status !== "resolved" && t.status !== "escalated";

  return (
    <Card>
      <Button variant="ghost" className="mb-3" onClick={onBack}>
        ← Back
      </Button>
      <div className="mb-1 flex items-center justify-between gap-2">
        <h2 className="text-base font-medium text-ink">{t.title}</h2>
        <div className="flex items-center gap-2">
          <StatusBadge status={t.status} />
          {canEscalate && (
            <Button variant="ghost" onClick={() => escalate.mutate()}>
              Escalate
            </Button>
          )}
          {!t.resolved && (
            <Button variant="soft" onClick={() => resolve.mutate()}>
              Mark resolved
            </Button>
          )}
        </div>
      </div>
      <p className="mb-1 text-sm text-ink">{t.body}</p>
      <p className="mb-4 text-xs text-muted">
        {t.author_name} · {t.batch_code}
      </p>

      <div className="flex flex-col divide-y divide-brdr border-t border-brdr">
        {t.replies.map((r) => (
          <div key={r.id} className="py-2">
            <div className="text-sm text-ink">{r.body}</div>
            <div className="text-xs text-muted">{r.author_name}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex flex-col gap-2">
        <textarea
          className="min-h-16 rounded-lg border border-brdr bg-surface p-2 text-sm"
          placeholder="Write a reply…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <Button className="w-fit" onClick={() => reply.mutate()} disabled={!body || reply.isPending}>
          {reply.isPending ? "Replying…" : "Reply"}
        </Button>
      </div>
    </Card>
  );
}
