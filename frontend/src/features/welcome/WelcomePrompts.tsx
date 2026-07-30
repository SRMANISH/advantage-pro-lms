import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button, Card, Input } from "../../design-system";
import { welcomeApi, type WelcomePrompt } from "./api";

/**
 * Post-enrolment welcome popup (reqs 16/17): asks each new student two questions — is
 * their address on file, and have they received their Advantage Pro goodies. Shown to
 * students on any portal page (mounted in PortalLayout), one enrolment at a time.
 */
export function WelcomePrompts() {
  const pending = useQuery({ queryKey: ["welcome-me"], queryFn: welcomeApi.pending });
  const first = pending.data?.[0];
  if (!first) return null;
  return <WelcomeCard key={first.enrollment} prompt={first} />;
}

function WelcomeCard({ prompt }: { prompt: WelcomePrompt }) {
  const qc = useQueryClient();
  const [addressOnFile, setAddressOnFile] = useState<boolean | null>(null);
  const [goodiesReceived, setGoodiesReceived] = useState<boolean | null>(null);
  const [address, setAddress] = useState(prompt.address);

  const submit = useMutation({
    mutationFn: () =>
      welcomeApi.submit({
        enrollment: prompt.enrollment,
        address_on_file: addressOnFile!,
        goodies_received: goodiesReceived!,
        address: addressOnFile ? undefined : address,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["welcome-me"] }),
  });

  const needsAddress = addressOnFile === false;
  const canSubmit =
    addressOnFile !== null &&
    goodiesReceived !== null &&
    (!needsAddress || address.trim().length > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md">
        <h2 className="mb-1 text-base font-medium text-ink">Quick welcome check</h2>
        <p className="mb-4 text-sm text-muted">
          For your <span className="font-medium text-ink">{prompt.batch_code}</span> batch — two
          quick questions.
        </p>

        <YesNo
          label="Do we have your correct postal address on file?"
          value={addressOnFile}
          onChange={setAddressOnFile}
        />
        {needsAddress && (
          <div className="mb-4">
            <label htmlFor="welcome-address" className="mb-1 block text-xs text-muted">
              Your postal address (we'll send this to the office for your goodies)
            </label>
            <Input
              id="welcome-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="House, street, city, PIN"
            />
          </div>
        )}

        <YesNo
          label="Have you received your Advantage Pro goodies?"
          value={goodiesReceived}
          onChange={setGoodiesReceived}
        />

        <Button
          className="mt-2 w-full"
          onClick={() => submit.mutate()}
          disabled={!canSubmit || submit.isPending}
        >
          {submit.isPending ? "Saving…" : "Submit"}
        </Button>
      </Card>
    </div>
  );
}

function YesNo({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="mb-4">
      <p className="mb-1.5 text-sm text-ink">{label}</p>
      <div className="flex gap-2">
        <Button variant={value === true ? "primary" : "ghost"} onClick={() => onChange(true)}>
          Yes
        </Button>
        <Button variant={value === false ? "primary" : "ghost"} onClick={() => onChange(false)}>
          No
        </Button>
      </div>
    </div>
  );
}
