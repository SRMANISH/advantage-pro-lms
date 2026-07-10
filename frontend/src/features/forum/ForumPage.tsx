import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Paperclip } from "lucide-react";
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
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { forumApi, type Attachment, type ThreadStatus } from "./api";

// Only Faculty and Tech Support may respond to doubts (students ask; MIS has no forum).
const RESPONDERS = new Set(["faculty", "tech_support"]);

function StatusBadge({ status }: { status: ThreadStatus }) {
  return <Badge>{status}</Badge>;
}

function Attachments({ items }: { items: Attachment[] }) {
  if (!items?.length) return null;
  const images = items.filter((a) => a.content_type?.startsWith("image/"));
  const files = items.filter((a) => !a.content_type?.startsWith("image/"));
  return (
    <div className="mt-1.5 flex flex-col gap-2">
      {/* Image attachments render inline so a screenshot of the doubt is visible in place. */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((a) => (
            <a key={a.id} href={a.download_url} target="_blank" rel="noreferrer" className="block">
              <img
                src={a.download_url}
                alt={a.filename}
                loading="lazy"
                className="max-h-56 rounded-lg border border-brdr object-contain"
              />
            </a>
          ))}
        </div>
      )}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((a) => (
            <a
              key={a.id}
              href={a.download_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky px-2.5 py-1 text-xs font-medium text-brand-strong hover:underline"
            >
              <Paperclip size={13} /> {a.filename}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export function ForumPage({ role }: { role: RoleDef }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <PortalLayout role={role}>
      <SectionHeading title="Doubt forum" subtitle="Ask, answer and resolve batch doubts." />
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
  const [file, setFile] = useState<File | null>(null);
  const create = useMutation({
    mutationFn: () => forumApi.create({ ...form, file }),
    onSuccess: () => {
      setForm({ batch: "", title: "", body: "" });
      setFile(null);
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
            <label className="text-xs text-muted">
              Attach a screenshot or file (optional)
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.gif,.pdf,.txt,.zip,.docx,.xlsx"
                className="mt-1 block w-full text-sm text-ink file:mr-3 file:rounded-lg file:border-0 file:bg-sky file:px-3 file:py-1.5 file:text-brand-strong"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
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
                    {t.status === "open" && t.hours_waiting > 0 && ` · waiting ${t.hours_waiting}h`}
                  </div>
                </div>
                <span className="flex items-center gap-1.5">
                  {t.overdue && <Badge tone="danger">overdue</Badge>}
                  <StatusBadge status={t.status} />
                </span>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState title="No doubts found" hint="Post a doubt to start a thread." />
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
  const [replyFile, setReplyFile] = useState<File | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["thread", id] });
    qc.invalidateQueries({ queryKey: ["threads"] });
  };
  const reply = useMutation({
    mutationFn: () => forumApi.reply(id, body, replyFile),
    onSuccess: () => {
      setBody("");
      setReplyFile(null);
      invalidate();
    },
  });
  const resolve = useMutation({ mutationFn: () => forumApi.resolve(id), onSuccess: invalidate });
  const escalate = useMutation({ mutationFn: () => forumApi.escalate(id), onSuccess: invalidate });

  if (thread.isLoading || !thread.data) return <ListSkeleton items={2} />;
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
      <Attachments items={t.attachments} />
      <p className="mb-4 mt-1 text-xs text-muted">
        {t.author_name} · {t.batch_code}
      </p>

      <div className="flex flex-col divide-y divide-brdr border-t border-brdr">
        {t.replies.map((r) => (
          <div key={r.id} className="py-2">
            <div className="text-sm text-ink">{r.body}</div>
            <Attachments items={r.attachments} />
            <div className="text-xs text-muted">{r.author_name}</div>
          </div>
        ))}
      </div>

      {RESPONDERS.has(user?.role ?? "") ? (
        <div className="mt-3 flex flex-col gap-2">
          <textarea
            className="min-h-16 rounded-lg border border-brdr bg-surface p-2 text-sm"
            placeholder="Write a reply…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <label className="text-xs text-muted">
            Attach a file (optional)
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.gif,.pdf,.txt,.zip,.docx,.xlsx"
              className="mt-1 block w-full text-sm text-ink file:mr-3 file:rounded-lg file:border-0 file:bg-sky file:px-3 file:py-1.5 file:text-brand-strong"
              onChange={(e) => setReplyFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <Button className="w-fit" onClick={() => reply.mutate()} disabled={!body || reply.isPending}>
            {reply.isPending ? "Replying…" : "Reply"}
          </Button>
        </div>
      ) : (
        <p className="mt-3 rounded-lg bg-sky/50 px-3 py-2 text-xs text-navy">
          Your faculty or tech support will reply here — replies arrive as notifications.
        </p>
      )}
    </Card>
  );
}
