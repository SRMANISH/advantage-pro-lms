import { expect, test } from "@playwright/test";

import { dismissEngagementPopup, loginViaUi } from "./fixtures";

/**
 * Money-flow 2 (DEMO_FLOWS.md Flow 3): a student asks a doubt, faculty replies (status ->
 * answered), then either side resolves it (status -> resolved).
 */
test("doubt lifecycle: student asks, faculty replies, then resolves", async ({ page }) => {
  const title = `E2E doubt ${Date.now()}`;

  await loginViaUi(page, "S102", "Demo!passLMS1", "student");
  await page.goto("/student/forum");
  await dismissEngagementPopup(page);
  const fsDemoValue = await page
    .locator("select option", { hasText: "FS-DEMO" })
    .getAttribute("value");
  await page.locator("select").selectOption(fsDemoValue!);
  await page.getByPlaceholder("Title").fill(title);
  await page.locator("textarea").first().fill("How does this feature work?");
  await page.getByRole("button", { name: /post doubt/i }).click();

  // Reopen the new thread and confirm it starts "open".
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await expect(page.getByText(/^open$/i)).toBeVisible();
  await page.getByRole("button", { name: /← back/i }).click();

  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/forum");
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await page.locator("textarea").fill("Here's the answer to your doubt.");
  await page.getByRole("button", { name: /^reply$/i }).click();
  await expect(page.getByText(/^answered$/i)).toBeVisible();

  await page.getByRole("button", { name: /mark resolved/i }).click();
  await expect(page.getByText(/^resolved$/i)).toBeVisible();
});
