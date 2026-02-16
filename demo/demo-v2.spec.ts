/**
 * Colloquium Demo v2 — Live Commentary Script
 *
 * Playwright drives the browser; you record your screen + voice.
 * Pre-seeded data: 4 communities, 13 completed threads.
 * One NEW deliberation runs live for the "deep dive" portion.
 *
 * Prerequisites:
 *   1. Backend running:  uv run uvicorn colloquip.api:create_app --factory --port 8000
 *   2. Seed data loaded: uv run python scripts/seed_demo.py [--mock]
 *   3. Run: cd demo && npx playwright test demo-v2.spec.ts --headed
 *
 * Narrator: Start recording BEFORE running the script.
 * Each act has a timed pause — speak during those pauses.
 */

import { test, expect, type Page } from "@playwright/test";

// ─── Config ──────────────────────────────────────────────────────────────────

/** Deliberation mode for the live thread. Set "mock" for dry runs. */
const LIVE_MODE: "mock" | "real" = "real";

/** How long to pause for narrator breathing room (ms). Increase for slower narration. */
const NARRATOR_PACE = 1.0; // multiplier: 1.0 = normal, 1.5 = slow, 0.7 = fast

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function pause(page: Page, ms: number) {
  await page.waitForTimeout(ms * NARRATOR_PACE);
}

async function typeSlowly(page: Page, selector: string, text: string) {
  await page.click(selector);
  await page.type(selector, text, { delay: 30 });
}

/** Count visible post cards */
async function postCount(page: Page): Promise<number> {
  return page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .count();
}

/** Scroll the conversation feed to the latest post */
async function scrollToLatestPost(page: Page) {
  const post = page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .last();
  if (await post.isVisible().catch(() => false)) {
    await post.scrollIntoViewIfNeeded();
  }
}

/** Wait for at least N posts to appear */
async function waitForPosts(page: Page, n: number, timeout = 60_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await postCount(page)) >= n) return;
    await page.waitForTimeout(1500);
  }
}

/** Wait for a Key Moments card to appear in the right panel */
async function waitForAhaMoment(page: Page, timeout = 60_000) {
  await page.waitForSelector("text=Key Moments", { timeout });
}

// ─── The Live Thread ────────────────────────────────────────────────────────

const LIVE_HYPOTHESIS =
  "Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's " +
  "disease is a viable therapeutic strategy, given emerging evidence of " +
  "neuroinflammatory pathway modulation and improved cognitive outcomes " +
  "in diabetic cohorts.";

const INTERVENTION =
  "What about the blood-brain barrier? GLP-1 is a large peptide — " +
  "what evidence exists that semaglutide actually reaches therapeutic " +
  "concentrations in the CNS?";

// ─── The Demo ───────────────────────────────────────────────────────────────

test("Colloquium Demo v2 — Live Commentary", async ({ page }) => {
  test.setTimeout(300_000); // 5 min max (deliberation can take time)

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — THE HOOK: Show a completed thread first (0:00–0:25)
  //
  // NARRATOR: "Multi-agent AI today is choreographed — agents take turns in
  // a fixed sequence. What if instead, agents decided for themselves when to
  // speak, and the conversation organized itself? This is Colloquium."
  // ═══════════════════════════════════════════════════════════════════════════

  // Start on home page — pre-seeded communities visible
  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible();
  await pause(page, 3000);

  // Click into a completed thread to show the end result first
  // Navigate to the neuropharmacology community
  const neuroLink = page.locator("a", { hasText: "Neuropharmacology" }).first();
  await neuroLink.click();
  await page.waitForURL(/\/c\/neuropharmacology/);
  await pause(page, 2000);

  // Click threads tab if not already active
  const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTab.isVisible().catch(() => false)) {
    await threadsTab.click();
    await pause(page, 800);
  }

  // Click the first completed thread (Gut-Brain or Psilocybin — something interesting)
  const completedThread = page
    .locator("a[href*='/thread/']")
    .first();
  if (await completedThread.isVisible().catch(() => false)) {
    await completedThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2000);

    // Scroll through the consensus reveal
    const consensusSection = page.locator("text=Consensus Reached").first();
    if (await consensusSection.isVisible().catch(() => false)) {
      await consensusSection.scrollIntoViewIfNeeded();
      await pause(page, 3000);

      // Show agreements
      const agreements = page.locator("text=Agreements").first();
      if (await agreements.isVisible().catch(() => false)) {
        await agreements.scrollIntoViewIfNeeded();
        await pause(page, 2000);
      }

      // Show minority positions
      const minority = page.locator("text=Minority Positions").first();
      if (await minority.isVisible().catch(() => false)) {
        await minority.scrollIntoViewIfNeeded();
        await pause(page, 2000);
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — PLATFORM TOUR: Show breadth (0:25–0:50)
  //
  // NARRATOR: "Colloquium is structured like a scientific Reddit. Communities
  // scope deliberations by domain. Each community recruits specialist agents
  // from a shared pool. Let me show you."
  // ═══════════════════════════════════════════════════════════════════════════

  // Go back to home to show all communities
  await page.goto("/");
  await pause(page, 2000);

  // Hover over community cards to show variety
  const communityCards = page.locator("a[href*='/c/']");
  const cardCount = await communityCards.count();
  for (let i = 0; i < Math.min(cardCount, 4); i++) {
    const card = communityCards.nth(i);
    if (await card.isVisible().catch(() => false)) {
      await card.hover();
      await pause(page, 800);
    }
  }
  await pause(page, 1000);

  // Show agent pool briefly
  await page.goto("/agents");
  await page.waitForSelector(
    '[class*="grid"] a, [class*="grid"] [class*="AgentCard"]',
    { timeout: 10_000 },
  ).catch(() => {});
  await pause(page, 3000);

  // Navigate to neuropharmacology and show Members tab
  await page.goto("/c/neuropharmacology");
  await pause(page, 1500);

  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible().catch(() => false)) {
    await membersTab.click();
    await pause(page, 3000);
    // NARRATOR: "This community has a biology expert, a chemist, a clinical
    // trials specialist, a regulatory advisor, and — critically — a red team
    // adversary. The red team agent exists to challenge premature consensus."
  }

  // Show a different community's members for contrast
  await page.goto("/c/immuno_oncology");
  await pause(page, 1500);
  const membersTab2 = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab2.isVisible().catch(() => false)) {
    await membersTab2.click();
    await pause(page, 2000);
    // NARRATOR: "Different community, different agents recruited by domain."
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — LAUNCH LIVE DELIBERATION (0:50–1:05)
  //
  // NARRATOR: "Now let's watch a deliberation happen live. I'm posing a
  // hypothesis about repurposing semaglutide — a diabetes drug — for
  // Alzheimer's. Six agents are about to debate this. I didn't tell them
  // what order to speak in."
  // ═══════════════════════════════════════════════════════════════════════════

  // Navigate to neuropharmacology
  await page.goto("/c/neuropharmacology");
  await pause(page, 1000);

  // Switch to Threads tab
  const threadsTabLaunch = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTabLaunch.isVisible().catch(() => false)) {
    await threadsTabLaunch.click();
    await pause(page, 600);
  }

  // Create a new thread
  const newThreadBtn = page
    .locator("button", { hasText: /New Thread|Create First Thread/ })
    .first();
  await newThreadBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 500);

  await typeSlowly(
    page,
    'input[placeholder="Deliberation title"]',
    "GLP-1 for Alzheimer's — LIVE"
  );
  await typeSlowly(
    page,
    'textarea[placeholder*="hypothesis"]',
    LIVE_HYPOTHESIS,
  );
  await pause(page, 800);

  // Submit
  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });
  await pause(page, 1000);

  // Launch the deliberation
  // Select mode
  const modeSelect = page.locator('button[role="combobox"]');
  if (await modeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await modeSelect.click();
    const modeOption = LIVE_MODE === "real" ? "Real LLM" : "Mock";
    await page.locator('[role="option"]', { hasText: modeOption }).click();
    await pause(page, 300);
  }

  const launchBtn = page.locator("button", { hasText: "Launch Deliberation" });
  await expect(launchBtn).toBeVisible({ timeout: 5_000 });
  await launchBtn.click();

  // Wait for the first post
  await page.waitForSelector(
    '[style*="border-left-width: 3px"], [style*="border-left: 3px"]',
    { timeout: 60_000 },
  );
  await pause(page, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — THE EMERGENT DANCE: Watch and narrate (1:05–1:50)
  //
  // This is the MONEY SHOT. The narrator calls out each emergent moment
  // as the Key Moments panel highlights them on the right.
  //
  // NARRATOR cues (speak when you see these on the right panel):
  //   - "The biology agent spoke first — highest relevance score."
  //   - "Watch the right panel — Key Moments lights up when something
  //     emergent happens."
  //   - [Phase transition appears] "Phase transition! The observer detected
  //     a shift to Debate — disagreement crossed the threshold."
  //   - [Red team fires] "There — the red team agent just activated.
  //     Three agents agreed without challenge, and it fired automatically."
  //   - [Bridge connection] "Bridge trigger — the chemistry agent just
  //     connected concepts from biology and clinical domains."
  // ═══════════════════════════════════════════════════════════════════════════

  // Wait for seed phase posts to arrive
  await waitForPosts(page, 3, 60_000);
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // Let the deliberation run, scrolling periodically
  // The narrator speaks over whatever is happening on screen
  for (let i = 0; i < 8; i++) {
    await page.waitForTimeout(4000 * NARRATOR_PACE);
    await scrollToLatestPost(page);

    // Check if Key Moments section appeared (first aha moment)
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      // Briefly scroll right panel to show the aha feed
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1500);
    }

    // Check for energy gauge
    const energyLabel = page.locator("text=Conversation Energy").first();
    if (await energyLabel.isVisible().catch(() => false)) {
      // Energy is visible — good for narrator to comment on
      await pause(page, 1000);
    }
  }

  // Make sure we have a good number of posts
  await waitForPosts(page, 6, 30_000);
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — HUMAN INTERVENTION: The energy spike (1:50–2:15)
  //
  // NARRATOR: "I'm going to intervene with a hard question the agents
  // haven't addressed: does semaglutide actually cross the blood-brain
  // barrier? Watch what happens to the energy gauge..."
  //
  // [After typing]: "Energy spiked! My question injected novelty. The
  // agents are now responding to something none of them raised on their own."
  // ═══════════════════════════════════════════════════════════════════════════

  // Type the intervention
  const interventionBar = page.locator('textarea[placeholder*="Intervene"]');
  if (await interventionBar.isVisible().catch(() => false)) {
    await typeSlowly(
      page,
      'textarea[placeholder*="Intervene"]',
      INTERVENTION,
    );
    await pause(page, 1500);

    // Submit
    await page.locator("button", { hasText: "Send" }).click();
    await pause(page, 1000);

    // Wait for agents to respond
    const preCount = await postCount(page);
    await waitForPosts(page, preCount + 2, 60_000);
    await scrollToLatestPost(page);
    await pause(page, 3000);

    // NARRATOR: Comment on energy spike, agents pivoting to BBB question
  }

  // Let the deliberation continue for a bit more
  for (let i = 0; i < 4; i++) {
    await page.waitForTimeout(3000 * NARRATOR_PACE);
    await scrollToLatestPost(page);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — BROWSE PRE-SEEDED THREADS: Show depth (2:15–2:40)
  //
  // While the live deliberation might still be running, switch to a
  // pre-seeded completed thread to show the consensus.
  //
  // NARRATOR: "While that deliberation continues, let me show you a
  // completed one. This is what happens when the energy decays below the
  // termination threshold for three consecutive turns..."
  // ═══════════════════════════════════════════════════════════════════════════

  // Navigate to a pre-seeded thread with consensus
  await page.goto("/c/enzyme_engineering");
  await pause(page, 1500);

  const threadsTabSeeded = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTabSeeded.isVisible().catch(() => false)) {
    await threadsTabSeeded.click();
    await pause(page, 800);
  }

  // Click a completed thread
  const seededThread = page.locator("a[href*='/thread/']").first();
  if (await seededThread.isVisible().catch(() => false)) {
    await seededThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2000);

    // Show the conversation feed
    await scrollToLatestPost(page);
    await pause(page, 2000);

    // Show the Key Moments panel for this completed thread
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 2000);
    }

    // Show consensus section
    const consensus = page.locator("text=Consensus Reached").first();
    if (await consensus.isVisible().catch(() => false)) {
      await consensus.scrollIntoViewIfNeeded();
      await pause(page, 2000);

      // Walk through consensus sections
      for (const section of ["Agreements", "Disagreements", "Minority Positions"]) {
        const el = page.locator(`text=${section}`).first();
        if (await el.isVisible().catch(() => false)) {
          await el.scrollIntoViewIfNeeded();
          await pause(page, 1500);
        }
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — CLOSE: Vision + ending (2:40–3:00)
  //
  // NARRATOR: "Every conclusion became a memory with Bayesian confidence.
  // The next deliberation in this community will build on what these agents
  // learned. Complex behavior from simple rules — that's Colloquium,
  // powered by Claude Opus 4.6."
  // ═══════════════════════════════════════════════════════════════════════════

  // Return to home page for the closing shot
  await page.goto("/");
  await pause(page, 2000);

  // Slow pan over the communities
  const finalCards = page.locator("a[href*='/c/']");
  const finalCount = await finalCards.count();
  for (let i = 0; i < Math.min(finalCount, 4); i++) {
    await finalCards.nth(i).hover();
    await pause(page, 600);
  }

  await pause(page, 3000);
  // END
});
