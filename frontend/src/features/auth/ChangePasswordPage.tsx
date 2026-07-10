import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { RoleDef } from "../../app/roles";
import { Button, Card, Input, PasswordRules, SectionHeading, useToast } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { passwordApi } from "./passwordApi";

export function ChangePasswordPage({ role }: { role: RoleDef }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    if (newPw !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await passwordApi.change(oldPw, newPw);
      toast.show("Password changed.", "success");
      setOldPw("");
      setNewPw("");
      setConfirm("");
      navigate(`/${role.slug}`);
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Could not change password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PortalLayout role={role}>
      <SectionHeading title="Change password" subtitle="Update your account password." />
      <Card className="max-w-md">
        <div className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-muted" htmlFor="old-pw">
              Current password
            </label>
            <Input
              id="old-pw"
              type="password"
              autoComplete="current-password"
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted" htmlFor="new-pw">
              New password
            </label>
            <Input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
            <PasswordRules value={newPw} className="mt-2" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-muted" htmlFor="confirm-pw">
              Confirm new password
            </label>
            <Input
              id="confirm-pw"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
          {error && (
            <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
              {error}
            </p>
          )}
          <Button onClick={submit} disabled={!oldPw || !newPw || !confirm || busy}>
            {busy ? "Saving…" : "Change password"}
          </Button>
        </div>
      </Card>
    </PortalLayout>
  );
}
