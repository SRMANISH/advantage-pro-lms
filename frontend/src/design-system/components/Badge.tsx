import type { HTMLAttributes } from "react";

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

export function Badge({ tone = "default", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
