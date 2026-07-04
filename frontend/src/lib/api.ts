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
