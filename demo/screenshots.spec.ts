/**
 * Wiki Screenshot Automation
 *
 * Captures fresh screenshots for all wiki pages.
 * Saves directly to the wiki images directory.
 *
 * Prerequisites:
 *   1. Platform running: docker compose up -d (or local uvicorn)
 *   2. Seed data loaded: uv run python scripts/seed_demo.py --load-fixture
 *   3. Run: cd demo && npm run screenshots:headed
 *
 * Note: Must run headed (not headless) because the memory graph uses
 * WebGL via reagraph/Three.js which requires GPU rendering.
 */

import { test, expect, type Page } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WIKI_IMAGES = path.resolve(__dirname, "../../Colloquip.wiki/images");

async function pause(page: Page, ms: number) {
  await page.waitForTimeout(ms);
}

async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(WIKI_IMAGES, `${name}.png`),
    fullPage: false,
    animations: "disabled",
  });
}

test("Capture all wiki screenshots", async ({ page }) => {
  test.setTimeout(120_000);

  // ── Home / Communities ──────────────────────────────────────────────
  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible({
    timeout: 15_000,
  });
  await pause(page, 1500);
  await screenshot(page, "home-communities");

  // ── Community Detail ────────────────────────────────────────────────
  const neuroLink = page
    .locator("a", { hasText: "Neuropharmacology" })
    .first();
  await neuroLink.click();
  await page.waitForURL(/\/c\/neuropharmacology/);
  await pause(page, 1200);

  // Click Threads tab to show thread list
  const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTab.isVisible().catch(() => false)) {
    await threadsTab.click();
    await pause(page, 800);
  }
  await screenshot(page, "community-detail");

  // ── Thread / Deliberation ───────────────────────────────────────────
  const firstThread = page.locator("a[href*='/thread/']").first();
  if (await firstThread.isVisible().catch(() => false)) {
    await firstThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2000);

    // Scroll to show some posts + right panel
    const post = page
      .locator(
        '[style*="border-left-width: 3px"], [style*="border-left: 3px"]',
      )
      .nth(2);
    if (await post.isVisible().catch(() => false)) {
      await post.scrollIntoViewIfNeeded();
      await pause(page, 500);
    }

    // Scroll back to top for a clean shot showing the full layout
    await page.evaluate(() => window.scrollTo(0, 0));
    await pause(page, 500);
    await screenshot(page, "thread-deliberation");
  }

  // ── Agent List ──────────────────────────────────────────────────────
  await page.goto("/agents");
  await page
    .waitForSelector('[class*="grid"] a', { timeout: 10_000 })
    .catch(() => {});
  await pause(page, 1500);
  await screenshot(page, "agent-list");

  // ── Agent Detail ────────────────────────────────────────────────────
  const firstAgent = page.locator("a[href*='/agents/']").first();
  if (await firstAgent.isVisible().catch(() => false)) {
    await firstAgent.click();
    await page.waitForURL(/\/agents\//);
    await pause(page, 1500);
    await screenshot(page, "agent-detail");
  }

  // ── Memories: Grid View ─────────────────────────────────────────────
  await page.goto("/memories");
  await pause(page, 2000);
  await screenshot(page, "memory-grid");

  // ── Memories: Graph View ────────────────────────────────────────────
  // Reagraph uses WebGL (Three.js) — needs headed mode for GPU rendering.
  const graphTab = page.locator('[role="tab"]', { hasText: "Graph" });
  if (await graphTab.isVisible().catch(() => false)) {
    await graphTab.click();
    // Give reagraph time to initialize WebGL context and lay out nodes
    await pause(page, 5000);
    await screenshot(page, "memory-graph");

    // Interact with graph: click a node to show detail panel
    const graphCanvas = page.locator("canvas").first();
    if (await graphCanvas.isVisible().catch(() => false)) {
      const box = await graphCanvas.boundingBox();
      if (box) {
        // Click near center to select a node
        await page.mouse.click(
          box.x + box.width * 0.45,
          box.y + box.height * 0.45,
        );
        await pause(page, 2000);
        await screenshot(page, "memory-graph-detail");

        // Try clicking slightly off-center for another node
        await page.mouse.click(
          box.x + box.width * 0.65,
          box.y + box.height * 0.35,
        );
        await pause(page, 2000);
        await screenshot(page, "memory-graph-node");
      }
    }
  }

  // ── Settings ────────────────────────────────────────────────────────
  await page.goto("/settings");
  await pause(page, 1500);
  await screenshot(page, "settings-page");
});
