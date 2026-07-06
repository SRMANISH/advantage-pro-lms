import { defineConfig, devices } from "@playwright/test";

/**
 * E2E suite against the real dev servers (Django API + Vite SPA).
 *
 * `npm run e2e` boots both servers automatically (or reuses ones you already have
 * running) against the dev database — the same seed_demo accounts as DEMO_GUIDE.md.
 * workers: 1 — specs mutate shared dev data (FS-DEMO doubts/tests/tasks); running them
 * one at a time keeps the suite deterministic against that single shared database.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: ".venv\\Scripts\\python.exe manage.py runserver 8000 --noreload",
      cwd: "../backend",
      url: "http://localhost:8000/api/v1/health/",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
