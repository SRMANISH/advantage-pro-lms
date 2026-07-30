import { motion } from "framer-motion";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ROLES, slugForRole } from "../app/roles";
import { Button, Input, Logo, fadeUp, staggerContainer, staggerItem } from "../design-system";
import { useAuth } from "../features/auth/auth";

const FEATURES = [
  { title: "Learn your way", body: "Live classes and recorded lessons you can revisit anytime." },
  { title: "Practice with purpose", body: "Tests, tasks and faculty feedback that help you improve." },
  { title: "See your progress", body: "Attendance, scores, streaks and rank in one clear view." },
];

const NAV_LINKS: Array<{ label: string; href?: string; to?: string }> = [
  { label: "Features", href: "#features" },
  { label: "Utility links", to: "/utility-links" },
  { label: "Contact", href: "#contact" },
];

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-sky via-appbg to-surface">
      {/* Ambient brand glows */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-brand/10 blur-3xl" />
        <div className="absolute -right-24 top-1/3 h-96 w-96 rounded-full bg-navy/10 blur-3xl" />
      </div>

      <Navbar />

      <main className="relative mx-auto grid max-w-6xl gap-10 px-6 pb-10 pt-8 lg:grid-cols-2 lg:items-center lg:pt-14">
        <motion.div variants={staggerContainer} initial="hidden" animate="show">
          <motion.span
            variants={staggerItem}
            className="inline-flex rounded-full border border-brdr bg-surface px-3 py-1 text-xs font-medium tracking-wide text-navy shadow-card"
          >
            YOUR LEARNING, ALL IN ONE PLACE
          </motion.span>
          <motion.h1
            variants={staggerItem}
            className="mt-5 text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl"
          >
            Everything you need to
            <br />
            <span className="relative text-brand-strong">
              learn and grow.
              <span className="absolute -bottom-1 left-0 h-1 w-full rounded-full bg-brand/40" />
            </span>
          </motion.h1>
          <motion.p variants={staggerItem} className="mt-5 max-w-md text-base text-muted">
            Watch classes, practise with tests and tasks, track your attendance and scores, and
            stay connected with your batch — your whole learning journey in one place.
          </motion.p>

          <motion.div id="features" variants={staggerItem} className="mt-8 grid gap-3 sm:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-2xl border border-brdr bg-surface/70 p-4 shadow-card">
                <div className="text-sm font-semibold text-ink">{f.title}</div>
                <div className="mt-1 text-xs leading-relaxed text-muted">{f.body}</div>
              </div>
            ))}
          </motion.div>

          <motion.p variants={staggerItem} className="mt-8 text-xs text-muted">
            Vectra Technosoft · Networking with success · since 1998
          </motion.p>
        </motion.div>

        <motion.div variants={fadeUp} initial="hidden" animate="show" id="signin">
          <SignInCard />
        </motion.div>
      </main>

      <footer
        id="contact"
        className="relative border-t border-brdr bg-surface/60 py-6 text-center text-xs text-muted"
      >
        Advantage Pro · Vectra Technosoft · since 1998
      </footer>
    </div>
  );
}

function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-brdr/70 bg-surface/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <a href="#top" className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface shadow-card ring-1 ring-black/5">
            <Logo size={38} />
          </span>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold text-ink">Advantage Pro</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted">
              Learning Management
            </div>
          </div>
        </a>
        <nav className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((l) =>
            l.to ? (
              <Link
                key={l.label}
                to={l.to}
                className="text-sm font-medium text-muted transition-colors hover:text-brand-strong"
              >
                {l.label}
              </Link>
            ) : (
              <a
                key={l.label}
                href={l.href}
                className="text-sm font-medium text-muted transition-colors hover:text-brand-strong"
              >
                {l.label}
              </a>
            ),
          )}
        </nav>
        <a
          href="#signin"
          className="rounded-xl bg-brand px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-strong"
        >
          Sign in
        </a>
      </div>
    </header>
  );
}

/** One sign-in for everyone — the backend routes each account to its own portal. */
function SignInCard() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await login(identifier, password);
      navigate(`/${slugForRole(user.role)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-3xl border border-brdr bg-surface p-8 shadow-lift">
      <div className="text-xs font-semibold uppercase tracking-wider text-brand-strong">
        Welcome back
      </div>
      <h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
        Sign in to your workspace
      </h2>
      <p className="mt-1 text-sm text-muted">
        One sign-in for everyone — we&apos;ll take you straight to your portal.
      </p>

      <form className="mt-6 flex flex-col gap-3" onSubmit={submit}>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted" htmlFor="landing-id">
            Email or Registration ID
          </label>
          <Input
            id="landing-id"
            autoComplete="username"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="Example: s101@example.com or S101"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-muted" htmlFor="landing-pw">
            Password
          </label>
          <Input
            id="landing-pw"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>
        {error && (
          <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" className="mt-1 w-full" disabled={!identifier || !password || busy}>
          {busy ? "Signing in…" : "Sign in securely"}
        </Button>
      </form>

      <div className="mt-4 flex items-center justify-between text-xs">
        <Link to="/forgot-password" className="font-medium text-brand-strong hover:underline">
          Forgot password?
        </Link>
        <span className="text-muted">New student? Check your setup email.</span>
      </div>

      <div className="mt-5 border-t border-brdr pt-4">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">
          Prefer your role page?
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {ROLES.map((r) => (
            <Link
              key={r.slug}
              to={`/login/${r.slug}`}
              className="text-xs font-medium text-navy/70 hover:text-brand-strong hover:underline"
            >
              {r.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

