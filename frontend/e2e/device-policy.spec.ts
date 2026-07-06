import { expect, test } from "@playwright/test";

import { createActiveStudent, dismissEngagementPopup, loginViaApi, loginViaUi } from "./fixtures";

/**
 * Money-flow 4 (DEMO_FLOWS.md Flow 9): a student's device binds on first login; signing in
 * from a different device is blocked and raises an approval request; MIS approves it
 * outside class hours, after which that device also works.
 *
 * FingerprintJS is deliberately stable across browser profiles/incognito (that's the whole
 * point of the library), so "open a second browser context" would not reliably produce a
 * different device_id here. Instead we intercept the real login POST and force a specific
 * device_id per attempt — the same technique a real second device's browser would produce
 * a different value for, without depending on this machine's actual fingerprint entropy.
 */
test("device block -> MIS approval -> the new device then works", async ({ page, context }) => {
  const regNumber = `E2EDEV${Date.now()}`;
  const password = "Adv123*Device";

  await loginViaApi(context, "admin1", "Demo!passLMS1");
  await createActiveStudent(context, regNumber, password);
  await page.context().clearCookies(); // drop the admin session before the student logs in

  let forcedDeviceId = "e2e-device-A";
  await page.route("**/api/v1/auth/login/", async (route) => {
    const body = { ...route.request().postDataJSON(), device_id: forcedDeviceId };
    await route.continue({ postData: JSON.stringify(body) });
  });

  // First login (device A) binds the device.
  await loginViaUi(page, regNumber, password, "student");
  await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();

  // Log out, then sign in again from "device B" — must be blocked.
  await page.request.post("http://localhost:8000/api/v1/auth/logout/");
  await page.goto(`/login/student`);
  forcedDeviceId = "e2e-device-B";
  await page.locator("#login-id").fill(regNumber);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await expect(page.getByText(/new device/i)).toBeVisible();

  // MIS approves the pending request (outside any live class).
  await loginViaUi(page, "mis1", "Demo!passLMS1", "mis");
  await page.goto("/mis/devices");
  const row = page.locator("div.flex.items-center.justify-between.py-3", { hasText: regNumber });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /^approve$/i }).click();
  await expect(page.getByText(/device approved/i)).toBeVisible();
  await page.request.post("http://localhost:8000/api/v1/auth/logout/");

  // Device B now works.
  await page.goto("/login/student");
  await page.locator("#login-id").fill(regNumber);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await page.waitForURL((url) => url.pathname === "/student", { timeout: 15_000 });
  await dismissEngagementPopup(page);
  await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
});
