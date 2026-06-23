import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Button, Input, Logo } from "../../design-system";
import { useAuth } from "./auth";

interface LoginPageProps {
  role: RoleDef;
}

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
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="hidden flex-col items-center justify-center gap-3 bg-sky p-10 text-center md:flex">
        <Logo size={150} />
        <p className="mt-2 text-sm text-navy">{role.tagline}</p>
      </div>

      <div className="flex flex-col justify-center gap-4 p-8 md:p-14">
        <div className="md:hidden">
          <Logo size={72} />
        </div>
        <div>
          <h1 className="text-xl font-medium text-ink">{role.label} sign in</h1>
          <p className="text-sm text-muted">Use the credentials issued for your account.</p>
        </div>

        <form className="flex flex-col gap-3" onSubmit={onSubmit}>
          <label className="text-xs text-muted" htmlFor="login-id">
            Login ID
          </label>
          <Input
            id="login-id"
            autoComplete="username"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            placeholder="e.g. your registration number"
          />
          <label className="text-xs text-muted" htmlFor="password">
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

          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" className="mt-2" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in securely"}
          </Button>
        </form>

        <p className="text-xs text-muted">Two-step verified · device-bound access.</p>
      </div>
    </div>
  );
}
