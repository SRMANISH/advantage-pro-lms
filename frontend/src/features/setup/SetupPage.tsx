import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button, Card, Input, Logo } from "../../design-system";
import { setupApi } from "./api";

type Step = "loading" | "email" | "phone" | "password" | "done" | "error";

const STEP_LABEL: Record<string, string> = {
  email: "Step 1 of 3 · Email code",
  phone: "Step 2 of 3 · Phone code",
  password: "Step 3 of 3 · Set password",
};

export function SetupPage() {
  const { token = "" } = useParams();
  const [step, setStep] = useState<Step>("loading");
  const [error, setError] = useState<string | null>(null);
  const [masked, setMasked] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    setupApi.start(token).then((r) => {
      if (r.detail) {
        setError(r.detail);
        setStep("error");
      } else {
        setMasked(r.email ?? "");
        setDevCode(r.dev_code ?? null);
        setStep("email");
      }
    });
  }, [token]);

  const submitEmail = async () => {
    setBusy(true);
    setError(null);
    const r = await setupApi.verifyEmail(token, code);
    setBusy(false);
    if (r.detail) return setError(r.detail);
    setMasked(r.phone ?? "");
    setDevCode(r.dev_code ?? null);
    setCode("");
    setStep("phone");
  };

  const submitPhone = async () => {
    setBusy(true);
    setError(null);
    const r = await setupApi.verifyPhone(token, code);
    setBusy(false);
    if (r.detail) return setError(r.detail);
    setCode("");
    setStep("password");
  };

  const submitPassword = async () => {
    setError(null);
    if (pw !== pw2) return setError("Passwords do not match.");
    setBusy(true);
    const r = await setupApi.complete(token, pw);
    setBusy(false);
    if (r.detail) return setError(r.detail);
    setStep("done");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-appbg p-6">
      <Card className="w-full max-w-md">
        <div className="mb-4 flex justify-center">
          <Logo size={84} />
        </div>

        {step === "loading" && <p className="text-center text-sm text-muted">Loading…</p>}

        {step === "error" && (
          <div className="text-center">
            <h1 className="text-lg font-medium text-ink">Setup link problem</h1>
            <p className="mt-2 text-sm text-red-600">{error}</p>
            <p className="mt-3 text-sm text-muted">Ask your administrator to resend your link.</p>
          </div>
        )}

        {(step === "email" || step === "phone" || step === "password") && (
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-brand-strong">{STEP_LABEL[step]}</p>

            {step === "email" && (
              <>
                <p className="text-sm text-muted">
                  Enter the code we sent to <span className="text-ink">{masked}</span>.
                </p>
                <Input
                  inputMode="numeric"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="6-digit code"
                />
                <Button onClick={submitEmail} disabled={busy || code.length < 4}>
                  {busy ? "Verifying…" : "Verify email"}
                </Button>
              </>
            )}

            {step === "phone" && (
              <>
                <p className="text-sm text-muted">
                  Enter the code we sent to <span className="text-ink">{masked}</span>.
                </p>
                <Input
                  inputMode="numeric"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="6-digit code"
                />
                <Button onClick={submitPhone} disabled={busy || code.length < 4}>
                  {busy ? "Verifying…" : "Verify phone"}
                </Button>
              </>
            )}

            {step === "password" && (
              <>
                <p className="text-sm text-muted">Choose a password (at least 10 characters).</p>
                <Input
                  type="password"
                  value={pw}
                  onChange={(e) => setPw(e.target.value)}
                  placeholder="New password"
                />
                <Input
                  type="password"
                  value={pw2}
                  onChange={(e) => setPw2(e.target.value)}
                  placeholder="Confirm password"
                />
                <Button onClick={submitPassword} disabled={busy || !pw || !pw2}>
                  {busy ? "Activating…" : "Activate account"}
                </Button>
              </>
            )}

            {devCode && (
              <p className="text-xs text-muted">Dev code: {devCode}</p>
            )}
            {error && (
              <p className="text-sm text-red-600" role="alert">
                {error}
              </p>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="text-center">
            <h1 className="text-lg font-medium text-ink">Account activated</h1>
            <p className="mt-2 text-sm text-muted">You can now sign in.</p>
            <Link
              to="/login/student"
              className="mt-4 inline-block rounded-lg bg-brand-strong px-4 py-2 text-sm font-medium text-white"
            >
              Go to sign in
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}
