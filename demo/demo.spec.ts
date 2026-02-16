/**
 * Colloquium Demo Script — 3-minute competition video
 *
 * Two deliberations in DIFFERENT communities showcase the platform's breadth:
 *   1. Neuropharmacology community: GLP-1 agonists for Alzheimer's (drug repurposing)
 *   2. Enzyme Engineering community: Engineered PETases for industrial plastic degradation
 *
 * Story arc:
 *   Act 1 (0:00–0:20)  — Platform overview: home, init, agent pool
 *   Act 2 (0:20–0:55)  — Create Community 1 (Neuropharmacology) + Thread 1 (GLP-1)
 *   Act 3 (0:55–1:30)  — Create Community 2 (Enzyme Engineering) + Thread 2 (PETase)
 *   Act 4 (1:30–1:40)  — Launch Thread 1
 *   Act 5 (1:40–2:00)  — Launch Thread 2 concurrently in a second tab
 *   Act 6 (2:00–2:20)  — Cross-cut: flip between both live deliberations
 *   Act 7 (2:20–2:40)  — Human intervention on BOTH threads
 *   Act 8 (2:40–3:00)  — Consensus reveal
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

/** Create a community via the sidebar dialog */
async function createCommunity(
  page: Page,
  slug: string,
  displayName: string,
  description: string,
  primaryDomain: string,
) {
  // Click "Create Community" in the sidebar
  const createBtn = page.locator("button", { hasText: "Create Community" });
  await createBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 400);

  // Fill the form
  await typeSlowly(page, 'input[placeholder*="drug_discovery"]', slug);
  await typeSlowly(
    page,
    'input[placeholder*="Drug Discovery"]',
    displayName,
  );
  await typeSlowly(
    page,
    'textarea[placeholder*="purpose"]',
    description,
  );
  await typeSlowly(
    page,
    'input[placeholder*="pharmaceutical"]',
    primaryDomain,
  );
  await pause(page, 400);

  // Submit
  await page.locator('[role="dialog"] button[type="submit"]').click();

  // Wait for navigation to the new community page
  await page.waitForURL(/\/c\//, { timeout: 10_000 });
  const url = page.url();
  await pause(page, 800);
  return url;
}

/** Create a thread via the dialog (community page must already be loaded) */
async function createThread(
  page: Page,
  title: string,
  hypothesis: string,
) {
  const newThreadBtn = page.locator("button", {
    hasText: /New Thread|Create First Thread/,
  }).first();
  await newThreadBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 500);

  await typeSlowly(page, 'input[placeholder="Deliberation title"]', title);
  await typeSlowly(page, 'textarea[placeholder*="hypothesis"]', hypothesis);
  await pause(page, 600);

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });

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
    { timeout: 30_000 },
  );
}

// ─── Community & Thread config ──────────────────────────────────────────────

const COMMUNITY_1 = {
  slug: "neuropharmacology",
  displayName: "Neuropharmacology",
  description:
    "Drug repurposing and novel therapeutic strategies for neurological diseases. Focus on translational evidence from metabolic pathways to CNS targets.",
  primaryDomain: "drug_discovery",
};

const COMMUNITY_2 = {
  slug: "enzyme_engineering",
  displayName: "Enzyme Engineering",
  description:
    "Computational and directed-evolution approaches to designing novel enzymes for industrial and environmental applications.",
  primaryDomain: "protein_engineering",
};

const THREAD_1 = {
  title: "GLP-1 Agonists for Alzheimer's Disease",
  hypothesis:
    "Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's " +
    "disease is a viable therapeutic strategy, given emerging evidence of " +
    "neuroinflammatory pathway modulation and improved cognitive outcomes " +
    "in diabetic cohorts.",
};

const THREAD_2 = {
  title: "Engineered PETases for Industrial Plastic Degradation",
  hypothesis:
    "Engineered PETase variants (via directed evolution and computational " +
    "redesign) can achieve sufficient catalytic efficiency and thermostability " +
    "to serve as a commercially viable industrial process for PET plastic " +
    "degradation, replacing mechanical recycling within 5 years.",
};

const INTERVENTION_1 =
  "What about the blood-brain barrier? GLP-1 is a large peptide — " +
  "what evidence exists that semaglutide actually reaches therapeutic " +
  "concentrations in the CNS, and should we be worried about peripheral " +
  "vs. central mechanisms being conflated?";

const INTERVENTION_2 =
  "I'm skeptical about the 5-year timeline. Current engineered PETases " +
  "still operate orders of magnitude slower than needed for industrial " +
  "throughput. Are we underestimating the gap between lab-scale and " +
  "industrial-scale performance?";

// ─── The Demo ───────────────────────────────────────────────────────────────

test("Colloquium Competition Demo — Dual Community Deliberation", async ({
  page,
  context,
}) => {
  test.setTimeout(180_000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — Platform Overview (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible();
  await pause(page, 1200);

  // Initialize platform
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await pause(page, 600);

  await page.locator("button", { hasText: "Initialize Platform" }).click();
  await expect(
    page.locator("text=Platform initialized successfully"),
  ).toBeVisible({ timeout: 15_000 });
  await pause(page, 1000);

  // Browse agent pool
  await page.goto("/agents");
  await expect(page.locator("text=Agent Pool")).toBeVisible();
  await page.waitForSelector(
    '[class*="grid"] a, [class*="grid"] [class*="AgentCard"]',
    { timeout: 10_000 },
  );
  await pause(page, 1500);

  // Back to home
  await page.goto("/");
  await pause(page, 800);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — Create Community 1 (Neuropharmacology) + Thread 1 (~35 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  const community1Url = await createCommunity(
    page,
    COMMUNITY_1.slug,
    COMMUNITY_1.displayName,
    COMMUNITY_1.description,
    COMMUNITY_1.primaryDomain,
  );

  // Show Members tab briefly
  const membersTab1 = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab1.isVisible()) {
    await membersTab1.click();
    await pause(page, 1500);
    await page.locator('[role="tab"]', { hasText: "Threads" }).click();
    await pause(page, 600);
  }

  // Create Thread 1 (GLP-1 for Alzheimer's)
  const thread1Url = await createThread(
    page,
    THREAD_1.title,
    THREAD_1.hypothesis,
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — Create Community 2 (Enzyme Engineering) + Thread 2 (~35 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Navigate home to create the second community
  await page.goto("/");
  await pause(page, 600);

  const community2Url = await createCommunity(
    page,
    COMMUNITY_2.slug,
    COMMUNITY_2.displayName,
    COMMUNITY_2.description,
    COMMUNITY_2.primaryDomain,
  );

  // Show Members tab briefly — different agents recruited!
  const membersTab2 = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab2.isVisible()) {
    await membersTab2.click();
    await pause(page, 1500);
    await page.locator('[role="tab"]', { hasText: "Threads" }).click();
    await pause(page, 600);
  }

  // Create Thread 2 (PETase — deliberately aggressive timeline for red-team pushback)
  const thread2Url = await createThread(
    page,
    THREAD_2.title,
    THREAD_2.hypothesis,
  );

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — Launch Thread 1 (~10 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto(thread1Url);
  await pause(page, 600);
  await launchDeliberation(page);
  await pause(page, 1500);

  await scrollToLatestPost(page);
  await pause(page, 1200);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — Open Thread 2 in a New Tab & Launch Concurrently (~20 seconds)
  // Thread 1 keeps running in the background!
  // ═══════════════════════════════════════════════════════════════════════════

  const page2 = await context.newPage();
  await page2.goto(thread2Url);
  await pause(page2, 600);
  await launchDeliberation(page2);
  await pause(page2, 1500);

  // Watch Thread 2 for a bit
  await waitForPosts(page2, 3, 20_000);
  await scrollToLatestPost(page2);
  await pause(page2, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — Cross-cut: Flip Between Both Live Deliberations (~20 seconds)
  // ═══════════════════════════════════════════════════════════════════════════

  // Switch to Thread 1 — it's been running concurrently!
  await page.bringToFront();
  await scrollToLatestPost(page);
  await pause(page, 1500);

  // Show energy & phase on Thread 1
  const energy1 = page.locator("text=Energy").first();
  if (await energy1.isVisible().catch(() => false)) {
    await energy1.scrollIntoViewIfNeeded();
    await pause(page, 1200);
  }
  const phase1 = page.locator("text=Phase Progress").first();
  if (await phase1.isVisible().catch(() => false)) {
    await phase1.scrollIntoViewIfNeeded();
    await pause(page, 1200);
  }

  // Flip to Thread 2 — show it's alive too
  await page2.bringToFront();
  await scrollToLatestPost(page2);
  await pause(page2, 1500);

  // Show energy on Thread 2
  const energy2 = page2.locator("text=Energy").first();
  if (await energy2.isVisible().catch(() => false)) {
    await energy2.scrollIntoViewIfNeeded();
    await pause(page2, 1200);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — Human Intervention on BOTH Threads (~20 seconds)
  //
  // Thread 1: Ask about the blood-brain barrier (probing biological plausibility)
  // Thread 2: Challenge the 5-year timeline (the model may reason against it)
  // ═══════════════════════════════════════════════════════════════════════════

  // Intervene on Thread 2 first (PETase — skeptical challenge)
  const interventionBar2 = page2.locator('textarea[placeholder*="Intervene"]');
  if (await interventionBar2.isVisible().catch(() => false)) {
    await typeSlowly(
      page2,
      'textarea[placeholder*="Intervene"]',
      INTERVENTION_2,
    );
    await pause(page2, 600);
    await page2.locator("button", { hasText: "Send" }).click();
    await pause(page2, 800);
  }

  // Switch to Thread 1 and intervene (GLP-1 — probing BBB question)
  await page.bringToFront();
  await scrollToLatestPost(page);
  await pause(page, 600);

  const interventionBar1 = page.locator('textarea[placeholder*="Intervene"]');
  if (await interventionBar1.isVisible().catch(() => false)) {
    await typeSlowly(
      page,
      'textarea[placeholder*="Intervene"]',
      INTERVENTION_1,
    );
    await pause(page, 600);
    await page.locator("button", { hasText: "Send" }).click();
    await pause(page, 800);

    // Wait for agents to respond to the intervention
    await page.waitForTimeout(5_000);
    await scrollToLatestPost(page);
    await pause(page, 1500);
  }

  // Check Thread 2 response to skeptical intervention
  await page2.bringToFront();
  await page2.waitForTimeout(3_000);
  await scrollToLatestPost(page2);
  await pause(page2, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 8 — Consensus Reveal (~20 seconds)
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
      await pause(consensusPage, 1500);
    }
  }

  // Final pause
  await pause(consensusPage, 2000);
});
