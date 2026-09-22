import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { signup, uniqueEmail } from "./helpers";

function approveAttorney(barNo: string) {
  execFileSync(
    "D:\\WEB DEV\\WhyPolice\\backend\\venv\\Scripts\\python.exe",
    [
      "-c",
      `from sqlalchemy import create_engine, text\n` +
        `from app.core.config import settings\n` +
        `engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 15})\n` +
        `conn = engine.connect()\n` +
        `conn.execute(text("UPDATE users SET verification_status = 'approved' WHERE verified_bar_no = :bar"), {"bar": ${JSON.stringify(barNo)}})\n` +
        `conn.commit()\n`,
    ],
    { cwd: "D:\\WEB DEV\\WhyPolice\\backend", encoding: "utf-8" },
  );
}

/**
 * Milestone 1/2 re-verification — full attorney journey. No
 * ADMIN_AUTH0_SUBS is configured in this dev environment, so attorney
 * approval uses the same direct-DB-update pattern already
 * user-approved earlier in this project's own testing history (M2.4's
 * Final Testing gate) — equivalent to what the real admin endpoint
 * would do, just without a real admin identity available locally.
 */
test.describe("Attorney journey", () => {
  test("signup, apply, pending state, approval, portal access", async ({ page }) => {
    const email = uniqueEmail("e2e-attorney");
    const barNo = `E2E${Date.now()}`;
    await signup(page, email, "/account");

    await expect(page.getByRole("button", { name: /become an attorney/i })).toBeVisible({ timeout: 10_000 });
    await page.getByRole("button", { name: /become an attorney/i }).click();

    await page.locator("#bar-no").fill(barNo);
    await page.locator("#jurisdiction").fill("New York");
    await page.getByRole("button", { name: /^submit$/i }).click();
    await expect(page.getByText(/pending review/i)).toBeVisible({ timeout: 25_000 });

    // Pending attorney visiting the portal sees the pending banner, not the real portal.
    await page.goto("/attorneys/dashboard");
    await expect(page.getByText(/pending/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/subscribe to see real cases/i)).not.toBeVisible();

    approveAttorney(barNo);

    await page.goto("/attorneys/dashboard");
    await expect(page.getByText("Attorney Portal")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/pending review/i)).not.toBeVisible();

    // Real paywall: an approved-but-unsubscribed attorney sees the
    // blurred preview + subscribe CTA, not the raw real feed.
    await expect(page.getByText(/subscribe to see real cases/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /subscribe for \$149/i })).toBeVisible();
  });

  test("citizen visiting the attorney portal sees a real explanatory page, not a raw 403/404", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-portal-guard");
    await signup(page, email, "/attorneys/dashboard");
    await expect(page.getByText(/this is the attorney portal/i)).toBeVisible({ timeout: 20_000 });
  });
});
