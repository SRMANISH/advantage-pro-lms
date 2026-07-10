import { Check, Circle, Dot } from "lucide-react";

import { cn } from "../utils/cn";

/**
 * Mirrors the backend AUTH_PASSWORD_VALIDATORS so users see the rules up front on every
 * password screen (setup, reset, change). The two client-verifiable rules (length, not
 * all-numeric) light up live as you type; the two server-only rules (common-password
 * blocklist, similarity to your own details) show as guidance — they're enforced on
 * submit and their exact message is surfaced in the form's error line.
 */
export function PasswordRules({ value, className }: { value: string; className?: string }) {
  const typed = value.length > 0;
  const live = [
    { label: "At least 10 characters", met: value.length >= 10 },
    { label: "Not entirely numbers", met: typed && !/^\d+$/.test(value) },
  ];
  const guidance = [
    "Not a common or easily-guessed password",
    "Not too similar to your name, email or Registration ID",
  ];

  return (
    <ul className={cn("flex flex-col gap-1 text-xs", className)} aria-label="Password requirements">
      {live.map((r) => (
        <li
          key={r.label}
          className={cn("flex items-center gap-1.5", r.met ? "text-success" : "text-muted")}
        >
          {r.met ? (
            <Check size={13} aria-hidden />
          ) : (
            <Circle size={11} className="ml-px mr-px" aria-hidden />
          )}
          <span>{r.label}</span>
        </li>
      ))}
      {guidance.map((label) => (
        <li key={label} className="flex items-center gap-1.5 text-muted">
          <Dot size={14} aria-hidden />
          <span>{label}</span>
        </li>
      ))}
    </ul>
  );
}
