import { expect, test } from "@playwright/test";

import { createActiveStudent, dismissEngagementPopup, loginViaApi, loginViaUi } from "./fixtures";

/**
 * Money-flow 5 (DEMO_FLOWS.md Flow 10): admin completes a batch, and a student in it can
 * then enter a Certificate ID to complete certification. Uses a dedicated, brand-new
 * batch/course (never FS-DEMO, which other flows and manual demos share and rely on
 * staying Active).
 */
test("completing a batch lets its student certify", async ({ page, context }) => {
  const stamp = Date.now();
  const courseCode = `E2EC${stamp}`;
  const batchCode = `E2EB${stamp}`;
  const regNumber = `E2ECERT${stamp}`;
  const password = "Adv123*Certify";
  const certificateId = `CERT-${stamp}`;

  // Courses are Super Admin-only under the updated procedure.
  await loginViaUi(page, "superadmin1", "Demo!passLMS1", "super-admin");
  await page.goto("/super-admin/courses");
  await page.getByPlaceholder("Code (e.g. FS)").fill(courseCode);
  await page.getByPlaceholder("Name").fill("E2E Certify Course");
  await page.getByRole("button", { name: /create course/i }).click();
  await expect(page.getByText(courseCode)).toBeVisible();
  await page.request.post("http://localhost:8000/api/v1/auth/logout/");

  // Admin builds the batch from that course.
  await loginViaUi(page, "admin1", "Demo!passLMS1", "admin");
  await page.goto("/admin/batches");
  const today = new Date().toISOString().slice(0, 10);
  await page.getByPlaceholder("Batch ID (e.g. FS-2026A)").fill(batchCode);
  await page.getByPlaceholder("Name").fill("E2E Certify Batch");
  const courseValue = await page
    .locator("select option", { hasText: courseCode })
    .getAttribute("value");
  await page.locator("form select").selectOption(courseValue!);
  await page.locator("#batch-start").fill(today);
  await page.locator("#batch-end").fill(today);
  // Class schedule is now mandatory (req 14).
  await page.getByRole("button", { name: "Mon" }).click();
  await page.locator("#class-from").fill("18:00");
  await page.locator("#class-to").fill("20:00");
  await page.getByRole("button", { name: /create batch/i }).click();
  const row = page.locator("div.flex.flex-wrap.items-center.gap-3.py-3", { hasText: batchCode });
  await expect(row).toBeVisible();

  // Enrol + fully activate a student into this new batch (fixture — Flow 1 covers the UI
  // enrolment journey itself; this test's focus is completion -> certification).
  await loginViaApi(context, "admin1", "Demo!passLMS1");
  await createActiveStudent(context, regNumber, password, batchCode, courseCode, "faculty1");

  // Draft -> Active -> Completed (closes video access as a side effect).
  await row.getByRole("button", { name: /^activate$/i }).click();
  await expect(row.getByRole("button", { name: /^complete$/i })).toBeVisible();
  await row.getByRole("button", { name: /^complete$/i }).click();
  await expect(row.getByText(/^completed$/i)).toBeVisible();

  await page.context().clearCookies();
  await loginViaUi(page, regNumber, password, "student");
  await page.goto("/student/certificate");
  await dismissEngagementPopup(page);
  const certCard = page.locator(
    "div.rounded-2xl.border.border-brdr.bg-surface.p-5.shadow-card",
    { hasText: "E2E Certify Batch" },
  );
  await expect(certCard.getByText(/pending/i)).toBeVisible();
  await certCard.getByPlaceholder(/enter your certificate id/i).fill(certificateId);
  await certCard.getByRole("button", { name: /^submit$/i }).click();
  await expect(certCard.getByText(/certified/i)).toBeVisible();
  await expect(certCard.getByText(certificateId)).toBeVisible();
});
