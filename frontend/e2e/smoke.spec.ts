import { expect, test } from "@playwright/test";

/**
 * Money-flow smoke: public landing renders, the utility-links board is reachable, and a
 * staff account can sign in through the real API to a working dashboard. (Student login
 * is device-bound — a fresh browser profile would be held for approval by design — so
 * the signed-in path uses faculty; the form/API path is identical.)
 */

test("landing page renders with sign-in entry point", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /sign in/i }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /utility links/i }).first()).toBeVisible();
});

test("public utility-links notice board loads", async ({ page }) => {
  await page.goto("/utility-links");
  await expect(page.getByRole("heading", { name: /notice board|utility links/i })).toBeVisible();
});

test("faculty signs in and reaches their dashboard", async ({ page }) => {
  await page.goto("/login/faculty");
  await page.locator("#login-id").fill("faculty1");
  await page.locator("#password").fill("Demo!passLMS1");
  await page.getByRole("button", { name: /sign in securely/i }).click();

  await page.waitForURL("**/faculty", { timeout: 15_000 });
  // The portal shell renders the role's nav — proof the session + /me round-trip worked.
  await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Content", exact: true })).toBeVisible();
});

test("wrong password is rejected with a friendly error", async ({ page }) => {
  await page.goto("/login/faculty");
  await page.locator("#login-id").fill("faculty1");
  await page.locator("#password").fill("wrong-password");
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await expect(page.getByText(/invalid credentials/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login\/faculty/);
});
