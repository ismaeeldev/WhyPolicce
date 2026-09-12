import puppeteer from "puppeteer-core";
import { mkdir } from "node:fs/promises";
await mkdir(".ui-review", { recursive: true });
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH ?? "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1000 });
  for (const [name, url] of [["reference", "https://why.com"], ["home", "http://localhost:3000"]]) {
    try {
      await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
      await page.screenshot({ path: `.ui-review/${name}.png`, fullPage: true });
      console.log(name, await page.title());
    } catch (error) { console.log(name, error.message); }
  }
} finally { await browser.close(); }
