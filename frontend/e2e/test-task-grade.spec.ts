import { expect, test } from "@playwright/test";

import { dismissEngagementPopup, loginViaUi } from "./fixtures";

/**
 * Money-flow 3 (DEMO_FLOWS.md Flow 5): faculty creates an MCQ test, a student takes it and
 * is auto-graded instantly; faculty creates a task, a student submits it, faculty grades
 * it, and the student sees the grade.
 */

async function selectFsDemo(page: import("@playwright/test").Page, selectId: string) {
  const select = page.locator(`#${selectId}`);
  const value = await page.locator(`#${selectId} option`, { hasText: "FS-DEMO" }).getAttribute("value");
  await select.selectOption(value!);
}

test("faculty creates a test, student takes it and is auto-graded", async ({ page }) => {
  const title = `E2E Quiz ${Date.now()}`;

  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/tests");
  await selectFsDemo(page, "tests-batch");
  await page.getByPlaceholder("Test title").fill(title);
  await page.getByPlaceholder("Question text").fill("What is 2 + 2?");
  await page.getByPlaceholder("Choice 1").fill("4");
  await page.getByPlaceholder("Choice 2").fill("5");
  // Choice 1 (index 0) is already marked correct by default.
  await page.getByRole("button", { name: /create test/i }).click();
  await expect(page.getByText(title)).toBeVisible();

  await loginViaUi(page, "S105", "Demo!passLMS1", "student");
  await page.goto("/student/tests");
  await dismissEngagementPopup(page);
  // Each test is one ".flex.items-center.justify-between.py-2" row (the exact class list
  // on that wrapper) — scoping to it (not a bare "div") avoids matching every ancestor
  // that also happens to contain the title text.
  await page
    .locator("div.flex.items-center.justify-between.py-2", { hasText: title })
    .getByRole("button", { name: /^take$/i })
    .click();
  await page.getByText("4", { exact: true }).click();
  await page.getByRole("button", { name: /submit test/i }).click();
  await expect(page.getByText(/your score: 1\/1/i)).toBeVisible();
});

test("faculty creates a task, student submits, faculty grades, student sees the grade", async ({
  page,
}) => {
  const title = `E2E Task ${Date.now()}`;

  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/tasks");
  await selectFsDemo(page, "tasks-batch");
  await page.getByPlaceholder("Title").fill(title);
  await page.getByPlaceholder("Description").fill("Build a small feature.");
  await page.getByRole("button", { name: /create task/i }).click();
  await expect(page.getByText(title)).toBeVisible();

  await loginViaUi(page, "S106", "Demo!passLMS1", "student");
  await page.goto("/student/tasks");
  await dismissEngagementPopup(page);
  // Every <Card> renders this exact base class list — one Card per task, so scoping to
  // it (not a bare "div") avoids matching every ancestor that contains the title text.
  const card = page.locator(
    "div.rounded-2xl.border.border-brdr.bg-surface.p-5.shadow-card",
    { hasText: title },
  );
  await card.getByPlaceholder(/type your answer/i).fill("Here is my submission.");
  await card.getByRole("button", { name: /^submit$/i }).click();
  await expect(card.getByText(/^submitted$/i).first()).toBeVisible();

  await loginViaUi(page, "faculty1", "Demo!passLMS1", "faculty");
  await page.goto("/faculty/tasks");
  await selectFsDemo(page, "tasks-batch");
  await page.getByRole("button", { name: new RegExp(title) }).click();
  // S106's display name is their seeded full name (e.g. "Arjun Menon"), not "S106" —
  // the Score input appearing is the real signal the submission row rendered.
  await expect(page.getByPlaceholder("Score")).toBeVisible();
  await page.getByPlaceholder("Score").fill("9");
  await page.getByPlaceholder("Feedback").fill("Nicely done.");
  await page.getByRole("button", { name: /^grade$/i }).click();
  await expect(page.getByText(/graded/i).first()).toBeVisible();

  await loginViaUi(page, "S106", "Demo!passLMS1", "student");
  await page.goto("/student/tasks");
  await dismissEngagementPopup(page);
  const graded = page.locator(
    "div.rounded-2xl.border.border-brdr.bg-surface.p-5.shadow-card",
    { hasText: title },
  );
  await expect(graded.getByText(/score: 9/i)).toBeVisible();
});
