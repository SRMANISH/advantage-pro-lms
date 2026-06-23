import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input } from "../../design-system";
import { useAuth } from "../auth/auth";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { tasksApi, type Submission, type TaskItem } from "./tasksApi";

export function TasksPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <h1 className="mb-4 text-xl font-medium text-ink">Tasks</h1>
      {user?.role === "student" ? <StudentTasks /> : <ManageTasks />}
    </PortalLayout>
  );
}

/* ---------------- Faculty / admin ---------------- */

function ManageTasks() {
  const qc = useQueryClient();
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const [batchId, setBatchId] = useState("");
  const tasks = useQuery({
    queryKey: ["tasks", batchId],
    queryFn: () => tasksApi.list(batchId || undefined),
  });

  const [form, setForm] = useState({ title: "", description: "", deadline: "" });
  const create = useMutation({
    mutationFn: () =>
      tasksApi.create({
        batch: batchId,
        title: form.title,
        description: form.description,
        deadline: form.deadline || undefined,
      }),
    onSuccess: () => {
      setForm({ title: "", description: "", deadline: "" });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return (
    <div className="grid gap-6">
      <Card>
        <label className="mb-1 block text-sm text-muted">Batch</label>
        <select
          className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
          value={batchId}
          onChange={(e) => setBatchId(e.target.value)}
        >
          <option value="">Select a batch…</option>
          {batches.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.code} — {b.name}
            </option>
          ))}
        </select>
      </Card>

      {batchId && (
        <Card>
          <h2 className="mb-3 text-base font-medium text-ink">New task</h2>
          <Input
            className="mb-2"
            placeholder="Title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <Input
            className="mb-2"
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <label className="mb-1 block text-xs text-muted">Deadline (optional)</label>
          <Input
            type="datetime-local"
            className="mb-3"
            value={form.deadline}
            onChange={(e) => setForm({ ...form, deadline: e.target.value })}
          />
          <Button onClick={() => create.mutate()} disabled={!form.title || create.isPending}>
            {create.isPending ? "Creating…" : "Create task"}
          </Button>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Tasks</h2>
        {tasks.data && tasks.data.length > 0 ? (
          <div className="flex flex-col gap-2">
            {tasks.data.map((t) => (
              <TaskGrading key={t.id} task={t} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">No tasks yet.</p>
        )}
      </Card>
    </div>
  );
}

function TaskGrading({ task }: { task: TaskItem }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const subs = useQuery({
    queryKey: ["submissions", task.id],
    queryFn: () => tasksApi.submissions(task.id),
    enabled: open,
  });

  return (
    <div className="rounded-lg border border-brdr p-3">
      <button className="flex w-full items-center justify-between" onClick={() => setOpen((o) => !o)}>
        <span className="text-sm font-medium text-ink">{task.title}</span>
        <span className="text-xs text-muted">{task.submission_count} submission(s)</span>
      </button>
      {open && (
        <div className="mt-3 flex flex-col gap-3">
          {subs.data && subs.data.length > 0 ? (
            subs.data.map((s) => (
              <GradeRow key={s.id} submission={s} onGraded={() => qc.invalidateQueries({ queryKey: ["submissions", task.id] })} />
            ))
          ) : (
            <p className="text-sm text-muted">No submissions yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function GradeRow({ submission, onGraded }: { submission: Submission; onGraded: () => void }) {
  const [score, setScore] = useState(submission.score?.toString() ?? "");
  const [feedback, setFeedback] = useState(submission.feedback);
  const grade = useMutation({
    mutationFn: () => tasksApi.grade(submission.id, { score: Number(score), feedback }),
    onSuccess: onGraded,
  });

  return (
    <div className="rounded-lg bg-sky p-3">
      <div className="mb-1 flex items-center gap-2 text-sm">
        <span className="font-medium text-ink">{submission.student_name}</span>
        {submission.is_late && <Badge>late</Badge>}
      </div>
      {submission.text && <p className="mb-1 text-sm text-ink">{submission.text}</p>}
      {submission.file_url && (
        <a href={submission.file_url} target="_blank" rel="noreferrer" className="text-sm text-brand-strong underline">
          View file
        </a>
      )}
      <div className="mt-2 flex items-center gap-2">
        <Input
          className="w-20"
          placeholder="Score"
          value={score}
          onChange={(e) => setScore(e.target.value)}
        />
        <Input placeholder="Feedback" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
        <Button onClick={() => grade.mutate()} disabled={!score || grade.isPending}>
          Grade
        </Button>
      </div>
    </div>
  );
}

/* ---------------- Student ---------------- */

function StudentTasks() {
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: () => tasksApi.list() });

  return (
    <div className="grid gap-4">
      {tasks.isLoading ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : tasks.data && tasks.data.length > 0 ? (
        tasks.data.map((t) => <StudentTaskCard key={t.id} task={t} />)
      ) : (
        <Card>
          <p className="text-sm text-muted">No tasks yet.</p>
        </Card>
      )}
    </div>
  );
}

function StudentTaskCard({ task }: { task: TaskItem }) {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const submit = useMutation({
    mutationFn: () => tasksApi.submit(task.id, { text, file }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const mine = task.my_submission;

  return (
    <Card>
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-base font-medium text-ink">{task.title}</h2>
        {task.deadline && (
          <Badge>{task.is_overdue ? "overdue" : `due ${task.deadline.slice(0, 10)}`}</Badge>
        )}
      </div>
      {task.description && <p className="mb-2 text-sm text-muted">{task.description}</p>}

      {mine ? (
        <div className="rounded-lg bg-sky p-3 text-sm">
          <span className="font-medium text-navy">Submitted</span>
          {mine.is_late && <Badge className="ml-2">late</Badge>}
          {mine.score != null ? (
            <p className="mt-1 text-ink">
              Score: {mine.score}
              {mine.feedback && ` · ${mine.feedback}`}
            </p>
          ) : (
            <p className="mt-1 text-muted">Awaiting grading.</p>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <textarea
            className="min-h-20 rounded-lg border border-brdr bg-surface p-2 text-sm"
            placeholder="Type your answer (or attach a file)…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
          <Button
            className="w-fit"
            onClick={() => submit.mutate()}
            disabled={(!text && !file) || submit.isPending}
          >
            {submit.isPending ? "Submitting…" : "Submit"}
          </Button>
        </div>
      )}
    </Card>
  );
}
