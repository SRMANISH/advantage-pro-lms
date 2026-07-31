import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import type { Page } from "./api";

/**
 * Server-side pagination + (optional debounced) search for data-dense tables. Replaces the
 * "fetch 100 rows then paginate/search client-side" pattern, which silently hid every row
 * past the first page. Query keys include page/search/params so react-query caches each page
 * and keepPreviousData avoids a flash while the next loads. Changing `search` or `params`
 * (e.g. a batch filter) resets to page 1 so we never request an out-of-range page (DRF 404s
 * on those). Invalidating the base `key` refreshes every cached page after a mutation.
 */
export function useServerTable<T, P extends Page<T> = Page<T>>(opts: {
  key: unknown[];
  fetcher: (params: Record<string, unknown>) => Promise<P>;
  pageSize?: number;
  searchable?: boolean;
  params?: Record<string, string | undefined>;
}) {
  const pageSize = opts.pageSize ?? 25;
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");

  const paramsKey = JSON.stringify(opts.params ?? {});

  // Debounce the search box; reset to page 1 on a new term.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(query.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  // Reset to page 1 whenever a filter param changes.
  useEffect(() => setPage(1), [paramsKey]);

  const extra = Object.fromEntries(Object.entries(opts.params ?? {}).filter(([, v]) => v));

  const result = useQuery({
    queryKey: [...opts.key, page, pageSize, search, paramsKey],
    queryFn: () =>
      opts.fetcher({
        page,
        page_size: pageSize,
        ...(opts.searchable && search ? { search } : {}),
        ...extra,
      }),
    placeholderData: keepPreviousData,
  });

  const total = result.data?.count ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return {
    rows: result.data?.results ?? [],
    // The whole envelope, for endpoints that return a page of rows *plus* whole-dataset
    // context (status counts, a configured window) alongside it.
    data: result.data,
    total,
    page,
    setPage,
    pageCount,
    query,
    setQuery,
    isLoading: result.isLoading,
    isFetching: result.isFetching,
    // Exposed so a page can render a failure distinctly from "no rows" — without these a
    // failed fetch is indistinguishable from an empty table.
    isError: result.isError,
    refetch: result.refetch,
  };
}
