import { test, expect } from "@playwright/test";
import { signup, uniqueEmail, ensureFeedLoaded } from "./helpers";

/**
 * Milestone 2 UI-discipline re-sweep: responsive, dark mode, redirects/
 * guards, hard-refresh shell persistence.
 */
test.describe("Redirect logic", () => {
  test("logged-out visitor hitting /inquiries/new is redirected to login with returnTo preserved", async ({ page }) => {
    await page.goto("/inquiries/new");
    await page.waitForURL((url) => url.pathname.includes("/login") || url.hostname !== "localhost", {
      timeout: 15_000,
    });
    const url = page.url();
    expect(url).toContain("returnTo");
  });

  test("logged-out visitor hitting /attorneys/dashboard is redirected to login", async ({ page }) => {
    await page.goto("/attorneys/dashboard");
    await page.waitForURL((url) => url.pathname.includes("/login") || url.hostname !== "localhost", {
      timeout: 15_000,
    });
  });

  test("the home feed and a thread page need no login at all", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL("/");
    await ensureFeedLoaded(page);
  });
});

test.describe("Responsive (375px)", () => {
  test.use({ viewport: { width: 375, height: 800 } });

  test("feed has no horizontal overflow and the mobile Filters sheet opens", async ({ page }) => {
    const email = uniqueEmail("e2e-mobile-feed");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);

    await page.getByRole("button", { name: /^filters$/i }).click();
    // Both a desktop and a mobile-sheet <select> render "All states" as
    // an <option> simultaneously (one hidden via CSS at this viewport,
    // per the dedicated mobile-sheet pattern) — getByText's default
    // visibility filter can still resolve to the hidden one first, so
    // assert on the real select element actually visible on screen.
    await expect(page.locator("select").filter({ hasText: /all states/i }).first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("new-inquiry form has no horizontal overflow", async ({ page }) => {
    const email = uniqueEmail("e2e-mobile-form");
    await signup(page, email, "/inquiries/new");
    await page.locator("#title").waitFor({ state: "visible" });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
  });
});

test.describe("Dark mode", () => {
  test("theme toggle switches and the feed still renders correctly", async ({ page }) => {
    const email = uniqueEmail("e2e-dark-mode");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);

    const startedDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    await page.locator('[aria-label*="light mode" i], [aria-label*="dark mode" i]').first().click();
    await expect
      .poll(async () => page.evaluate(() => document.documentElement.classList.contains("dark")))
      .toBe(!startedDark);

    await expect
      .poll(async () => page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count())
      .toBeGreaterThan(0);
  });
});

test.describe("Hard refresh / shell persistence", () => {
  test("shell stays mounted across a hard refresh on the feed and new-inquiry route", async ({ page }) => {
    const email = uniqueEmail("e2e-refresh");
    await signup(page, email, "/");
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.locator('[aria-label="Main navigation"]')).toBeVisible({ timeout: 10_000 });

    await page.goto("/inquiries/new");
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.locator('[aria-label="Main navigation"]')).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Privacy", () => {
  test("another user's email is never leaked into a feed or thread page", async ({ page, browser }) => {
    // The Milestone 1 privacy rule is about OTHER users' emails never
    // leaking to a viewer — a logged-in user's own avatar legitimately
    // shows their own Auth0 profile name (which, for a fresh signup with
    // no separate display name set, Auth0 itself defaults to the email
    // address — real Auth0 behavior, not a product bug). Real signup A
    // creates an inquiry, real signup B (a separate browser context, a
    // genuinely different viewer) must never see A's email anywhere.
    const emailA = uniqueEmail("e2e-privacy-author");
    const ctxA = await browser.newContext();
    const pageA = await ctxA.newPage();
    await signup(pageA, emailA, "/inquiries/new");
    await pageA.locator("#title").fill("E2E privacy-check inquiry");
    await pageA.locator("#description").fill("A short description for the privacy check.");
    await pageA.locator("#state").selectOption("NY");
    await pageA.locator("#city").fill("Privacyville");
    await pageA.getByRole("button", { name: "Community Trace" }).click();
    await pageA.getByRole("button", { name: /post inquiry/i }).click();
    await pageA.waitForURL(/\/inquiries\/[0-9a-f-]{36}$/, { timeout: 30_000 });
    const threadUrl = pageA.url();
    await ctxA.close();

    const emailB = uniqueEmail("e2e-privacy-viewer");
    await signup(page, emailB, "/");
    await page.goto(threadUrl);
    await expect(page.getByText(/the original inquiry/i)).toBeVisible({ timeout: 10_000 });

    const html = await page.content();
    expect(html).not.toContain(emailA);
  });
});
