import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, Input, Select } from "../../design-system";
import { engagementApi, type NextPlanInput } from "./api";

// Institute links — override at build time via env without touching code.
const LINKEDIN_URL =
  (import.meta.env.VITE_LINKEDIN_URL as string | undefined) ??
  "https://www.linkedin.com/company/advantage-pro";
const GOOGLE_REVIEW_URL =
  (import.meta.env.VITE_GOOGLE_REVIEW_URL as string | undefined) ??
  "https://search.google.com/local/writereview?placeid=YOUR_PLACE_ID";

type Prompt = "linkedin" | "google" | "nextplan" | null;

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md">{children}</Card>
    </div>
  );
}

/** Post-login + course-end engagement prompts, shown one at a time for students. */
export function EngagementPrompts() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["engagement-me"], queryFn: engagementApi.me });
  // "Later" hides a prompt for this session only (no backend skip) so it returns next login.
  const [dismissed, setDismissed] = useState<Set<Prompt>>(new Set());
  const refresh = () => qc.invalidateQueries({ queryKey: ["engagement-me"] });

  const linkedin = useMutation({
    mutationFn: engagementApi.linkedinAction,
    onSuccess: refresh,
  });
  const google = useMutation({
    mutationFn: engagementApi.googleReviewAction,
    onSuccess: refresh,
  });
  const nextPlan = useMutation({
    mutationFn: (body: NextPlanInput) => engagementApi.submitNextPlan(body),
    onSuccess: refresh,
  });

  const [plan, setPlan] = useState<NextPlanInput>({
    planning_another_course: false,
    interested_course: "",
    expected_timing: "",
    goal: "",
    preferred_contact_time: "",
  });

  if (!me.data) return null;
  const d = me.data;

  let current: Prompt = null;
  if (d.linkedin.show) current = "linkedin";
  else if (d.google_review.show) current = "google";
  else if (d.next_plan.show) current = "nextplan";
  if (!current || dismissed.has(current)) return null;

  const later = () => setDismissed((prev) => new Set(prev).add(current));

  if (current === "linkedin") {
    return (
      <Overlay>
        <h2 className="mb-1 text-lg font-medium text-ink">Follow us on LinkedIn</h2>
        <p className="mb-4 text-sm text-muted">
          Following the Advantage Pro LinkedIn page is required to stay updated on results,
          openings and announcements. Open the page, follow us, then confirm below.
        </p>
        <div className="flex flex-wrap gap-2">
          <a href={LINKEDIN_URL} target="_blank" rel="noreferrer">
            <Button onClick={() => linkedin.mutate("opened")}>Open LinkedIn</Button>
          </a>
          <Button variant="soft" onClick={() => linkedin.mutate("confirmed")}>
            I&apos;ve followed — confirm
          </Button>
          <Button variant="ghost" onClick={later}>
            Later
          </Button>
        </div>
      </Overlay>
    );
  }

  if (current === "google") {
    return (
      <Overlay>
        <h2 className="mb-1 text-lg font-medium text-ink">Share a Google review</h2>
        <p className="mb-4 text-sm text-muted">
          You&apos;ve completed your course — a quick Google review of your experience helps other
          learners. Open the review page and submit, then confirm below.
        </p>
        <div className="flex flex-wrap gap-2">
          <a href={GOOGLE_REVIEW_URL} target="_blank" rel="noreferrer">
            <Button onClick={() => google.mutate("opened")}>Open review page</Button>
          </a>
          <Button variant="soft" onClick={() => google.mutate("submitted")}>
            I&apos;ve submitted it
          </Button>
          <Button variant="ghost" onClick={later}>
            Later
          </Button>
        </div>
      </Overlay>
    );
  }

  return (
    <Overlay>
      <h2 className="mb-1 text-lg font-medium text-ink">What&apos;s your next plan?</h2>
      <p className="mb-3 text-sm text-muted">
        Tell us what you&apos;d like to learn next so we can guide you. It takes a minute.
      </p>
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={plan.planning_another_course}
            onChange={(e) => setPlan({ ...plan, planning_another_course: e.target.checked })}
          />
          I&apos;m planning another course
        </label>
        <Input
          placeholder="Interested course (e.g. Data Science)"
          value={plan.interested_course}
          onChange={(e) => setPlan({ ...plan, interested_course: e.target.value })}
        />
        <Input
          placeholder="Expected timing (e.g. in 3 months)"
          value={plan.expected_timing}
          onChange={(e) => setPlan({ ...plan, expected_timing: e.target.value })}
        />
        <Select value={plan.goal} onChange={(e) => setPlan({ ...plan, goal: e.target.value })}>
          <option value="">Goal…</option>
          <option value="job_change">Job change</option>
          <option value="promotion">Promotion</option>
          <option value="upskilling">Upskilling</option>
          <option value="other">Other</option>
        </Select>
        <Input
          placeholder="Preferred contact time (e.g. evenings)"
          value={plan.preferred_contact_time}
          onChange={(e) => setPlan({ ...plan, preferred_contact_time: e.target.value })}
        />
      </div>
      <div className="mt-3 flex gap-2">
        <Button onClick={() => nextPlan.mutate(plan)} disabled={nextPlan.isPending}>
          {nextPlan.isPending ? "Submitting…" : "Submit"}
        </Button>
        <Button variant="ghost" onClick={later}>
          Later
        </Button>
      </div>
    </Overlay>
  );
}
