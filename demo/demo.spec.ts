/**
 * Colloquip Demo Script — 3-minute competition video
 *
 * Story arc:
 *   Act 1 (0:00–0:30)  — Platform overview: home, agents, settings init
 *   Act 2 (0:30–1:00)  — Create a community & thread
 *   Act 3 (1:00–2:20)  — Launch deliberation, watch agents debate in real-time
 *   Act 4 (2:20–2:40)  — Human intervention mid-deliberation
 *   Act 5 (2:40–3:00)  — Consensus reveal & wrap-up
 *
 * Prerequisites:
 *   1. Backend running: uv run uvicorn colloquip.api:create_app --factory --port 8000
 *   2. Frontend running: cd web && npm run dev
 *   3. Run: cd demo && npx playwright test --headed
 *
 * The video is saved to demo/test-results/
 */

import { test, expect, type Page } from "@playwright/test";

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Pause long enough for the viewer to read the current screen */
async function pause(page: Page, ms = 1500) {
  await page.waitForTimeout(ms);
}

/** Slowly type text character-by-character for visual effect */
async function typeSlowly(page: Page, selector: string, text: string) {
  await page.click(selector);
  await page.type(selector, text, { delay: 40 });
}

/** Wait for an element to appear and scroll it into view */
async function waitAndScroll(page: Page, selector: string, timeout = 10_000) {
  const el = page.locator(selector).first();
  await el.waitFor({ state: "visible", timeout });
  await el.scrollIntoViewIfNeeded();
  return el;
}

// ─── The Demo ───────────────────────────────────────────────────────────────

test("Colloquip Competition Demo", async ({ page }) => {
  test.setTimeout(180_000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — Platform Overview (~30 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // -- Home page: show the empty state --
  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquip")).toBeVisible();
  await pause(page, 2000);

  // -- Initialize the platform (loads agents + default communities) --
  await page.goto("/settings");
  await expect(page.locator("text=Settings")).toBeVisible();
  await pause(page, 1000);

  // Click "Initialize Platform"
  const initButton = page.locator("button", {
    hasText: "Initialize Platform",
  });
  await initButton.click();

  // Wait for success message
  await expect(
    page.locator("text=Platform initialized successfully")
  ).toBeVisible({ timeout: 15_000 });
  await pause(page, 1500);

  // -- Browse agent pool --
  await page.goto("/agents");
  await expect(page.locator("text=Agent Pool")).toBeVisible();
  // Wait for agents to load
  await page.waitForSelector('[class*="grid"] a, [class*="grid"] [class*="AgentCard"]', {
    timeout: 10_000,
  });
  await pause(page, 2500);

  // -- Home page: now populated with communities --
  await page.goto("/");
  await page.waitForSelector('a[href*="/c/"]', { timeout: 10_000 });
  await pause(page, 2000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — Community Deep Dive & Thread Creation (~30 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // -- Click into the first community --
  const communityLink = page.locator('a[href*="/c/"]').first();
  const communityHref = await communityLink.getAttribute("href");
  await communityLink.click();

  // Wait for community page to load
  await page.waitForSelector('[data-radix-collection-item], [role="tab"]', {
    timeout: 10_000,
  });
  await pause(page, 2000);

  // -- Show the Members tab briefly --
  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible()) {
    await membersTab.click();
    await pause(page, 2000);
  }

  // -- Switch back to Threads tab --
  const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTab.isVisible()) {
    await threadsTab.click();
    await pause(page, 1000);
  }

  // -- Open "New Thread" dialog --
  const newThreadBtn = page.locator("button", { hasText: /New Thread|Create First Thread/ });
  await newThreadBtn.click();

  // Wait for dialog
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 800);

  // Fill in the form
  await typeSlowly(
    page,
    'input[placeholder="Deliberation title"]',
    "GLP-1 Agonists for Alzheimer's Disease"
  );
  await pause(page, 500);

  await typeSlowly(
    page,
    'textarea[placeholder*="hypothesis"]',
    "Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's disease is a viable therapeutic strategy, given emerging evidence of neuroinflammatory pathway modulation and improved cognitive outcomes in diabetic cohorts."
  );
  await pause(page, 1000);

  // Submit
  const startBtn = page.locator('[role="dialog"] button[type="submit"]');
  await startBtn.click();

  // Wait for navigation to thread page
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });
  await pause(page, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — Launch & Watch the Deliberation (~80 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // -- Launch deliberation --
  const launchBtn = page.locator("button", { hasText: "Launch Deliberation" });
  await expect(launchBtn).toBeVisible({ timeout: 5_000 });
  await pause(page, 1000);
  await launchBtn.click();

  // Wait for the first post to appear — agents are generating
  await page.waitForSelector('[class*="PostCard"], [class*="post-card"], [style*="border-left"]', {
    timeout: 30_000,
  });
  await pause(page, 1000);

  // Watch the deliberation unfold: scroll-follow as new posts stream in
  // We'll check for posts appearing over ~60 seconds
  const startTime = Date.now();
  const maxWatchTime = 60_000; // Watch for up to 60 seconds
  let lastPostCount = 0;
  let stableCount = 0;

  while (Date.now() - startTime < maxWatchTime) {
    // Count visible posts
    const postCount = await page
      .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
      .count();

    if (postCount > lastPostCount) {
      lastPostCount = postCount;
      stableCount = 0;

      // Scroll to the latest post
      const lastPost = page
        .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
        .last();
      await lastPost.scrollIntoViewIfNeeded();
    } else {
      stableCount++;
    }

    // If we have at least 6 posts and they stopped coming, or the session
    // completed, break out
    if (stableCount > 8 && lastPostCount >= 6) break;

    // Check if completed
    const completed = await page.locator("text=Consensus Reached").isVisible().catch(() => false);
    if (completed) break;

    await page.waitForTimeout(2000);
  }

  // Show the energy gauge on the right panel (scroll right panel if needed)
  const energySection = page.locator("text=Energy").first();
  if (await energySection.isVisible().catch(() => false)) {
    await energySection.scrollIntoViewIfNeeded();
    await pause(page, 2000);
  }

  // Show phase timeline
  const phaseSection = page.locator("text=Phase Progress").first();
  if (await phaseSection.isVisible().catch(() => false)) {
    await phaseSection.scrollIntoViewIfNeeded();
    await pause(page, 1500);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — Human Intervention (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Only intervene if the deliberation is still running
  const interventionBar = page.locator('textarea[placeholder*="Intervene"]');
  const isRunning = await interventionBar.isVisible().catch(() => false);

  if (isRunning) {
    // Type an intervention question
    await typeSlowly(
      page,
      'textarea[placeholder*="Intervene"]',
      "What about the blood-brain barrier penetration data from the recent Phase II trial of oral semaglutide?"
    );
    await pause(page, 1000);

    // Click send
    const sendBtn = page.locator("button", { hasText: "Send" });
    await sendBtn.click();
    await pause(page, 1000);

    // Wait for response posts
    await page.waitForTimeout(8_000);

    // Scroll to see the latest agent responses
    const latestPost = page
      .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
      .last();
    if (await latestPost.isVisible().catch(() => false)) {
      await latestPost.scrollIntoViewIfNeeded();
    }
    await pause(page, 2000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — Consensus & Wrap-up (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Wait for consensus (up to 40 more seconds)
  try {
    await page.waitForSelector("text=Consensus Reached", { timeout: 40_000 });
    await pause(page, 1500);

    // Scroll through the consensus sections
    const consensusSummary = page.locator("text=Consensus Summary");
    if (await consensusSummary.isVisible().catch(() => false)) {
      await consensusSummary.scrollIntoViewIfNeeded();
      await pause(page, 2500);
    }

    // Scroll to agreements
    const agreements = page.locator("text=Agreements").first();
    if (await agreements.isVisible().catch(() => false)) {
      await agreements.scrollIntoViewIfNeeded();
      await pause(page, 2000);
    }

    // Scroll to disagreements
    const disagreements = page.locator("text=Disagreements").first();
    if (await disagreements.isVisible().catch(() => false)) {
      await disagreements.scrollIntoViewIfNeeded();
      await pause(page, 2000);
    }

    // Scroll to final stances
    const stances = page.locator("text=Final Stances").first();
    if (await stances.isVisible().catch(() => false)) {
      await stances.scrollIntoViewIfNeeded();
      await pause(page, 2500);
    }
  } catch {
    // If consensus didn't arrive in time, scroll to whatever we have
    const lastPost = page
      .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
      .last();
    if (await lastPost.isVisible().catch(() => false)) {
      await lastPost.scrollIntoViewIfNeeded();
    }
    await pause(page, 3000);
  }

  // Final dramatic pause on whatever is on screen
  await pause(page, 2000);
});
