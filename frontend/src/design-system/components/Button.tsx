import type { ButtonHTMLAttributes } from "react";

import { cn } from "../utils/cn";

type Variant = "primary" | "soft" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary: "bg-brand-strong text-white hover:bg-navy",
  soft: "bg-sky text-navy border border-brdr hover:bg-brand/10",
  ghost: "bg-surface text-ink border border-brdr hover:bg-sky",
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/50 disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
