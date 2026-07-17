import { expect, test, type Page } from "@playwright/test";

import { dismissEngagementPopup, loginViaUi } from "./fixtures";

/** E2E coverage for the Procedure-v2 features the money-flow specs didn't touch:
 * student->management feedback (req 20) and the Colab test kind (req 3). */

async function selectFsDemo(page: Page, selectId: string) {
  const value = await page
    .locator(`#${selectId} option`, { hasText: "FS-DEMO" })
    .getAttribute("value");
  await page.locator(`#${selectId}`).selectOption(value!);
}

test("student feedback reaches the Super Admin inbox (req 20)", async ({ page }) => {
  const subject = `E2E Feedback ${Date.now()}`;

  await loginViaUi(page, "S105", "Demo!passLMS1", "student");
  await page.goto("/student/feedback");
  await dismissEngagementPopup(page);
  await page.locator("#fb-subject").fill(subject);
  await page.locator("#fb-message").fill("Please review the class timings.");
  await page.getByRole("button", { name: /send to management/i }).click();
  await expect(page.getByText(/sent privately to management/i)).toBeVisible();

  // Only the Super Admin can see it — it shows in their private inbox.
  await loginViaUi(page, "superadmin1", "Demo!passLMS1", "super-admin");
  await page.goto("/super-admin/feedback");
  await expect(page.getByText(subject)).toBeVisible();
});

test("Colab test: student submits a link, faculty grades it (req 3)", async ({ page }) => {
  const title = `E2E Colab ${Date.now()}`;

  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/tests");
  await selectFsDemo(page, "tests-batch");
  await page.getByPlaceholder("Test title").fill(title);
  await page.locator("#test-kind").selectOption("colab");
  await page.getByRole("button", { name: /create test/i }).click();
  await expect(page.getByText(title)).toBeVisible();

  // Student submits their Colab link.
  await loginViaUi(page, "S107", "Demo!passLMS1", "student");
  await page.goto("/student/tests");
  await dismissEngagementPopup(page);
  await page
    .locator("div.flex.items-center.justify-between.gap-2.py-2", { hasText: title })
    .getByRole("button", { name: /^submit$/i })
    .click();
  await page.locator("#take-link").fill("https://colab.research.google.com/drive/e2e");
  await page.getByRole("button", { name: /^submit$/i }).click();
  await expect(page.getByText(/faculty will grade it soon/i)).toBeVisible();

  // Faculty opens the grade panel and scores it.
  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/tests");
  await selectFsDemo(page, "tests-batch");
  await page
    .locator("div.flex.items-center.justify-between.gap-2.py-2", { hasText: title })
    .getByRole("button", { name: /^grade$/i })
    .click();
  await page.locator('input[type="number"]').first().fill("80");
  await page.getByRole("button", { name: /save grade/i }).click();
  await expect(page.getByText(/graded 80/i).first()).toBeVisible();
});
