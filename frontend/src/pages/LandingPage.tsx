import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import { ROLES } from "../app/roles";
import { Logo, fadeUp, staggerContainer, staggerItem } from "../design-system";

const FEATURES = [
  { title: "Learn your way", body: "Live classes and recorded lessons you can revisit anytime." },
  { title: "Practice with purpose", body: "Tests, tasks and faculty feedback that help you improve." },
  { title: "See your progress", body: "Attendance, scores, streaks and rank in one clear view." },
];

const PRIMARY = ["student", "faculty", "admin", "super_admin"];

export function LandingPage() {
  const primaryRoles = PRIMARY.map((v) => ROLES.find((r) => r.value === v)!).filter(Boolean);

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-sky via-appbg to-surface">
      {/* Ambient brand glows */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -left-24 -top-24 h-80 w-80 rounded-full bg-brand/10 blur-3xl" />
        <div className="absolute -right-24 top-1/3 h-96 w-96 rounded-full bg-navy/10 blur-3xl" />
      </div>

      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface shadow-card">
            <Logo size={42} />
          </span>
          <div className="leading-tight">
            <div className="text-base font-semibold text-ink">Advantage Pro</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted">
              Learning Management
            </div>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-brdr bg-surface px-3 py-1.5 text-xs text-muted shadow-card">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          All learning systems operational
        </span>
      </header>

      <main className="relative mx-auto grid max-w-6xl gap-10 px-6 pb-16 pt-6 lg:grid-cols-2 lg:items-center lg:pt-14">
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
            Watch classes, practise with tests and tasks, track your attendance and scores, and stay
            connected with your batch — your whole learning journey in one place.
          </motion.p>

          <motion.div variants={staggerItem} className="mt-8 grid gap-3 sm:grid-cols-3">
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

        <motion.div variants={fadeUp} initial="hidden" animate="show">
          <div className="rounded-3xl border border-brdr bg-surface p-8 shadow-lift">
            <div className="text-xs font-semibold uppercase tracking-wider text-brand-strong">
              Welcome to Advantage Pro
            </div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
              Sign in to your portal
            </h2>
            <p className="mt-1 text-sm text-muted">
              Pick your portal and jump back into learning.
            </p>

            <div className="mt-6 grid grid-cols-2 gap-3">
              {primaryRoles.map((r) => (
                <Link
                  key={r.slug}
                  to={`/login/${r.slug}`}
                  className="group rounded-xl border border-brdr bg-surface px-4 py-3 transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-card"
                >
                  <div className="text-sm font-semibold text-navy group-hover:text-brand-strong">
                    {r.label}
                  </div>
                  <div className="truncate text-xs text-muted">{r.tagline}</div>
                </Link>
              ))}
            </div>

            <Link
              to="/login/mis"
              className="mt-3 block rounded-xl bg-brand-strong px-4 py-3 text-center text-sm font-semibold text-white transition hover:bg-navy"
            >
              Other staff sign in
            </Link>

            <div className="mt-5 flex items-center justify-between text-xs">
              <Link to="/forgot-password" className="font-medium text-brand-strong hover:underline">
                Forgot password?
              </Link>
              <span className="text-muted">Two-step verified access</span>
            </div>
          </div>
        </motion.div>
      </main>

      <footer className="relative border-t border-brdr bg-surface/60 py-6 text-center text-xs text-muted">
        Advantage Pro · Vectra Technosoft · since 1998
      </footer>
    </div>
  );
}
