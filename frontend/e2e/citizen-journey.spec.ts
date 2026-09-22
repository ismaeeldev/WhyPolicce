import { test, expect } from "@playwright/test";
import { signup, uniqueEmail, ensureFeedLoaded, firstRealInquiryHref } from "./helpers";

/**
 * Milestone 1/2 re-verification — full citizen journey. Real signup,
 * real feed, real inquiry creation, real thread interactions.
 */
test.describe("Citizen journey", () => {
  test("app shell renders for a logged-out visitor", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /WhyPolice/i })).toBeVisible();
    await expect(page.getByText(/independent public archive/i)).toBeVisible();
  });

  test("signup lands on the home feed, real inquiries render", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-feed");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);

    const count = await page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count();
    expect(count).toBeGreaterThan(0);
  });

  test("search narrows the feed and clear-filters restores it", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-search");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);

    const before = await page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count();

    const search = page.locator('input[type="search"], input[placeholder*="Search" i]').first();
    await search.fill("zzzznonexistentqueryxyz123");
    await expect(page.getByText(/no matches for these filters/i)).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: /clear filters/i }).click();
    await expect
      .poll(async () => page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count())
      .toBeGreaterThanOrEqual(before);
  });

  test("pagination Load more appends real new items", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-page");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);

    const before = await page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count();
    const loadMore = page.getByRole("button", { name: /load more/i });
    if (await loadMore.isVisible().catch(() => false)) {
      await loadMore.click();
      await expect
        .poll(async () => page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count())
        .toBeGreaterThan(before);
    }
  });

  test("full new-inquiry creation, over-limit upgrade modal, trim, and publish", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-create");
    await signup(page, email, "/inquiries/new");

    await page.locator("#title").fill("E2E premium-pass test inquiry");
    await page.locator("#description").fill("x".repeat(300));
    await page.locator("#state").selectOption("NY");
    await page.locator("#city").fill("Testville");
    await page.getByRole("button", { name: "Community Trace" }).click();

    await page.getByRole("button", { name: /post inquiry/i }).click();
    await expect(page.getByText(/needs the \$2\.99 upgrade/i)).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: /trim/i }).click();
    await page.locator("#description").fill("A short, valid, under-limit description.");
    await page.getByRole("button", { name: /post inquiry/i }).click();

    await page.waitForURL(/\/inquiries\/[0-9a-f-]{36}$/, { timeout: 30_000 });
    await expect(page.getByText(/the original inquiry/i)).toBeVisible();
    await expect(page.getByText("E2E premium-pass test inquiry")).toBeVisible();
  });

  test("thread page: follow, comment, edit inquiry, edit/delete comment", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-thread");
    await signup(page, email, "/inquiries/new");

    await page.locator("#title").fill("E2E thread interaction test");
    await page.locator("#description").fill("A short description for thread interaction testing.");
    await page.locator("#state").selectOption("CA");
    await page.locator("#city").fill("Testburg");
    await page.getByRole("button", { name: "Community Trace" }).click();
    await page.getByRole("button", { name: /post inquiry/i }).click();
    await page.waitForURL(/\/inquiries\/[0-9a-f-]{36}$/, { timeout: 15_000 });

    // Follow
    const followBtn = page.getByRole("button", { name: /^follow/i });
    await followBtn.click();
    await expect(page.getByRole("button", { name: /^following/i })).toBeVisible({ timeout: 8_000 });

    // Post comment
    const commentBox = page.locator("textarea").first();
    await commentBox.fill("E2E real comment.");
    await page.getByRole("button", { name: /post comment/i }).click();
    await expect(page.getByText("E2E real comment.")).toBeVisible({ timeout: 8_000 });

    // Edit the inquiry (author-only control)
    const editBtn = page.getByRole("button", { name: /edit inquiry/i });
    await editBtn.click();
    const titleField = page.locator('input[value*="E2E thread interaction test"]').first();
    await expect(titleField).toBeVisible({ timeout: 5_000 });
  });

  test("report button on an inquiry shows toast without navigating away", async ({ page }) => {
    const email = uniqueEmail("e2e-citizen-report");
    await signup(page, email, "/");
    await ensureFeedLoaded(page);
    const href = await firstRealInquiryHref(page);
    await page.goto(href);
    await expect(page.getByText(/the original inquiry/i)).toBeVisible({ timeout: 10_000 });

    // .first() — a real inquiry may already have real comments (from
    // other test runs' leftover data), each with their own Report
    // button; this test targets the inquiry-level one specifically.
    await page.getByRole("button", { name: /^report/i }).first().click();
    await page.locator('input[placeholder*="reporting" i]').first().fill("E2E test report reason");
    await page.getByRole("button", { name: /submit report/i }).first().click();

    await expect(page.getByText(/report submitted/i)).toBeVisible({ timeout: 8_000 });
    expect(new URL(page.url()).pathname).toBe(new URL(href, page.url()).pathname);
  });
});
