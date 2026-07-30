import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  Badge,
  BatchSelect,
  Button,
  Card,
  EmptyState,
  Input,
  ListSkeleton,
} from "../../design-system";
import { batchesApi } from "../batches/api";
import {
  assessmentsApi,
  type NewQuestion,
  type TestAttemptRow,
  type TestKind,
  type TestListItem,
} from "./api";

const KIND_LABEL: Record<TestKind, string> = {
  mcq: "MCQ (auto-graded)",
  file: "File upload (e.g. Excel)",
  colab: "Colab / notebook link",
};

/* ---------------- Faculty / admin: build & list ---------------- */

const blankQuestion = (): NewQuestion => ({
  text: "",
  choices: [
    { text: "", is_correct: true },
    { text: "", is_correct: false },
  ],
});

export function ManageTests() {
  const qc = useQueryClient();
  const batches = useQuery({ queryKey: ["batches"], queryFn: batchesApi.listBatches });
  const [batchId, setBatchId] = useState("");
  const tests = useQuery({
    queryKey: ["tests", batchId],
    queryFn: () => assessmentsApi.list(batchId || undefined),
  });

  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<TestKind>("mcq");
  const [instructions, setInstructions] = useState("");
  const [maxScore, setMaxScore] = useState(100);
  const [resourceUrl, setResourceUrl] = useState("");
  const [resourceFile, setResourceFile] = useState<File | null>(null);
  const [questions, setQuestions] = useState<NewQuestion[]>([blankQuestion()]);
  const [error, setError] = useState<string | null>(null);
  const [grading, setGrading] = useState<TestListItem | null>(null);

  const reset = () => {
    setTitle("");
    setKind("mcq");
    setInstructions("");
    setMaxScore(100);
    setResourceUrl("");
    setResourceFile(null);
    setQuestions([blankQuestion()]);
  };

  const create = useMutation({
    mutationFn: () =>
      assessmentsApi.create(
        {
          batch: batchId,
          title,
          kind,
          instructions,
          max_score: maxScore,
          resource_url: resourceUrl,
          questions: kind === "mcq" ? questions : [],
        },
        resourceFile,
      ),
    onSuccess: () => {
      reset();
      setError(null);
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
    onError: () =>
      setError(
        kind === "mcq"
          ? "Could not create test — every question needs text, 2+ choices, and a correct answer."
          : "Could not create test — check the title and score.",
      ),
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
    batchId &&
    title &&
    (kind !== "mcq" || questions.every((q) => q.text && q.choices.every((c) => c.text)));

  if (grading) {
    return <GradeAttempts test={grading} onBack={() => setGrading(null)} />;
  }

  return (
    <div className="grid gap-6">
      <Card>
        <BatchSelect
          id="tests-batch"
          value={batchId}
          onChange={setBatchId}
          batches={batches.data}
        />
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

          <div className="mb-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="test-kind" className="mb-1 block text-xs font-medium text-muted">
                Test type
              </label>
              <select
                id="test-kind"
                className="h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm"
                value={kind}
                onChange={(e) => setKind(e.target.value as TestKind)}
              >
                {(Object.keys(KIND_LABEL) as TestKind[]).map((k) => (
                  <option key={k} value={k}>
                    {KIND_LABEL[k]}
                  </option>
                ))}
              </select>
            </div>
            {kind !== "mcq" && (
              <div>
                <label htmlFor="test-max" className="mb-1 block text-xs font-medium text-muted">
                  Marks (out of)
                </label>
                <Input
                  id="test-max"
                  type="number"
                  min={1}
                  value={maxScore}
                  onChange={(e) => setMaxScore(Number(e.target.value) || 0)}
                />
              </div>
            )}
          </div>

          {kind === "mcq" ? (
            <>
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
              <div className="mb-2 flex items-center gap-3">
                <Button
                  variant="soft"
                  onClick={() => setQuestions((qs) => [...qs, blankQuestion()])}
                >
                  + Add question
                </Button>
              </div>
            </>
          ) : (
            <div className="mb-3">
              <label
                htmlFor="test-instructions"
                className="mb-1 block text-xs font-medium text-muted"
              >
                Instructions for students
              </label>
              <textarea
                id="test-instructions"
                className="min-h-24 w-full rounded-lg border border-brdr bg-surface p-2 text-sm"
                placeholder={
                  kind === "file"
                    ? "e.g. Download the dataset, complete the pivot tables, and upload your .xlsx."
                    : "e.g. Complete the notebook and paste your shared Colab link."
                }
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
              {kind === "file" && (
                <div className="mt-3">
                  <label htmlFor="test-resource" className="mb-1 block text-xs font-medium text-muted">
                    Starter sheet to hand out (optional — students download, fill, re-upload)
                  </label>
                  <input
                    id="test-resource"
                    type="file"
                    onChange={(e) => setResourceFile(e.target.files?.[0] ?? null)}
                    className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-sky file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-brand-strong"
                  />
                  {resourceFile && <p className="mt-1 text-xs text-muted">{resourceFile.name}</p>}
                </div>
              )}
              <div className="mt-3">
                <label htmlFor="test-resource-url" className="mb-1 block text-xs font-medium text-muted">
                  {kind === "colab" ? "Starter notebook link" : "Reference link"} (optional)
                </label>
                <Input
                  id="test-resource-url"
                  placeholder={
                    kind === "colab"
                      ? "https://colab.research.google.com/…"
                      : "https://…"
                  }
                  value={resourceUrl}
                  onChange={(e) => setResourceUrl(e.target.value)}
                />
              </div>
            </div>
          )}

          <Button onClick={() => create.mutate()} disabled={!canSubmit || create.isPending}>
            {create.isPending ? "Creating…" : "Create test"}
          </Button>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        </Card>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Tests</h2>
        {tests.data && tests.data.length > 0 ? (
          <div className="flex flex-col divide-y divide-brdr">
            {tests.data.map((t) => (
              <div key={t.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-ink">{t.title}</span>
                  <Badge tone={t.kind === "mcq" ? "neutral" : "info"}>{KIND_LABEL[t.kind]}</Badge>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted">
                    {t.kind === "mcq"
                      ? `${t.question_count} Qs · ${t.attempt_count} attempt(s)`
                      : `out of ${t.max_score} · ${t.attempt_count} submission(s)`}
                  </span>
                  {t.kind !== "mcq" && (
                    <Button variant="soft" onClick={() => setGrading(t)}>
                      Grade
                    </Button>
                  )}
                </div>
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

/* ---------------- Faculty: grade file/colab submissions ---------------- */

function GradeAttempts({ test, onBack }: { test: TestListItem; onBack: () => void }) {
  const qc = useQueryClient();
  const attempts = useQuery({
    queryKey: ["test-attempts", test.id],
    queryFn: () => assessmentsApi.attempts(test.id),
  });

  return (
    <div className="grid gap-4">
      <Button variant="ghost" className="w-fit" onClick={onBack}>
        ← Back to tests
      </Button>
      <h2 className="text-base font-medium text-ink">
        Grade: {test.title}{" "}
        <span className="text-sm font-normal text-muted">(out of {test.max_score})</span>
      </h2>
      {attempts.isLoading ? (
        <ListSkeleton items={3} />
      ) : attempts.data && attempts.data.length > 0 ? (
        <div className="grid gap-3">
          {attempts.data.map((a) => (
            <GradeRow
              key={a.id}
              attempt={a}
              onGraded={() => qc.invalidateQueries({ queryKey: ["test-attempts", test.id] })}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="No submissions yet" />
      )}
    </div>
  );
}

function GradeRow({ attempt, onGraded }: { attempt: TestAttemptRow; onGraded: () => void }) {
  const [score, setScore] = useState(attempt.graded ? attempt.score : 0);
  const [feedback, setFeedback] = useState(attempt.feedback);

  const grade = useMutation({
    mutationFn: () => assessmentsApi.gradeAttempt(attempt.id, { score, feedback }),
    onSuccess: onGraded,
  });

  return (
    <Card>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm">
          <span className="font-medium text-ink">{attempt.student_name}</span>{" "}
          <span className="text-muted">({attempt.registration_number})</span>
        </div>
        {attempt.graded ? (
          <Badge tone="success">Graded {attempt.score}/{attempt.total}</Badge>
        ) : (
          <Badge tone="warning">Awaiting grade</Badge>
        )}
      </div>
      <div className="mb-3 flex flex-wrap gap-3 text-sm">
        {attempt.file_url && (
          <a href={attempt.file_url} target="_blank" rel="noreferrer" className="text-brand-strong underline">
            Open submitted file ↗
          </a>
        )}
        {attempt.link && (
          <a href={attempt.link} target="_blank" rel="noreferrer" className="text-brand-strong underline">
            Open Colab link ↗
          </a>
        )}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-muted">Score (max {attempt.total})</label>
          <Input
            type="number"
            min={0}
            max={attempt.total}
            value={score}
            onChange={(e) => setScore(Number(e.target.value) || 0)}
            className="w-28"
          />
        </div>
        <Input
          placeholder="Feedback (optional)"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          className="min-w-48 flex-1"
        />
        <Button onClick={() => grade.mutate()} disabled={grade.isPending}>
          {grade.isPending ? "Saving…" : "Save grade"}
        </Button>
      </div>
    </Card>
  );
}

