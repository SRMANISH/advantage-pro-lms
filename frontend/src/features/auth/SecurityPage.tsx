import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import type { RoleDef } from "../../app/roles";
import { Badge, Button, Card, Input, SectionHeading, Spinner, useToast } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { totpApi, type TOTPEnrollment } from "./totpApi";

export function SecurityPage({ role }: { role: RoleDef }) {
  const qc = useQueryClient();
  const toast = useToast();
  const status = useQuery({ queryKey: ["totp-status"], queryFn: totpApi.status });

  const [enrollment, setEnrollment] = useState<TOTPEnrollment | null>(null);
  const [code, setCode] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [confirming, setConfirming] = useState(false);

  const [disablePassword, setDisablePassword] = useState("");
  const [disableError, setDisableError] = useState("");
  const [disabling, setDisabling] = useState(false);

  const startEnroll = async () => {
    setConfirmError("");
    try {
      setEnrollment(await totpApi.enroll());
    } catch {
      toast.show("Could not start enrollment. Please try again.", "error");
    }
  };

  const confirmEnroll = async () => {
    setConfirmError("");
    setConfirming(true);
    try {
      await totpApi.confirm(code);
      setEnrollment(null);
      setCode("");
      qc.invalidateQueries({ queryKey: ["totp-status"] });
      toast.show("Two-factor authentication is now on.", "success");
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setConfirmError(detail ?? "Invalid code — check your app and try again.");
    } finally {
      setConfirming(false);
    }
  };

  const disable = async () => {
    setDisableError("");
    setDisabling(true);
    try {
      await totpApi.disable(disablePassword);
      setDisablePassword("");
      qc.invalidateQueries({ queryKey: ["totp-status"] });
      toast.show("Two-factor authentication turned off.", "success");
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDisableError(detail ?? "Could not turn off two-factor authentication.");
    } finally {
      setDisabling(false);
    }
  };

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Two-factor authentication"
        subtitle="Add a 6-digit code from an authenticator app to your sign-in, on top of your password."
      />
      <Card className="max-w-md">
        {status.isLoading ? (
          <Spinner size={20} />
        ) : status.data?.enabled ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Badge tone="success">Enabled</Badge>
              <span className="text-sm text-muted">
                Your account requires a code from your app at every sign-in.
              </span>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted" htmlFor="disable-pw">
                Current password
              </label>
              <Input
                id="disable-pw"
                type="password"
                autoComplete="current-password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
              />
            </div>
            {disableError && (
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
                {disableError}
              </p>
            )}
            <Button
              variant="ghost"
              className="w-fit text-danger hover:bg-danger/10"
              onClick={disable}
              disabled={!disablePassword || disabling}
            >
              {disabling ? "Turning off…" : "Turn off two-factor authentication"}
            </Button>
          </div>
        ) : enrollment ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-ink">
              Scan this with your authenticator app (Google Authenticator, Authy, 1Password…),
              or enter the key manually.
            </p>
            <div className="flex justify-center rounded-xl bg-white p-4">
              <QRCodeSVG value={enrollment.otpauth_url} size={176} />
            </div>
            <p className="break-all rounded-lg bg-sky/50 px-3 py-2 text-center font-mono text-xs text-navy">
              {enrollment.secret}
            </p>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted" htmlFor="confirm-code">
                Enter the 6-digit code from your app
              </label>
              <Input
                id="confirm-code"
                inputMode="numeric"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
              />
            </div>
            {confirmError && (
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
                {confirmError}
              </p>
            )}
            <div className="flex gap-2">
              <Button onClick={confirmEnroll} disabled={!code || confirming}>
                {confirming ? "Verifying…" : "Confirm & enable"}
              </Button>
              <Button variant="ghost" onClick={() => setEnrollment(null)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Badge>Disabled</Badge>
              <span className="text-sm text-muted">Only your password is required to sign in.</span>
            </div>
            <Button className="w-fit" onClick={startEnroll}>
              Enable two-factor authentication
            </Button>
          </div>
        )}
      </Card>
    </PortalLayout>
  );
}
