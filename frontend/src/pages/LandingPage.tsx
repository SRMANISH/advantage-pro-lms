import { Link } from "react-router-dom";

import { ROLES } from "../app/roles";
import { Logo } from "../design-system";

const FEATURES = [
  {
    title: "Secure video & notes",
    body: "Class recordings stream in-app with a personalised watermark — no downloads.",
  },
  {
    title: "Tests, tasks & grading",
    body: "Auto-graded MCQ tests and faculty-graded tasks, tracked per student.",
  },
  {
    title: "Attendance & performance",
    body: "Auto-captured from videos, tests, tasks and live classes, with batch ranking.",
  },
  {
    title: "Doubts & live classes",
    body: "Per-batch doubt forum and scheduled live classes with reminders.",
  },
];

const STAFF = ROLES.filter((r) => r.value !== "student");

export function LandingPage() {
  return (
    <div className="min-h-screen bg-appbg">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-brdr bg-surface px-6 py-3">
        <Logo size={40} />
        <Link
          to="/login/student"
          className="rounded-lg bg-brand-strong px-4 py-2 text-sm font-medium text-white hover:bg-navy"
        >
          Sign in
        </Link>
      </header>

      {/* Hero */}
      <section className="bg-sky">
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-6 py-16 text-center">
          <Logo size={120} />
          <h1 className="text-3xl font-medium text-navy sm:text-4xl">Advantage Pro LMS</h1>
          <p className="max-w-2xl text-base text-ink">
            One private platform for our batches — enrolment, class videos, tests, tasks,
            attendance, doubts and live classes, all in one place.
          </p>
          <p className="text-sm text-muted">Vectra Technosoft · Networking with success · since 1998</p>
          <div className="mt-2 flex flex-wrap justify-center gap-3">
            <Link
              to="/login/student"
              className="rounded-lg bg-brand-strong px-5 py-2.5 text-sm font-medium text-white hover:bg-navy"
            >
              Student sign in
            </Link>
            <Link
              to="/login/faculty"
              className="rounded-lg border border-brdr bg-surface px-5 py-2.5 text-sm font-medium text-navy hover:bg-sky"
            >
              Faculty sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-6 py-14">
        <h2 className="mb-6 text-center text-xl font-medium text-ink">What's inside</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-brdr bg-surface p-5">
              <h3 className="mb-1 text-base font-medium text-brand-strong">{f.title}</h3>
              <p className="text-sm text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Portals */}
      <section className="mx-auto max-w-5xl px-6 pb-16">
        <h2 className="mb-1 text-center text-xl font-medium text-ink">Choose your portal</h2>
        <p className="mb-6 text-center text-sm text-muted">
          Each role signs in through its own secure page.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {STAFF.map((r) => (
            <Link
              key={r.slug}
              to={`/login/${r.slug}`}
              className="rounded-xl border border-brdr bg-surface px-4 py-4 transition hover:bg-sky"
            >
              <div className="text-sm font-medium text-navy">{r.label}</div>
              <div className="text-xs text-muted">{r.tagline}</div>
            </Link>
          ))}
        </div>
      </section>

      <footer className="border-t border-brdr bg-surface py-6 text-center text-xs text-muted">
        Advantage Pro · Vectra Technosoft · since 1998
      </footer>
    </div>
  );
}
