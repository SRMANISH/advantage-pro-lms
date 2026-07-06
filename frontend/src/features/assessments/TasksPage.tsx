import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  FileUpload,
  Input,
  ListSkeleton,
  SectionHeading,
  cn,
  useToast,
} from "../../design-system";
import { useAuth } from "../auth/auth";
import { batchesApi } from "../batches/api";
import { PortalLayout } from "../portal/PortalLayout";
import { tasksApi, type Submission, type TaskItem } from "./tasksApi";

export function TasksPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <SectionHeading title="Tasks" subtitle="Assignments with deadlines, submissions and grading." />
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

  const [form, setForm] = useState<{
    title: string;
    description: string;
    deadline: string;
    deadline_type: "daily" | "weekly" | "custom";
  }>({ title: "", description: "", deadline: "", deadline_type: "custom" });
  const create = useMutation({
    mutationFn: () =>
      tasksApi.create({
        batch: batchId,
        title: form.title,
        description: form.description,
        deadline: form.deadline || undefined,
        deadline_type: form.deadline_type,
      }),
    onSuccess: () => {
      setForm({ title: "", description: "", deadline: "", deadline_type: "custom" });
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
          <div className="mb-3 grid gap-2 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-muted">Deadline type</label>
              <select
                className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
                value={form.deadline_type}
                onChange={(e) =>
                  setForm({ ...form, deadline_type: e.target.value as typeof form.deadline_type })
                }
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="custom">Custom (5+ days)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted">Deadline (optional)</label>
              <Input
                type="datetime-local"
                value={form.deadline}
                onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              />
            </div>
          </div>
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
          <EmptyState title="No tasks yet" />
        )}
      </Card>
    </div>
  );
}

function TaskGrading({ task }: { task: TaskItem }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [toGradeOnly, setToGradeOnly] = useState(false);
  const subs = useQuery({
    queryKey: ["submissions", task.id],
    queryFn: () => tasksApi.submissions(task.id),
    enabled: open,
  });

  const all = subs.data ?? [];
  const ungraded = all.filter((s) => s.score == null);
  const visible = toGradeOnly ? ungraded : all;

  return (
    <div className="rounded-lg border border-brdr p-3">
      <button className="flex w-full items-center justify-between" onClick={() => setOpen((o) => !o)}>
        <span className="text-sm font-medium text-ink">{task.title}</span>
        <span className="text-xs text-muted">{task.submission_count} submission(s)</span>
      </button>
      {open && (
        <div className="mt-3 flex flex-col gap-3">
          {all.length > 0 && (
            <label className="flex w-fit cursor-pointer items-center gap-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={toGradeOnly}
                onChange={(e) => setToGradeOnly(e.target.checked)}
              />
              To grade only ({ungraded.length})
            </label>
          )}
          {visible.length > 0 ? (
            visible.map((s) => (
              <GradeRow key={s.id} submission={s} onGraded={() => qc.invalidateQueries({ queryKey: ["submissions", task.id] })} />
            ))
          ) : (
            <EmptyState title={toGradeOnly ? "Everything is graded 🎉" : "No submissions yet"} />
          )}
        </div>
      )}
    </div>
  );
}

function GradeRow({ submission, onGraded }: { submission: Submission; onGraded: () => void }) {
  const toast = useToast();
  const [score, setScore] = useState(submission.score?.toString() ?? "");
  const [feedback, setFeedback] = useState(submission.feedback);
  const grade = useMutation({
    mutationFn: () => tasksApi.grade(submission.id, { score: Number(score), feedback }),
    onSuccess: () => {
      onGraded();
      toast.show("Submission graded — student notified.", "success");
    },
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
        <ListSkeleton items={3} />
      ) : tasks.data && tasks.data.length > 0 ? (
        tasks.data.map((t) => <StudentTaskCard key={t.id} task={t} />)
      ) : (
        <Card>
          <EmptyState title="No tasks yet" />
        </Card>
      )}
    </div>
  );
}

// Assignment-card status: drives the left rail colour + badge.
const TASK_STATUS = {
  graded: { rail: "border-l-success", badge: "success" as const, label: "Graded" },
  submitted: { rail: "border-l-brand", badge: "info" as const, label: "Submitted" },
  late: { rail: "border-l-warning", badge: "warning" as const, label: "Submitted late" },
  overdue: { rail: "border-l-danger", badge: "danger" as const, label: "Overdue" },
  pending: { rail: "border-l-brdr", badge: "neutral" as const, label: "Pending" },
};

function StudentTaskCard({ task }: { task: TaskItem }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const submit = useMutation({
    mutationFn: () => tasksApi.submit(task.id, { text, file }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      toast.show("Task submitted.", "success");
    },
  });

  const mine = task.my_submission;
  const statusKey = mine
    ? mine.score != null
      ? "graded"
      : mine.is_late
        ? "late"
        : "submitted"
    : task.is_overdue
      ? "overdue"
      : "pending";
  const status = TASK_STATUS[statusKey];

  return (
    <Card className={cn("border-l-4", status.rail)}>
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-ink">{task.title}</h2>
        <div className="flex items-center gap-2">
          {task.deadline && (
            <span className="text-xs text-muted">due {task.deadline.slice(0, 10)}</span>
          )}
          <Badge tone={status.badge}>{status.label}</Badge>
        </div>
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
          <FileUpload
            file={file}
            onFile={setFile}
            accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.zip"
            hint="Attach your work (optional) — PDF, docs or images"
          />
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
