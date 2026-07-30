import { Search } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { cn } from "../utils/cn";

/**
 * Client-side search + pagination over an in-memory list (backend pagination lands later;
 * call sites won't change shape when it does). `searchKeys` are the string fields matched.
 */
export function useTableTools<T extends object>(
  rows: T[] | undefined,
  searchKeys: (keyof T)[],
  pageSize = 10,
) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const all = rows ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return all;
    return all.filter((r) =>
      searchKeys.some((k) =>
        String(r[k] ?? "")
          .toLowerCase()
          .includes(q),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount);
  const paged = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);

  return {
    query,
    setQuery: (q: string) => {
      setQuery(q);
      setPage(1);
    },
    page: safePage,
    setPage,
    pageCount,
    total: filtered.length,
    rows: paged,
  };
}

export function TableToolbar({
  query,
  onQuery,
  placeholder = "Search…",
  right,
}: {
  query: string;
  onQuery: (q: string) => void;
  placeholder?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
      <label className="relative block w-full max-w-xs">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className="h-10 w-full rounded-xl border border-brdr bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
        />
      </label>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  );
}

export function Paginator({
  page,
  pageCount,
  onPage,
  total,
  className,
}: {
  page: number;
  pageCount: number;
  onPage: (p: number) => void;
  total?: number;
  className?: string;
}) {
  if (pageCount <= 1) return null;
  return (
    <div className={cn("mt-3 flex items-center justify-between text-sm", className)}>
      <span className="text-xs text-muted">
        Page {page} of {pageCount}
        {total != null && ` · ${total} record(s)`}
      </span>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          className="rounded-lg border border-brdr bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:bg-sky disabled:opacity-40"
        >
          ← Prev
        </button>
        <button
          onClick={() => onPage(page + 1)}
          disabled={page >= pageCount}
          className="rounded-lg border border-brdr bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:bg-sky disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
