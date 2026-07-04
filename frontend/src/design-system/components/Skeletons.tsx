import { Skeleton } from "./Skeleton";

/** Placeholder for a TableShell while rows load. */
export function TableSkeleton({ rows = 6, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-brdr bg-surface shadow-card">
      <div className="border-b border-brdr bg-sky/50 px-4 py-3">
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="divide-y divide-brdr">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="grid gap-4 px-4 py-3" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Placeholder for a card list while items load. */
export function ListSkeleton({ items = 4 }: { items?: number }) {
  return (
    <div className="grid gap-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-brdr bg-surface p-5 shadow-card">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="mt-3 h-3 w-2/3" />
          <Skeleton className="mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}
