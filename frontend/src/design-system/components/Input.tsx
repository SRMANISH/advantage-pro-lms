import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "../utils/cn";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm text-ink",
        "placeholder:text-muted focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
