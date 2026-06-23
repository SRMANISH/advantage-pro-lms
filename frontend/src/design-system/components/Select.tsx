import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "../utils/cn";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-brdr bg-surface px-3 text-sm text-ink",
        "focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
        className,
      )}
      {...props}
    />
  ),
);

Select.displayName = "Select";
