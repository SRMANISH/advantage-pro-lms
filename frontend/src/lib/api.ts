import axios from "axios";

import { toast } from "../design-system/components/Toast";

// Relative by default — the Vite dev proxy (and same-origin prod) forward to the API.
const baseURL = import.meta.env.VITE_API_URL ?? "/api/v1";

/** Shared API client. Cookies (session) are sent; Django CSRF header is wired for writes. */
export const api = axios.create({
  baseURL,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});

/**
 * Fail loudly when the API returns HTML instead of JSON.
 *
 * This is always a routing or proxy misconfiguration — a static host serving index.html for
 * an /api path, a rewrite that is not applied, a login page from some gateway. Without this
 * guard the HTML flows into the app as a plain string and surfaces far away as
 * "n.map is not a function" in whichever component happened to expect a list, which says
 * nothing about the real cause. Caught here it names itself.
 */
api.interceptors.response.use((response) => {
  const type = String(response.headers?.["content-type"] ?? "");
  if (type.includes("text/html")) {
    throw new Error(
      "The API returned an HTML page instead of data. The /api proxy is probably not " +
        "configured — check the deployment's rewrite rules.",
    );
  }
  return response;
});

/** A DRF page envelope: `{ count, next, previous, results }`. */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Accept either a plain array or a DRF paginated envelope and return the array. */
export function unwrap<T>(data: T[] | Paginated<T>): T[] {
  return Array.isArray(data) ? data : data.results;
}

export interface Page<T> {
  results: T[];
  count: number;
}

/** Fetch one server page, tolerating either an array or a DRF envelope. Used with
 * useServerTable to drive real server-side pagination (no silent client truncation). */
export async function fetchPage<T>(
  url: string,
  params: Record<string, unknown> = {},
): Promise<Page<T>> {
  const { data } = await api.get<Paginated<T> | T[]>(url, { params });
  if (Array.isArray(data)) return { results: data, count: data.length };
  return { results: data.results, count: data.count };
}

// Global mutation-error surface: any failed write pops an error toast with the server's
// detail. GETs and the auth flows (which render errors inline) are excluded.
const QUIET = ["/auth/login/", "/auth/password/", "/auth/setup/"];
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const config = error?.config ?? {};
    const method = (config.method ?? "get").toLowerCase();
    const url: string = config.url ?? "";
    if (method !== "get" && !QUIET.some((q) => url.includes(q))) {
      const data = error?.response?.data;
      const detail =
        (typeof data?.detail === "string" && data.detail) ||
        (Array.isArray(data) && typeof data[0] === "string" && data[0]) ||
        "Something went wrong — please try again.";
      toast(detail, "error");
    }
    return Promise.reject(error);
  },
);
