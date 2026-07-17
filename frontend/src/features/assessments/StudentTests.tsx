import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, Input, ListSkeleton } from "../../design-system";
import { assessmentsApi, type Attempt, type TestDetail } from "./api";

/* ---------------- Student: list & take ---------------- */

export function StudentTests() {
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
            <div key={t.id} className="flex items-center justify-between gap-2 py-2">
              <div className="text-sm">
                <span className="font-medium text-ink">{t.title}</span>{" "}
                <Badge tone={t.is_open ? "success" : "neutral"}>
                  {t.is_open ? "open" : "closed"}
                </Badge>
              </div>
              {t.my_attempt ? (
                <StudentAttemptStatus attempt={t.my_attempt} />
              ) : t.is_open ? (
                <Button onClick={() => setActiveId(t.id)}>
                  {t.kind === "mcq" ? "Take" : "Submit"}
                </Button>
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

function StudentAttemptStatus({ attempt }: { attempt: Attempt }) {
  if (!attempt.graded) {
    return <span className="text-sm text-amber-600">Submitted · awaiting grade</span>;
  }
  return (
    <span className="text-sm text-brand-strong">
      Score: {attempt.score}/{attempt.total}
    </span>
  );
}

function TakeTest({ id, onDone }: { id: string; onDone: () => void }) {
  const qc = useQueryClient();
  const test = useQuery({ queryKey: ["test", id], queryFn: () => assessmentsApi.get(id) });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [file, setFile] = useState<File | null>(null);
  const [link, setLink] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submitMcq = useMutation({
    mutationFn: (t: TestDetail) =>
      assessmentsApi.submit(
        id,
        t.questions.map((q) => ({ question: q.id, choice: answers[q.id] })).filter((a) => a.choice),
      ),
    onSuccess: (r) => {
      setResult(`Your score: ${r.score}/${r.total}`);
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
  });

  const submitArtefact = useMutation({
    mutationFn: () => assessmentsApi.submitArtefact(id, { file, link }),
    onSuccess: () => {
      setResult("Submitted — your faculty will grade it soon.");
      qc.invalidateQueries({ queryKey: ["tests"] });
    },
    onError: () => setError("Could not submit — check your file or link and try again."),
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
          <p className="text-lg font-medium text-ink">{result}</p>
          <Button className="mt-3" onClick={onDone}>
            Done
          </Button>
        </div>
      ) : t.kind === "mcq" ? (
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
            onClick={() => submitMcq.mutate(t)}
            disabled={submitMcq.isPending || Object.keys(answers).length === 0}
          >
            {submitMcq.isPending ? "Submitting…" : "Submit test"}
          </Button>
        </>
      ) : (
        <>
          {t.instructions && (
            <p className="mb-3 whitespace-pre-wrap rounded-lg bg-sky/50 px-3 py-2 text-sm text-navy">
              {t.instructions}
            </p>
          )}
          {(t.resource_download_url || t.resource_url) && (
            <div className="mb-3 flex flex-wrap gap-2">
              {t.resource_download_url && (
                <a
                  href={t.resource_download_url}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-strong"
                >
                  ⬇ Download the sheet
                </a>
              )}
              {t.resource_url && (
                <a
                  href={t.resource_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-brdr px-3 py-1.5 text-xs font-semibold text-brand-strong hover:bg-sky"
                >
                  {t.kind === "colab" ? "Open the notebook ↗" : "Open reference ↗"}
                </a>
              )}
            </div>
          )}
          {t.kind === "file" ? (
            <div className="mb-3">
              <label htmlFor="take-file" className="mb-1 block text-xs font-medium text-muted">
                Upload your file (out of {t.max_score})
              </label>
              <input
                id="take-file"
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-sky file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-brand-strong"
              />
            </div>
          ) : (
            <div className="mb-3">
              <label htmlFor="take-link" className="mb-1 block text-xs font-medium text-muted">
                Your Colab / notebook link
              </label>
              <Input
                id="take-link"
                placeholder="https://colab.research.google.com/…"
                value={link}
                onChange={(e) => setLink(e.target.value)}
              />
            </div>
          )}
          <Button
            onClick={() => submitArtefact.mutate()}
            disabled={submitArtefact.isPending || (t.kind === "file" ? !file : !link)}
          >
            {submitArtefact.isPending ? "Submitting…" : "Submit"}
          </Button>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        </>
      )}
    </Card>
  );
}
