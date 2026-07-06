import { expect, test } from "@playwright/test";

/**
 * Money-flow 1 (DEMO_FLOWS.md Flow 1): admin imports a student by CSV, the student
 * completes the two-step (email OTP -> phone OTP -> password) setup, then signs in.
 */
test("admin imports a student, they complete setup, then sign in", async ({ page }) => {
  const regNumber = `E2E${Date.now()}`;
  const password = "Adv123*Setup";

  await page.goto("/login/admin");
  await page.locator("#login-id").fill("admin1");
  await page.locator("#password").fill("Demo!passLMS1");
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await page.waitForURL((url) => url.pathname === "/admin", { timeout: 15_000 });

  await page.goto("/admin/enrolment");
  const csv =
    "registration_number,name,email,phone,batch,course,faculty\n" +
    `${regNumber},E2E Student,${regNumber.toLowerCase()}@example.com,9876500001,FS-DEMO,FS,faculty1\n`;
  await page.setInputFiles('input[type="file"]', {
    name: "student.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByRole("button", { name: /^validate$/i }).click();
  await expect(page.getByText(/1 row\(s\) valid/i)).toBeVisible();
  await page.getByRole("button", { name: /confirm import/i }).click();
  await expect(page.getByText(/imported 1 student/i)).toBeVisible();

  // Find the new pending row and pull its setup link.
  const row = page.locator("tr", { hasText: regNumber });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /setup link/i }).click();
  const setupLink = row.getByRole("link", { name: /open link/i });
  await expect(setupLink).toBeVisible();
  const href = await setupLink.getAttribute("href");
  expect(href).toBeTruthy();

  // Follow the link and complete the two-step setup using the on-page dev codes.
  await page.goto(href!);
  await expect(page.getByText(/step 1 of 3/i)).toBeVisible();
  const emailCode = await page.getByText(/dev code:/i).textContent();
  await page.getByPlaceholder("6-digit code").fill(emailCode!.replace(/\D/g, ""));
  await page.getByRole("button", { name: /verify email/i }).click();

  await expect(page.getByText(/step 2 of 3/i)).toBeVisible();
  const phoneCode = await page.getByText(/dev code:/i).textContent();
  await page.getByPlaceholder("6-digit code").fill(phoneCode!.replace(/\D/g, ""));
  await page.getByRole("button", { name: /verify phone/i }).click();

  await expect(page.getByText(/step 3 of 3/i)).toBeVisible();
  await page.getByPlaceholder("New password").fill(password);
  await page.getByPlaceholder("Confirm password").fill(password);
  await page.getByRole("button", { name: /activate account/i }).click();
  await expect(page.getByText(/account activated/i)).toBeVisible();

  // Sign in as the newly activated student.
  await page.getByRole("link", { name: /go to sign in/i }).click();
  await page.waitForURL("**/login/student");
  await page.locator("#login-id").fill(regNumber);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /sign in securely/i }).click();
  await page.waitForURL((url) => url.pathname === "/student", { timeout: 15_000 });
  await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
});
