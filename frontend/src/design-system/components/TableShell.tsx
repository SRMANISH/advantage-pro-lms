import type { ReactNode } from "react";

import { cn } from "../utils/cn";

/** Consistent rounded, bordered, horizontally-scrollable table container. */
export function TableShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-2xl border border-brdr bg-surface shadow-card", className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-brdr bg-sky/50 text-left text-xs uppercase tracking-wide text-muted">
      {children}
    </thead>
  );
}
