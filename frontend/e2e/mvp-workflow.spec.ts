import { expect, test } from "@playwright/test";

test("completes, exports, reviews and deletes the grounded MVP workflow", async ({ page }) => {
  const runId = String(Date.now());
  const company = `Acme Portfolio Labs ${runId}`;
  await page.goto("/");

  await page.getByLabel("Full name").fill(`Ada Portfolio ${runId}`);
  await page.getByLabel("Professional headline").fill("Backend Engineer");
  await page.getByLabel("Location", { exact: true }).fill("Madrid");
  await page.getByLabel("Preferred roles").fill("Backend Engineer");
  await page.getByLabel("Professional summary").fill("Builds reliable Python services.");
  await page.getByLabel("Latest employer").fill("Analytical Engines");
  await page.getByLabel("Role at employer").fill("Software Engineer");
  await page.getByLabel("Experience description").fill("Designed reliable Python APIs with Docker.");
  await page.getByLabel("Skills").fill("Python | programming_language | 36\nDocker | devops | 12");
  await page.getByLabel("Languages").fill("English | fluent");
  await page.getByRole("button", { name: "Save master profile" }).click();
  await expect(page.getByText("Master profile saved with explicit source facts.")).toBeVisible();

  const offer = [
    company,
    "Backend Engineer",
    "Madrid",
    "Python is required for this role.",
    "Docker is preferred.",
  ].join("\n");
  await page.getByLabel("Original job offer").fill(offer);
  await page.getByLabel("Exact job title").fill("Backend Engineer");
  await page.getByLabel("Exact company").fill(company);
  await page.getByLabel("Exact location").fill("Madrid");
  await page.getByLabel("Requirements to compare").fill(
    "required | skill | Python\npreferred | skill | Docker",
  );
  await page.getByRole("button", { name: "Import grounded offer" }).click();
  await expect(page.getByText("Offer imported with exact source evidence.")).toBeVisible();

  await page.getByRole("button", { name: "Calculate match" }).click();
  await expect(page.getByText("Explainable assessment created.")).toBeVisible();
  await expect(page.getByText("100%", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Generate grounded resume" }).first().click();
  await expect(page.getByText("Grounded draft generated and ready for review.")).toBeVisible();
  await expect(page.getByText("needs review", { exact: true })).toBeVisible();
  await expect(
    page.locator(".resume-review article > p").filter({ hasText: "Designed reliable Python APIs with Docker." }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: "Approve draft" }).click();
  await expect(page.getByText("approved", { exact: true })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export workspace" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^jobhunter-export-\d{4}-\d{2}-\d{2}\.json$/);

  await page.getByRole("button", { name: "Delete workspace" }).click();
  await page.getByRole("button", { name: "Confirm deletion" }).click();
  await expect(page.getByText("Workspace data deleted.")).toBeVisible();
  await expect(page.getByLabel("Full name")).toBeVisible();
});
