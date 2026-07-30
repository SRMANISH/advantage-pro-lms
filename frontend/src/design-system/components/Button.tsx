import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";

import { cn } from "../utils/cn";

type Variant = "primary" | "soft" | "ghost";

/**
 * Pass `href` to render an `<a>` styled as a button. Actions that are genuinely navigations
 * — a CSV download, an external link — must stay anchors so the browser handles them
 * natively (middle-click, "save as", keyboard activation); the alternative is a `<button>`
 * that reimplements downloading in JS. Everything else renders a real `<button>`.
 */
type ButtonProps = { variant?: Variant } & (
  | ({ href?: undefined } & ButtonHTMLAttributes<HTMLButtonElement>)
  | ({ href: string } & AnchorHTMLAttributes<HTMLAnchorElement>)
);

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white shadow-sm hover:bg-brand-strong active:translate-y-px",
  soft: "bg-sky text-navy border border-brdr hover:bg-brand/10",
  ghost: "bg-surface text-ink border border-brdr hover:bg-sky",
};

export function Button({ variant = "primary", className, children, ...props }: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all",
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/50 disabled:opacity-50 disabled:shadow-none",
    variants[variant],
    className,
  );
  // `children` is passed explicitly rather than through the spread so jsx-a11y can see the
  // anchor has content — it cannot follow a spread, and a link with no discernible text is
  // a genuine screen-reader failure, not a false positive.
  if (props.href !== undefined) {
    return (
      <a className={classes} {...(props as AnchorHTMLAttributes<HTMLAnchorElement>)}>
        {children}
      </a>
    );
  }
  return (
    <button className={classes} {...(props as ButtonHTMLAttributes<HTMLButtonElement>)}>
      {children}
    </button>
  );
}
