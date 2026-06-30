import { motion } from "framer-motion";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Button, Input, Logo } from "../../design-system";
import { useAuth } from "./auth";

interface LoginPageProps {
  role: RoleDef;
}

const TRUST = [
  "Two-step verified sign-in",
  "Device-bound student access",
  "Private, batch-based workspace",
];

/** Role-bound login page. Each role has its own URL; the server rejects mismatched accounts. */
export function LoginPage({ role }: LoginPageProps) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(loginId, password, role.value);
      navigate(`/${role.slug}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid credentials for this portal.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-navyDeep to-navy p-12 text-white lg:flex">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-brand/20 blur-3xl" />
          <div className="absolute -bottom-24 -left-10 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
        </div>
        <div className="relative flex items-center gap-3">
          <Logo size={40} className="ring-2 ring-white/15" />
          <div className="leading-tight">
            <div className="text-sm font-semibold">Advantage Pro</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-white/50">
              Learning Management
            </div>
          </div>
        </div>
        <div className="relative">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            {role.label} workspace
          </h2>
          <p className="mt-3 max-w-sm text-sm text-white/70">{role.tagline}</p>
          <ul className="mt-8 space-y-3">
            {TRUST.map((t) => (
              <li key={t} className="flex items-center gap-3 text-sm text-white/80">
                <span className="h-1.5 w-1.5 rounded-full bg-brand" />
                {t}
              </li>
            ))}
          </ul>
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
          <p className="mt-1 text-sm text-muted">Use the credentials issued for your account.</p>

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
                placeholder="e.g. your Registration ID"
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
              />
            </div>

            {error && (
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" className="mt-2 w-full" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in securely"}
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
