import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button, Input, Logo, Spinner, cn } from "../../design-system";
import { setupApi } from "./api";

type Step = "loading" | "email" | "phone" | "password" | "done" | "error";

const STEP_LABEL: Record<string, string> = {
  email: "Step 1 of 3 · Verify your email",
  phone: "Step 2 of 3 · Verify your phone",
  password: "Step 3 of 3 · Set your password",
};

const STEP_ORDER = ["email", "phone", "password"] as const;

function StepDots({ step }: { step: Step }) {
  const idx = STEP_ORDER.indexOf(step as (typeof STEP_ORDER)[number]);
  if (idx < 0) return null;
  return (
    <div className="mb-4 flex items-center gap-2" aria-hidden>
      {STEP_ORDER.map((s, i) => (
        <span
          key={s}
          className={cn(
            "h-1.5 flex-1 rounded-full transition-colors duration-500",
            i < idx ? "bg-success" : i === idx ? "bg-brand" : "bg-sky",
          )}
        />
      ))}
    </div>
  );
}

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
    <div className="ap-hero-soft flex min-h-screen items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md rounded-3xl border border-brdr bg-surface p-8 shadow-lift"
      >
        <div className="mb-5 flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white shadow-card ring-1 ring-black/5">
            <Logo size={40} />
          </span>
          <div className="leading-tight">
            <h1 className="text-lg font-semibold tracking-tight text-ink">
              Welcome to Advantage Pro
            </h1>
            <p className="text-xs text-muted">Let&apos;s set up your account — takes a minute.</p>
          </div>
        </div>

        {step === "loading" && (
          <div className="flex justify-center py-8">
            <Spinner size={26} />
          </div>
        )}

        {step === "error" && (
          <div className="text-center">
            <h2 className="text-lg font-medium text-ink">Setup link problem</h2>
            <p className="mt-2 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
            <p className="mt-3 text-sm text-muted">Ask your administrator to resend your link.</p>
          </div>
        )}

        {(step === "email" || step === "phone" || step === "password") && (
          <div className="flex flex-col gap-3">
            <StepDots step={step} />
            <p className="text-xs font-semibold uppercase tracking-wider text-brand-strong">
              {STEP_LABEL[step]}
            </p>

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
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
                {error}
              </p>
            )}
          </div>
        )}

        {step === "done" && (
          <div className="text-center">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-success/10 text-2xl">
              🎉
            </span>
            <h2 className="mt-3 text-lg font-semibold text-ink">Account activated</h2>
            <p className="mt-1 text-sm text-muted">
              Welcome aboard — your learning journey starts now.
            </p>
            <Link
              to="/login/student"
              className="mt-5 inline-block rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-strong"
            >
              Go to sign in
            </Link>
          </div>
        )}
      </motion.div>
    </div>
  );
}
