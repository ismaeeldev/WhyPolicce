import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config — replaces this project's earlier ad-hoc
 * Puppeteer scripts (scripts/browser-*.mjs) for the Milestone 1/2
 * re-verification pass. Real browser, real dev servers (already
 * running on 3000/8000), no mocking.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e-report" }]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
