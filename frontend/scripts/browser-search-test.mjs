/**
 * Authenticated AI search browser test — requires a logged-in Auth0 account.
 *
 * Set env vars (or pass on command line):
 *   AUTH_TEST_EMAIL    — Auth0 test user email
 *   AUTH_TEST_PASSWORD — Auth0 test user password
 *
 * Run: node scripts/browser-search-test.mjs
 * (dev servers must be on :3000 and :8000)
 */
import puppeteer from "puppeteer-core";

const BASE = process.env.SMOKE_BASE_URL ?? "http://localhost:3000";
const CHROME =
  process.env.CHROME_PATH ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const EMAIL = process.env.AUTH_TEST_EMAIL ?? "";
const PASSWORD = process.env.AUTH_TEST_PASSWORD ?? "WhyPolice_Test_2026!";

const QUERIES = [
  "What is 2+2?",
  "What is the capital of France?",
  "Why do cats knead blankets?",
];

const results = [];

function pass(name, detail = "") {
  results.push({ name, ok: true, detail });
  console.log(`✓ ${name}${detail ? ` — ${detail}` : ""}`);
}

function fail(name, detail = "") {
  results.push({ name, ok: false, detail });
  console.error(`✗ ${name}${detail ? ` — ${detail}` : ""}`);
}

async function auth0Login(page) {
  const email = EMAIL || `whypolice.test+${Date.now()}@gmail.com`;
  const password = PASSWORD;

  const authPath = EMAIL
    ? `/auth/login?returnTo=${encodeURIComponent("/search")}`
    : `/auth/login?screen_hint=signup&returnTo=${encodeURIComponent("/search")}`;

  await page.goto(`${BASE}${authPath}`, { waitUntil: "networkidle2", timeout: 60000 });

  // Wait until Auth0 Universal Login is showing (redirect off localhost).
  await page.waitForFunction(
    () => !location.hostname.includes("localhost"),
    { timeout: 60000 },
  );

  // Auth0 may show "Log in" first — switch to sign up if we're creating a user.
  if (!EMAIL) {
    const signupLink = await page.$('a[href*="signup"], button[data-action="sign-up"]');
    if (signupLink) {
      await signupLink.click();
      await new Promise((r) => setTimeout(r, 1000));
    }
  }

  await page.waitForSelector(
    'input[name="username"], input#username, input[name="email"], input[type="email"]',
    { timeout: 60000 },
  );

  const userField =
    (await page.$('input[name="username"]')) ??
    (await page.$("input#username")) ??
    (await page.$('input[name="email"]')) ??
    (await page.$('input[type="email"]'));
  const passField =
    (await page.$('input[name="password"]')) ?? (await page.$("input#password"));

  if (!userField || !passField) {
    fail("Auth0 login", "Could not find username/password fields on Auth0 page");
    return false;
  }

  await userField.click({ clickCount: 3 });
  await userField.type(email, { delay: 15 });
  await passField.type(password, { delay: 15 });

  const submit =
    (await page.$('button[type="submit"][data-action="sign-up"]')) ??
    (await page.$('button[type="submit"]')) ??
    (await page.$('button[name="action"]'));
  if (!submit) {
    fail("Auth0 login", "Could not find submit button on Auth0 page");
    return false;
  }
  await submit.click();

  try {
    await page.waitForFunction(() => location.pathname === "/search", { timeout: 90000 });
    pass("Auth0 auth → /search", EMAIL ? "existing user" : `signed up ${email}`);
    return true;
  } catch {
    const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 300));
    fail("Auth0 auth → /search", `url=${page.url()} snippet=${bodyText}`);
    return false;
  }
}

async function runSearch(page, query) {
  const input = await page.waitForSelector('input[aria-label="Search"]', { timeout: 15000 });
  await input.click({ clickCount: 3 });
  await page.keyboard.press("Backspace");
  await input.type(query, { delay: 15 });
  await page.keyboard.press("Enter");

  const started = Date.now();
  try {
    // "Copy" only appears when status === complete — reliable end-of-stream signal.
    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll("button")).some((b) =>
          (b.textContent ?? "").trim().startsWith("Copy"),
        ),
      { timeout: 120000 },
    );

    const answer = await page.evaluate(() => {
      const panel = document.querySelector("[aria-live='polite'][aria-busy='false']");
      return panel?.textContent?.trim() ?? "";
    });
    const ms = Date.now() - started;
    if (answer.length > 10) {
      pass(`Search: "${query.slice(0, 40)}"`, `${answer.slice(0, 100)}… (${ms}ms)`);
      return true;
    }
    fail(`Search: "${query.slice(0, 40)}"`, "Copy shown but answer text empty");
    return false;
  } catch {
    const errText = await page
      .$eval("[aria-live='polite']", (el) => el.textContent?.trim() ?? "")
      .catch(() => "");
    fail(`Search: "${query.slice(0, 40)}"`, errText || `timeout after ${Date.now() - started}ms`);
    return false;
  }
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  // Health checks
  const health = await page.goto(`${BASE}/`, { waitUntil: "networkidle2", timeout: 60000 });
  if ((health?.status() ?? 0) >= 200 && (health?.status() ?? 0) < 400) {
    pass("Frontend reachable", String(health.status()));
  } else {
    fail("Frontend reachable", `status ${health?.status()}`);
  }

  const loggedIn = await auth0Login(page);
  if (loggedIn) {
    for (const q of QUERIES) {
      await runSearch(page, q);
      await new Promise((r) => setTimeout(r, 1500));
    }
  }

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  if (failed.length) process.exit(1);
} finally {
  await browser.close();
}
