import axios from "axios";

// Relative by default — the Vite dev proxy (and same-origin prod) forward to the API.
const baseURL = import.meta.env.VITE_API_URL ?? "/api/v1";

/** Shared API client. Cookies (session) are sent; Django CSRF header is wired for writes. */
export const api = axios.create({
  baseURL,
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
});
