import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../utils/cn";

type Tone = "default" | "info" | "success" | "warning" | "danger" | "neutral";

const tones: Record<Tone, string> = {
  default: "bg-sky text-navy",
  info: "bg-brand/10 text-brand-strong",
  success: "bg-success/12 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-danger/12 text-danger",
  neutral: "bg-appbg text-muted",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

/**
 * Sentence-cases a plain-string label.
 *
 * Badges carry raw backend enum values (`{batch.state}` -> "active", `{status}` -> "escalated")
 * that must not render starting lowercase. This was previously the Tailwind `capitalize` class,
 * which is wrong twice over: it Title-Cases *every* word ("awaiting grade" -> "Awaiting Grade"),
 * and `text-transform` changes only the pixels — a screen reader still announces "active", and
 * copying the badge still yields lowercase. `::first-letter` would not have worked at all here,
 * since it does not apply to an inline-flex container.
 *
 * Non-string children (interpolated fragments like `Graded {score}/{total}`) pass through
 * untouched; those are written in sentence case at the call site.
 */
function sentenceCase(children: ReactNode): ReactNode {
  if (typeof children !== "string" || children.length === 0) return children;
  return children.charAt(0).toUpperCase() + children.slice(1);
}

export function Badge({ tone = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    >
      {sentenceCase(children)}
    </span>
  );
}
