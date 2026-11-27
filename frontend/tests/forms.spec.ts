import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test.use({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined });

test("the built bundle initializes formsets and submits a changed filter", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const fixture = await readFile("frontend/tests/forms.html", "utf8");
  const timepicker = await readFile("templates/includes/timepicker.html", "utf8");
  await page.route("https://forms.test/**", async (route) => {
    if (new URL(route.request().url()).pathname === "/site.js") {
      await route.fulfill({ path: "frontend/dist/js/site.js", contentType: "text/javascript" });
    } else {
      await route.fulfill({ contentType: "text/html", body: fixture.replace("</body>", timepicker + "</body>") });
    }
  });
  await page.goto("https://forms.test/");

  await page.locator("#add-premise-btn").click();
  await page.locator("#id_premises-1-room").fill("102");
  await page.locator(".remove-premise-btn").first().click();
  await expect(page.getByLabel("Аудитория")).toHaveValue("102");
  await expect(page.locator("#id_premises-0-room")).toHaveValue("102");
  await expect(page.locator("#id_premises-TOTAL_FORMS")).toHaveValue("1");
  await page.locator(".tp-clock-icon-btn").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.locator("#add-block-btn").click();
  await expect(page.locator('[name="blocks-0-order"]')).toHaveValue("0");
  await expect(page.locator("#id_blocks-TOTAL_FORMS")).toHaveValue("1");

  await page.locator("select").selectOption("open");
  await expect(page).toHaveURL("https://forms.test/filtered?status=open");
  expect(errors).toEqual([]);
});
