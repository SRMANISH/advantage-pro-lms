import { AnimatePresence, motion } from "framer-motion";
import { ClipboardList, PlayCircle, TrendingUp } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Button, Input, Logo } from "../../design-system";
import { TotpRequiredError } from "./api";
import { useAuth } from "./auth";

interface LoginPageProps {
  role: RoleDef;
}

const QUOTES = [
  "Learning today, leading tomorrow.",
  "Every login is one step closer to your goal.",
  "Small progress every day becomes big results.",
];

const HIGHLIGHTS = [
  {
    Icon: PlayCircle,
    title: "Learn at your pace",
    body: "Join live classes or replay recorded lessons whenever it suits you.",
  },
  {
    Icon: ClipboardList,
    title: "Practice with feedback",
    body: "Attempt tests, submit tasks and get faculty feedback that helps you grow.",
  },
  {
    Icon: TrendingUp,
    title: "Track your growth",
    body: "Attendance, scores, streaks and rank — always know where you stand.",
  },
];

/** Role-bound login page. Each role has its own URL; the server rejects mismatched accounts. */
export function LoginPage({ role }: LoginPageProps) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [quote, setQuote] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setQuote((q) => (q + 1) % QUOTES.length), 4500);
    return () => clearInterval(t);
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(loginId, password, role.value, needsTotp ? totpCode : undefined);
      navigate(`/${role.slug}`);
    } catch (e) {
      if (e instanceof TotpRequiredError) {
        setNeedsTotp(true);
        setError(needsTotp ? e.message : null); // only show as an error on a retry
      } else {
        setError(e instanceof Error ? e.message : "Invalid credentials for this portal.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="ap-hero relative hidden flex-col justify-between overflow-hidden p-12 text-white lg:flex">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-brand/20 blur-3xl" />
          <div className="absolute -bottom-24 -left-10 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
        </div>
        <div className="relative flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white shadow-sm">
            <Logo size={40} />
          </span>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold">Advantage Pro</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-white/60">
              Learning Management
            </div>
          </div>
        </div>
        <div className="relative">
          <h2 className="text-[2rem] font-semibold leading-[1.15] tracking-tight">
            A richer way to learn, all in one place.
          </h2>
          <div className="mt-4 h-7">
            <AnimatePresence mode="wait">
              <motion.p
                key={quote}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.4 }}
                className="text-base font-medium text-white/90"
              >
                “{QUOTES[quote]}”
              </motion.p>
            </AnimatePresence>
          </div>
          <div className="mt-9 space-y-3">
            {HIGHLIGHTS.map(({ Icon, title, body }) => (
              <div
                key={title}
                className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/10 p-3.5 backdrop-blur"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/15">
                  <Icon size={18} />
                </span>
                <div>
                  <div className="text-sm font-semibold">{title}</div>
                  <div className="text-xs leading-relaxed text-white/70">{body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-white/40">
          Vectra Technosoft · Networking with success · since 1998
        </p>
      </div>

      {/* Sign-in card */}
      <div className="flex items-center justify-center bg-appbg p-6 sm:p-10">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-md rounded-3xl border border-brdr bg-surface p-8 shadow-lift"
        >
          <div className="mb-6 lg:hidden">
            <Logo size={56} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{role.label} sign in</h1>
          <p className="mt-1 text-sm text-muted">Welcome back — continue your learning journey.</p>

          <form className="mt-6 flex flex-col gap-3" onSubmit={onSubmit}>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted" htmlFor="login-id">
                Registration ID / Login ID
              </label>
              <Input
                id="login-id"
                autoComplete="username"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                placeholder="Example: your Registration ID"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted" htmlFor="password">
                Password
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={needsTotp}
              />
            </div>

            {needsTotp && (
              <div>
                <label className="mb-1 block text-xs font-medium text-muted" htmlFor="totp-code">
                  Authenticator code
                </label>
                <Input
                  id="totp-code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="6-digit code"
                />
              </div>
            )}

            {error && (
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="mt-2 w-full"
              disabled={submitting || (needsTotp && !totpCode)}
            >
              {submitting ? "Signing in…" : needsTotp ? "Verify code" : "Sign in securely"}
            </Button>
          </form>

          <div className="mt-5 flex items-center justify-between text-xs">
            <Link to="/forgot-password" className="font-medium text-brand-strong hover:underline">
              Forgot password?
            </Link>
            <Link to="/" className="text-muted hover:text-navy">
              ← All portals
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
