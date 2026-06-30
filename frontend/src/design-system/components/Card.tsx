import type { HTMLAttributes } from "react";

import { cn } from "../utils/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-2xl border border-brdr bg-surface p-5 shadow-card", className)}
      {...props}
    />
  );
}
