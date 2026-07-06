import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, Card, Input, Logo } from "../../design-system";
import { passwordApi } from "./passwordApi";

type Step = "identify" | "email" | "phone" | "password" | "done";

function errOf(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return detail ?? "Something went wrong. Please try again.";
}

export function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>("identify");
  const [identifier, setIdentifier] = useState("");
  const [token, setToken] = useState("");
  const [mask, setMask] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(errOf(e));
    } finally {
      setBusy(false);
    }
  };

  const start = () =>
    run(async () => {
      const r = await passwordApi.forgot(identifier);
      setToken(r.token);
      setMask(r.email);
      setCode("");
      setStep("email");
    });

  const verifyEmail = () =>
    run(async () => {
      const r = await passwordApi.verifyEmail(token, code);
      setMask(r.phone ?? "");
      setCode("");
      setStep("phone");
    });

  const verifyPhone = () =>
    run(async () => {
      await passwordApi.verifyPhone(token, code);
      setStep("password");
    });

  const reset = () =>
    run(async () => {
      if (pw !== pw2) {
        setError("Passwords do not match.");
        return;
      }
      await passwordApi.reset(token, pw);
      setStep("done");
    });

  return (
    <div className="flex min-h-screen items-center justify-center bg-appbg p-4">
      <Card className="w-full max-w-md">
        <div className="mb-4 flex justify-center">
          <Logo size={56} />
        </div>
        <h1 className="mb-1 text-center text-xl font-medium text-ink">Reset your password</h1>
        <p className="mb-4 text-center text-sm text-muted">
          Two-step verification keeps your account secure.
        </p>

        {error && (
          <p className="mb-3 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {step === "identify" && (
          <div className="flex flex-col gap-2">
            <label htmlFor="forgot-identifier" className="text-xs text-muted">
              Email or Registration ID
            </label>
            <Input
              id="forgot-identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
            <Button onClick={start} disabled={!identifier || busy}>
              {busy ? "Sending…" : "Send email code"}
            </Button>
          </div>
        )}

        {step === "email" && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted">We sent a code to {mask}.</p>
            <Input placeholder="6-digit email code" value={code} onChange={(e) => setCode(e.target.value)} />
            <Button onClick={verifyEmail} disabled={!code || busy}>
              {busy ? "Verifying…" : "Verify email"}
            </Button>
          </div>
        )}

        {step === "phone" && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted">Enter the code sent to {mask}.</p>
            <Input placeholder="6-digit phone code" value={code} onChange={(e) => setCode(e.target.value)} />
            <Button onClick={verifyPhone} disabled={!code || busy}>
              {busy ? "Verifying…" : "Verify phone"}
            </Button>
          </div>
        )}

        {step === "password" && (
          <div className="flex flex-col gap-2">
            <Input type="password" placeholder="New password" value={pw} onChange={(e) => setPw(e.target.value)} />
            <Input type="password" placeholder="Confirm new password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
            <Button onClick={reset} disabled={!pw || !pw2 || busy}>
              {busy ? "Saving…" : "Set new password"}
            </Button>
          </div>
        )}

        {step === "done" && (
          <div className="text-center">
            <p className="mb-3 text-sm text-[color:var(--color-text-success,#1E8E5A)]">
              ✓ Password reset. You can sign in now.
            </p>
            <Link to="/login/student" className="text-brand-strong underline">
              Go to sign in
            </Link>
          </div>
        )}

        {step !== "done" && (
          <p className="mt-4 text-center text-xs text-muted">
            <Link to="/login/student" className="underline">
              Back to sign in
            </Link>
          </p>
        )}
      </Card>
    </div>
  );
}
