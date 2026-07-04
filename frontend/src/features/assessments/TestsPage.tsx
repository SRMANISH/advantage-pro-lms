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
import { batchesApi } from "../batches/api";
import { useAuth } from "../auth/auth";
import { PortalLayout } from "../portal/PortalLayout";
import { assessmentsApi, type NewQuestion, type TestDetail } from "./api";

export function TestsPage({ role }: { role: RoleDef }) {
  const { user } = useAuth();
  return (
    <PortalLayout role={role}>
      <SectionHeading title="Tests" subtitle="Auto-graded MCQ tests." />
      {user?.role === "student" ? <StudentTests /> : <ManageTests />}
    </PortalLayout>
  );
}

/* ---------------- Faculty / admin: build & list ---------------- */

const blankQuestion = (): NewQuestion => ({
  text: "",
  choices: [
    { text: "", is_correct: true },
    { text: "", is_correct: false },
  ],
});

function ManageTests() {
  const qc = useQueryClient();
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const [batchId, setBatchId] = useState("");
  const tests = useQuery({
    queryKey: ["tests", batchId],
    queryFn: () => assessmentsApi.list(batchId || undefined),
  });

  const [title, setTitle] = useState("");
  const [questions, setQuestions] = useState<NewQuestion[]>([blankQuestion()]);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      assessmentsApi.create({ batch: batchId, title, questions }),
    onSuccess: () => {
      setTitle("");
      setQuestions([blankQuestion()]);
      setError(null);
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
    onError: () => setError("Could not create test — every question needs text, 2+ choices, and a correct answer."),
  });

  const setQ = (qi: number, patch: Partial<NewQuestion>) =>
    setQuestions((qs) => qs.map((q, i) => (i === qi ? { ...q, ...patch } : q)));
  const setChoiceText = (qi: number, ci: number, text: string) =>
    setQ(qi, {
      choices: questions[qi].choices.map((c, i) => (i === ci ? { ...c, text } : c)),
    });
  const setCorrect = (qi: number, ci: number) =>
    setQ(qi, {
      choices: questions[qi].choices.map((c, i) => ({ ...c, is_correct: i === ci })),
    });

  const canSubmit =
    batchId && title && questions.every((q) => q.text && q.choices.every((c) => c.text));

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
          <h2 className="mb-3 text-base font-medium text-ink">New test</h2>
          <Input
            className="mb-3"
            placeholder="Test title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          {questions.map((q, qi) => (
            <div key={qi} className="mb-3 rounded-lg border border-brdr p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-ink">Question {qi + 1}</span>
                {questions.length > 1 && (
                  <button
                    className="text-xs text-danger"
                    onClick={() => setQuestions((qs) => qs.filter((_, i) => i !== qi))}
                  >
                    Remove
                  </button>
                )}
              </div>
              <Input
                className="mb-2"
                placeholder="Question text"
                value={q.text}
                onChange={(e) => setQ(qi, { text: e.target.value })}
              />
              {q.choices.map((c, ci) => (
                <div key={ci} className="mb-2 flex items-center gap-2">
                  <input
                    type="radio"
                    name={`correct-${qi}`}
                    checked={c.is_correct}
                    onChange={() => setCorrect(qi, ci)}
                    title="Mark as correct"
                  />
                  <Input
                    placeholder={`Choice ${ci + 1}`}
                    value={c.text}
                    onChange={(e) => setChoiceText(qi, ci, e.target.value)}
                  />
                </div>
              ))}
              <button
                className="text-xs text-brand-strong underline"
                onClick={() =>
                  setQ(qi, { choices: [...q.choices, { text: "", is_correct: false }] })
                }
              >
                + Add choice
              </button>
            </div>
          ))}

          <div className="flex items-center gap-3">
            <Button variant="soft" onClick={() => setQuestions((qs) => [...qs, blankQuestion()])}>
              + Add question
            </Button>
            <Button onClick={() => create.mutate()} disabled={!canSubmit || create.isPending}>
              {create.isPending ? "Creating…" : "Create test"}
            </Button>
          </div>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        </Card>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Tests</h2>
        {tests.data && tests.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {tests.data.map((t) => (
              <div key={t.id} className="flex items-center justify-between py-2 text-sm">
                <span className="font-medium text-ink">{t.title}</span>
                <span className="text-muted">
                  {t.question_count} Qs · {t.attempt_count} attempt(s)
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No tests yet" />
        )}
      </Card>
    </div>
  );
}

/* ---------------- Student: list & take ---------------- */

function StudentTests() {
  const tests = useQuery({ queryKey: ["tests"], queryFn: () => assessmentsApi.list() });
  const [activeId, setActiveId] = useState<string | null>(null);

  if (activeId) {
    return <TakeTest id={activeId} onDone={() => setActiveId(null)} />;
  }

  return (
    <Card>
      <h2 className="mb-3 text-base font-medium text-ink">Your tests</h2>
      {tests.isLoading ? (
        <ListSkeleton items={3} />
      ) : tests.data && tests.data.length > 0 ? (
        <div className="flex flex-col divide-y divide-brdr">
          {tests.data.map((t) => (
            <div key={t.id} className="flex items-center justify-between py-2">
              <div className="text-sm">
                <span className="font-medium text-ink">{t.title}</span>{" "}
                <Badge tone={t.is_open ? "success" : "neutral"}>
                  {t.is_open ? "open" : "closed"}
                </Badge>
              </div>
              {t.my_attempt ? (
                <span className="text-sm text-brand-strong">
                  Score: {t.my_attempt.score}/{t.my_attempt.total}
                </span>
              ) : t.is_open ? (
                <Button onClick={() => setActiveId(t.id)}>Take</Button>
              ) : (
                <span className="text-sm text-muted">Not attempted</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">No tests yet.</p>
      )}
    </Card>
  );
}

function TakeTest({ id, onDone }: { id: string; onDone: () => void }) {
  const qc = useQueryClient();
  const test = useQuery({ queryKey: ["test", id], queryFn: () => assessmentsApi.get(id) });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<{ score: number; total: number } | null>(null);

  const submit = useMutation({
    mutationFn: (t: TestDetail) =>
      assessmentsApi.submit(
        id,
        t.questions.map((q) => ({ question: q.id, choice: answers[q.id] })).filter((a) => a.choice),
      ),
    onSuccess: (r) => {
      setResult(r);
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
  });

  if (test.isLoading || !test.data) return <ListSkeleton items={2} />;
  const t = test.data;

  return (
    <Card>
      <Button variant="ghost" className="mb-3" onClick={onDone}>
        ← Back
      </Button>
      <h2 className="mb-3 text-base font-medium text-ink">{t.title}</h2>

      {result ? (
        <div>
          <p className="text-lg font-medium text-ink">
            Your score: {result.score}/{result.total}
          </p>
          <Button className="mt-3" onClick={onDone}>
            Done
          </Button>
        </div>
      ) : (
        <>
          {t.questions.map((q, qi) => (
            <div key={q.id} className="mb-4">
              <p className="mb-2 text-sm font-medium text-ink">
                {qi + 1}. {q.text}
              </p>
              {q.choices.map((c) => (
                <label key={c.id} className="mb-1 flex items-center gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name={q.id}
                    checked={answers[q.id] === c.id}
                    onChange={() => setAnswers((a) => ({ ...a, [q.id]: c.id }))}
                  />
                  {c.text}
                </label>
              ))}
            </div>
          ))}
          <Button
            onClick={() => submit.mutate(t)}
            disabled={submit.isPending || Object.keys(answers).length === 0}
          >
            {submit.isPending ? "Submitting…" : "Submit test"}
          </Button>
        </>
      )}
    </Card>
  );
}
