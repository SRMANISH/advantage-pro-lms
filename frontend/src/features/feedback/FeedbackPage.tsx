import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import type { RoleDef } from "../../app/roles";
import { Button, Card, Input, SectionHeading, useToast } from "../../design-system";
import { PortalLayout } from "../portal/PortalLayout";
import { feedbackApi } from "./api";

/** Student → management private feedback (req 20). Delivered to Super Admin only. */
export function FeedbackPage({ role }: { role: RoleDef }) {
  const toast = useToast();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");

  const send = useMutation({
    mutationFn: () => feedbackApi.send({ subject, message }),
    onSuccess: () => {
      setSubject("");
      setMessage("");
      toast.show("Sent privately to management. Thank you.", "success");
    },
    onError: () => toast.show("Could not send — please try again.", "error"),
  });

  return (
    <PortalLayout role={role}>
      <SectionHeading
        title="Message management"
        subtitle="Have feedback about a faculty, admin or the programme? This goes privately to the management — no one else can see it."
      />
      <Card className="max-w-xl">
        <div className="flex flex-col gap-3">
          <div>
            <label htmlFor="fb-subject" className="mb-1 block text-xs font-medium text-muted">
              Subject
            </label>
            <Input
              id="fb-subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Short summary"
            />
          </div>
          <div>
            <label htmlFor="fb-message" className="mb-1 block text-xs font-medium text-muted">
              Message
            </label>
            <textarea
              id="fb-message"
              className="min-h-32 w-full rounded-lg border border-brdr bg-surface p-2 text-sm"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Tell management what's on your mind…"
            />
          </div>
          <Button
            className="w-fit"
            onClick={() => send.mutate()}
            disabled={!subject || !message || send.isPending}
          >
            {send.isPending ? "Sending…" : "Send to management"}
          </Button>
        </div>
      </Card>
    </PortalLayout>
  );
}
