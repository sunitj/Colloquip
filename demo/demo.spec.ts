/**
 * Colloquip Demo Script — 3-minute competition video
 *
 * Two simultaneous deliberations showcase the platform's concurrency:
 *   1. Drug repurposing: GLP-1 agonists for Alzheimer's
 *   2. Protein engineering: De novo enzyme design via directed evolution + ML
 *
 * Story arc:
 *   Act 1 (0:00–0:25)  — Platform overview: home, init, agent pool
 *   Act 2 (0:25–1:05)  — Enter community, create BOTH threads
 *   Act 3 (1:05–1:15)  — Launch Thread 1 (drug repurposing)
 *   Act 4 (1:15–1:50)  — While Thread 1 runs, launch Thread 2 (protein eng)
 *   Act 5 (1:50–2:20)  — Flip between both live deliberations
 *   Act 6 (2:20–2:40)  — Human intervention on Thread 2
 *   Act 7 (2:40–3:00)  — Show consensus from whichever finishes first
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

async function pause(page: Page, ms = 1500) {
  await page.waitForTimeout(ms);
}

async function typeSlowly(page: Page, selector: string, text: string) {
  await page.click(selector);
  await page.type(selector, text, { delay: 35 });
}

/** Count posts visible on a thread page */
async function postCount(page: Page): Promise<number> {
  return page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .count();
}

/** Scroll to the most recent post */
async function scrollToLatestPost(page: Page) {
  const post = page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .last();
  if (await post.isVisible().catch(() => false)) {
    await post.scrollIntoViewIfNeeded();
  }
}

/** Wait for at least N posts to appear, with a timeout */
async function waitForPosts(page: Page, n: number, timeout = 30_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await postCount(page)) >= n) return;
    await page.waitForTimeout(1500);
  }
}

/** Create a thread via the dialog (community page must already be loaded) */
async function createThread(
  page: Page,
  title: string,
  hypothesis: string
) {
  const newThreadBtn = page.locator("button", {
    hasText: /New Thread|Create First Thread/,
  });
  await newThreadBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 500);

  await typeSlowly(page, 'input[placeholder="Deliberation title"]', title);
  await typeSlowly(page, 'textarea[placeholder*="hypothesis"]', hypothesis);
  await pause(page, 600);

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });

  // Capture the thread URL so we can navigate back
  const url = page.url();
  await pause(page, 800);
  return url;
}

/** Launch a pending deliberation and wait for the first post */
async function launchDeliberation(page: Page) {
  const launchBtn = page.locator("button", { hasText: "Launch Deliberation" });
  await expect(launchBtn).toBeVisible({ timeout: 5_000 });
  await launchBtn.click();

  // Wait for the first post
  await page.waitForSelector(
    '[style*="border-left-width: 3px"], [style*="border-left: 3px"]',
    { timeout: 30_000 }
  );
}

// ─── Thread config ──────────────────────────────────────────────────────────

const THREAD_1 = {
  title: "GLP-1 Agonists for Alzheimer's Disease",
  hypothesis:
    "Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's " +
    "disease is a viable therapeutic strategy, given emerging evidence of " +
    "neuroinflammatory pathway modulation and improved cognitive outcomes " +
    "in diabetic cohorts.",
};

const THREAD_2 = {
  title: "De Novo Enzyme Design via Directed Evolution + ML",
  hypothesis:
    "Combining machine-learning-guided directed evolution with " +
    "computational protein design (RFdiffusion / ProteinMPNN) can produce " +
    "de novo enzymes with catalytic efficiencies rivaling natural enzymes " +
    "within 3 rounds of experimental screening.",
};

// ─── The Demo ───────────────────────────────────────────────────────────────

test("Colloquip Competition Demo — Dual Deliberation", async ({
  page,
  context,
}) => {
  test.setTimeout(180_000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — Platform Overview (~25 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquip")).toBeVisible();
  await pause(page, 1500);

  // Initialize platform
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await pause(page, 800);

  await page.locator("button", { hasText: "Initialize Platform" }).click();
  await expect(
    page.locator("text=Platform initialized successfully")
  ).toBeVisible({ timeout: 15_000 });
  await pause(page, 1200);

  // Browse agent pool
  await page.goto("/agents");
  await expect(page.locator("text=Agent Pool")).toBeVisible();
  await page.waitForSelector(
    '[class*="grid"] a, [class*="grid"] [class*="AgentCard"]',
    { timeout: 10_000 }
  );
  await pause(page, 2000);

  // Home — communities loaded
  await page.goto("/");
  await page.waitForSelector('a[href*="/c/"]', { timeout: 10_000 });
  await pause(page, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — Enter Community & Create Both Threads (~40 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Click into first community
  const communityLink = page.locator('a[href*="/c/"]').first();
  const communityHref = (await communityLink.getAttribute("href"))!;
  await communityLink.click();
  await page.waitForSelector('[role="tab"]', { timeout: 10_000 });
  await pause(page, 1500);

  // Show Members tab briefly
  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible()) {
    await membersTab.click();
    await pause(page, 1800);
    await page.locator('[role="tab"]', { hasText: "Threads" }).click();
    await pause(page, 800);
  }

  // --- Create Thread 1 (drug repurposing) ---
  const thread1Url = await createThread(
    page,
    THREAD_1.title,
    THREAD_1.hypothesis
  );
  await pause(page, 800);

  // Navigate back to community to create the second thread
  await page.goto(communityHref);
  await page.waitForSelector('[role="tab"]', { timeout: 10_000 });
  await pause(page, 1000);

  // --- Create Thread 2 (protein engineering) ---
  const thread2Url = await createThread(
    page,
    THREAD_2.title,
    THREAD_2.hypothesis
  );
  await pause(page, 800);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — Launch Thread 1 (~10 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Go to Thread 1 and launch it
  await page.goto(thread1Url);
  await pause(page, 800);
  await launchDeliberation(page);
  await pause(page, 1500);

  // Scroll to show the first couple of posts arriving
  await scrollToLatestPost(page);
  await pause(page, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — Open Thread 2 in a New Tab & Launch It (~35 seconds)
  // Thread 1 keeps running in the background!
  // ═══════════════════════════════════════════════════════════════════════════

  const page2 = await context.newPage();
  await page2.goto(thread2Url);
  await pause(page2, 1000);
  await launchDeliberation(page2);
  await pause(page2, 1500);

  // Watch Thread 2 for a bit
  await waitForPosts(page2, 3, 20_000);
  await scrollToLatestPost(page2);
  await pause(page2, 2000);

  // Show the energy gauge
  const energy2 = page2.locator("text=Energy").first();
  if (await energy2.isVisible().catch(() => false)) {
    await energy2.scrollIntoViewIfNeeded();
    await pause(page2, 1500);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — Flip Between Both Live Deliberations (~30 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Switch back to Thread 1 — it's been running concurrently!
  await page.bringToFront();
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // Show energy & phase on Thread 1
  const energy1 = page.locator("text=Energy").first();
  if (await energy1.isVisible().catch(() => false)) {
    await energy1.scrollIntoViewIfNeeded();
    await pause(page, 1500);
  }
  const phase1 = page.locator("text=Phase Progress").first();
  if (await phase1.isVisible().catch(() => false)) {
    await phase1.scrollIntoViewIfNeeded();
    await pause(page, 1500);
  }

  // Scroll back to conversation to show latest posts
  await scrollToLatestPost(page);
  await pause(page, 1500);

  // Flip to Thread 2 briefly — show it's still going
  await page2.bringToFront();
  await scrollToLatestPost(page2);
  await pause(page2, 2000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — Human Intervention on Thread 2 (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  const interventionBar = page2.locator('textarea[placeholder*="Intervene"]');
  if (await interventionBar.isVisible().catch(() => false)) {
    await typeSlowly(
      page2,
      'textarea[placeholder*="Intervene"]',
      "How does the ProteinMPNN sequence recovery rate compare with Rosetta for active-site residues specifically?"
    );
    await pause(page2, 800);
    await page2.locator("button", { hasText: "Send" }).click();
    await pause(page2, 1000);

    // Wait for agents to respond
    await page2.waitForTimeout(6_000);
    await scrollToLatestPost(page2);
    await pause(page2, 2000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — Consensus Reveal (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Switch to Thread 1 for the consensus finish
  await page.bringToFront();

  // Wait for consensus on either thread (try Thread 1 first)
  let consensusPage = page;
  try {
    await page.waitForSelector("text=Consensus Reached", { timeout: 30_000 });
  } catch {
    // Try Thread 2 instead
    await page2.bringToFront();
    consensusPage = page2;
    try {
      await page2.waitForSelector("text=Consensus Reached", {
        timeout: 20_000,
      });
    } catch {
      // Neither finished — show where we are
      await scrollToLatestPost(page2);
      await pause(page2, 3000);
      return;
    }
  }

  // Walk through the consensus reveal
  await pause(consensusPage, 1200);

  const sections = [
    "Consensus Summary",
    "Agreements",
    "Disagreements",
    "Minority Positions",
    "Final Stances",
  ];

  for (const section of sections) {
    const el = consensusPage.locator(`text=${section}`).first();
    if (await el.isVisible().catch(() => false)) {
      await el.scrollIntoViewIfNeeded();
      await pause(consensusPage, 1800);
    }
  }

  // Final pause
  await pause(consensusPage, 2000);
});
