import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";

const API = "http://localhost:8000/api/v1";

/** Read the CSRF cookie Django set on this context, for the X-CSRFToken header. */
async function csrfToken(context: BrowserContext): Promise<string> {
  const cookies = await context.cookies();
  return cookies.find((c) => c.name === "csrftoken")?.value ?? "";
}

/**
 * Students may get a post-login/course-end LinkedIn/Google-review/next-plan engagement
 * popup. It's mounted fresh on every full page load (each page wraps its own
 * PortalLayout), so it can reappear after any page.goto — dismiss ("Later") it before
 * interacting with the page underneath. A short wait (not an instant check) is needed
 * since the popup's own status query hasn't resolved yet immediately after navigation.
 */
export async function dismissEngagementPopup(page: Page): Promise<void> {
  // Two student popups can stack: the engagement (LinkedIn) overlay renders ABOVE the
  // Phase-3b "Quick welcome check" and intercepts its clicks. Clear whichever is on top
  // each round until neither remains: "Later" dismisses engagement; Yes/Yes/Submit
  // answers the welcome check so it never returns for that student.
  for (let round = 0; round < 4; round++) {
    const later = page.getByRole("button", { name: "Later" });
    const welcome = page.getByRole("heading", { name: "Quick welcome check" });
    if (round === 0) {
      // The popups' own status queries need a moment to resolve after navigation.
      await Promise.race([
        later.waitFor({ state: "visible", timeout: 2_500 }),
        welcome.waitFor({ state: "visible", timeout: 2_500 }),
      ]).catch(() => undefined);
    }
    if (await later.isVisible().catch(() => false)) {
      await later.click();
      continue;
    }
    if (await welcome.isVisible().catch(() => false)) {
      const yes = page.getByRole("button", { name: "Yes", exact: true });
      await yes.nth(0).click();
      await yes.nth(1).click();
      await page.getByRole("button", { name: "Submit", exact: true }).click();
      await welcome.waitFor({ state: "hidden", timeout: 5_000 }).catch(() => undefined);
      continue;
    }
    break;
  }
}

/** Sign in through the real login form and land on the role's portal. */
export async function loginViaUi(
  page: Page,
  username: string,
  password: string,
  slug: string,
): Promise<void> {
  await page.goto(`/login/${slug}`);
  await page.locator("#login-id").fill(username);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await page.waitForURL((url) => url.pathname === `/${slug}`, { timeout: 15_000 });
  await dismissEngagementPopup(page);
}

/** Prime the CSRF cookie, then log in — mirrors the SPA's own auth.csrf()+login() calls. */
export async function loginViaApi(
  context: BrowserContext,
  username: string,
  password: string,
  role?: string,
): Promise<APIRequestContext> {
  const request = context.request;
  await request.get(`${API}/auth/csrf/`);
  const token = await csrfToken(context);
  const resp = await request.post(`${API}/auth/login/`, {
    headers: { "X-CSRFToken": token },
    data: { username, password, ...(role ? { role } : {}) },
  });
  if (!resp.ok()) {
    throw new Error(`login failed for ${username}: ${resp.status()} ${await resp.text()}`);
  }
  return request;
}

async function post(context: BrowserContext, path: string, data: unknown) {
  const token = await csrfToken(context);
  const resp = await context.request.post(`${API}${path}`, {
    headers: { "X-CSRFToken": token },
    data,
  });
  return resp;
}

async function multipart(context: BrowserContext, path: string, form: Record<string, string>) {
  const token = await csrfToken(context);
  return context.request.post(`${API}${path}`, {
    headers: { "X-CSRFToken": token },
    multipart: form,
  });
}

/**
 * Fixture helper: import one new student via the real import endpoint, then drive the
 * same two-step (email OTP -> phone OTP -> password) setup the UI uses, reading the
 * dev_code the backend returns in DEBUG mode at each step. Requires an admin/MIS session
 * already established on `context` (see loginViaApi). Returns the new username.
 */
export async function createActiveStudent(
  context: BrowserContext,
  registrationNumber: string,
  password: string,
  batchCode = "FS-DEMO",
  courseCode = "FS",
  facultyUsername = "faculty1",
): Promise<string> {
  const csv =
    "registration_number,name,email,phone,batch,course,faculty\n" +
    `${registrationNumber},E2E Student,${registrationNumber.toLowerCase()}@example.com,` +
    `9${Date.now().toString().slice(-9)},${batchCode},${courseCode},${facultyUsername}\n`;

  const imported = await multipart(context, "/enrollments/import/", {
    file: { name: "student.csv", mimeType: "text/csv", buffer: Buffer.from(csv) },
    dry_run: "false",
  });
  if (!imported.ok()) {
    throw new Error(`import failed: ${imported.status()} ${await imported.text()}`);
  }

  // Find the batch id, then the new enrolment row, to resend (== "Setup link") its token.
  // (/batches/ — the admin endpoint; the forum batch picker is no longer admin-visible.)
  const batches = await context.request.get(`${API}/batches/`);
  const batchData = await batches.json();
  const batchList = Array.isArray(batchData) ? batchData : batchData.results;
  const targetBatch = batchList.find((b: { code: string }) => b.code === batchCode);
  const roster = await context.request.get(
    `${API}/enrollments/?batch=${targetBatch.id}&page_size=200`,
  );
  const rows = await roster.json();
  const list = Array.isArray(rows) ? rows : rows.results;
  const row = list.find(
    (r: { registration_number: string }) => r.registration_number === registrationNumber,
  );
  if (!row) throw new Error(`imported student ${registrationNumber} not found in roster`);

  const resend = await post(context, "/auth/setup/resend/", { student_id: row.student });
  const { url } = await resend.json();
  const token = new URL(url).pathname.split("/").pop();

  const start = await post(context, "/auth/setup/start/", { token });
  const emailCode = (await start.json()).dev_code;
  const verifyEmail = await post(context, "/auth/setup/verify-email/", { token, code: emailCode });
  const phoneCode = (await verifyEmail.json()).dev_code;
  await post(context, "/auth/setup/verify-phone/", { token, code: phoneCode });
  const complete = await post(context, "/auth/setup/complete/", { token, password });
  if (!complete.ok()) {
    throw new Error(`setup complete failed: ${complete.status()} ${await complete.text()}`);
  }
  return registrationNumber;
}
