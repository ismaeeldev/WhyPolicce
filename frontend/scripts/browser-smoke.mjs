/**
 * Public-route browser smoke test — master guide Steps 2/8 checklist.
 * Run: node scripts/browser-smoke.mjs  (dev server must be on :3000)
 */
import puppeteer from "puppeteer-core";

const BASE = process.env.SMOKE_BASE_URL ?? "http://localhost:3000";
const CHROME =
  process.env.CHROME_PATH ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const PUBLIC_ROUTES = ["/", "/about", "/pricing", "/login", "/signup", "/privacy", "/terms"];

const results = [];

function pass(name, detail = "") {
  results.push({ name, ok: true, detail });
  console.log(`✓ ${name}${detail ? ` — ${detail}` : ""}`);
}

function fail(name, detail = "") {
  results.push({ name, ok: false, detail });
  console.error(`✗ ${name}${detail ? ` — ${detail}` : ""}`);
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  for (const route of PUBLIC_ROUTES) {
    const res = await page.goto(`${BASE}${route}`, { waitUntil: "networkidle2", timeout: 60000 });
    const status = res?.status() ?? 0;
    if (status >= 200 && status < 400) {
      pass(`GET ${route}`, String(status));
    } else {
      fail(`GET ${route}`, `status ${status}`);
    }
  }

  // Protected route redirects to login
  const searchRes = await page.goto(`${BASE}/search`, { waitUntil: "networkidle2" });
  const finalUrl = page.url();
  if (finalUrl.includes("/login") && searchRes?.status() === 200) {
    pass("Protected /search redirects to /login");
  } else {
    fail("Protected /search redirects to /login", finalUrl);
  }

  // Landing search bar + chips
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2" });
  const h1 = await page.$eval("h1", (el) => el.textContent?.trim() ?? "");
  if (h1.includes("Ask why")) pass("Hero headline renders");
  else fail("Hero headline renders", h1);

  await page.waitForSelector('input[aria-label="Search"]');
  const chipHandle = await page.evaluateHandle(() =>
    Array.from(document.querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").includes("Why do cats knead"),
    ),
  );
  const chipEl = chipHandle.asElement();
  if (chipEl) {
    await chipEl.click();
    const inputVal = await page.$eval('input[aria-label="Search"]', (el) => el.value);
    if (inputVal.length > 0) pass("Example chip fills search bar", inputVal.slice(0, 40));
    else fail("Example chip fills search bar", "clicked but input empty");
  } else {
    fail("Example chips present");
  }

  // Theme toggle in nav
  const themeBtn = await page.$('button[aria-label*="mode"]');
  if (themeBtn) pass("Theme toggle present in navbar");
  else fail("Theme toggle present in navbar");

  // Mobile viewport — no horizontal overflow on landing
  await page.setViewport({ width: 375, height: 812 });
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (!overflow) pass("No horizontal scroll at 375px on /");
  else fail("No horizontal scroll at 375px on /");

  // Route progress + navigation
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${BASE}/`, { waitUntil: "networkidle2" });
  await page.click('a[href="/pricing"]');
  await page.waitForFunction(() => location.pathname === "/pricing", { timeout: 15000 });
  pass("Nav / → /pricing works");

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  if (failed.length) process.exit(1);
} finally {
  await browser.close();
}
