import { Page, expect } from "@playwright/test";

export const PASSWORD = "WhyPolice_Test_2026!";

export function uniqueEmail(tag: string): string {
  return `whypolice.test+${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@gmail.com`;
}

/**
 * Real Auth0 signup — same account-creation flow every human user goes
 * through, no mocking. Used across the whole E2E suite so every test
 * gets a genuine, isolated identity.
 */
export async function signup(page: Page, email: string, returnTo: string) {
  const authPath = `/auth/login?screen_hint=signup&returnTo=${encodeURIComponent(returnTo)}`;
  await page.goto(authPath, { waitUntil: "networkidle" });
  await page.waitForURL((url) => !url.hostname.includes("localhost"), { timeout: 60_000 });

  const signupLink = page.locator('a[href*="signup"], button[data-action="sign-up"]').first();
  if (await signupLink.isVisible().catch(() => false)) {
    await signupLink.click();
    await page.waitForTimeout(800);
  }

  const emailField = page.locator('input[name="email"], input[type="email"]').first();
  await emailField.waitFor({ state: "visible", timeout: 60_000 });
  await emailField.click({ clickCount: 3 });
  await emailField.fill(email);

  const passField = page.locator('input[name="password"]').first();
  await passField.fill(PASSWORD);

  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL((url) => url.pathname === returnTo, { timeout: 90_000 });
  await page.waitForTimeout(600);
}

export async function ensureFeedLoaded(page: Page) {
  await expect
    .poll(
      async () => page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").count(),
      { timeout: 40_000, intervals: [500, 1000, 2000] },
    )
    .toBeGreaterThan(0);
  await page.waitForTimeout(500);
}

export async function firstRealInquiryHref(page: Page): Promise<string> {
  const link = page.locator("a[href^='/inquiries/']:not([href='/inquiries/new'])").first();
  const href = await link.getAttribute("href");
  if (!href) throw new Error("No real inquiry link found on feed");
  return href;
}
