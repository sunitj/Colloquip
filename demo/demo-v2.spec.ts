/**
 * Colloquium Demo v2 — Live Commentary Script
 *
 * Playwright drives the browser; you record your screen + voice.
 * Pre-seeded data: 5 communities, 16 completed threads (includes
 * a cross-community microbiome+immuno-oncology thread).
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
  test.setTimeout(600_000); // 10 min max (real LLM deliberation + exploration)

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — THE HOOK: Show a completed thread first (0:00–0:30)
  //
  // NARRATOR: "Multi-agent AI today is choreographed — agents take turns in
  // a fixed sequence. What if instead, agents decided for themselves when to
  // speak, and the conversation organized itself? This is Colloquium."
  // ═══════════════════════════════════════════════════════════════════════════

  // Start on home page — pre-seeded communities visible
  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible();
  await pause(page, 3000);

  // Navigate to neuropharmacology community
  const neuroLink = page.locator("a", { hasText: "Neuropharmacology" }).first();
  await neuroLink.click();
  await page.waitForURL(/\/c\/neuropharmacology/);
  await pause(page, 2000);

  // Click threads tab
  const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTab.isVisible().catch(() => false)) {
    await threadsTab.click();
    await pause(page, 800);
  }

  // Click the first completed thread to show the end result first
  const completedThread = page.locator("a[href*='/thread/']").first();
  if (await completedThread.isVisible().catch(() => false)) {
    await completedThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2000);

    // Show the right panel — Key Moments feed is the hook
    const keyMomentsHook = page.locator("text=Key Moments").first();
    if (await keyMomentsHook.isVisible().catch(() => false)) {
      await keyMomentsHook.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 2000);
      // NARRATOR: "Look at this panel — phase transitions, red-team challenges,
      // bridge connections. None of this was scripted."
    }

    // Scroll through the consensus
    const consensusSection = page.locator("text=Consensus Reached").first();
    if (await consensusSection.isVisible().catch(() => false)) {
      await consensusSection.scrollIntoViewIfNeeded();
      await pause(page, 2000);

      // Walk through consensus sections
      for (const section of ["Agreements", "Minority Positions"]) {
        const el = page.locator(`text=${section}`).first();
        if (await el.isVisible().catch(() => false)) {
          await el.scrollIntoViewIfNeeded();
          await pause(page, 1500);
        }
      }
    }

    // Show cost summary at the bottom of right panel
    const costSection = page.locator("text=Cost Summary").first();
    if (await costSection.isVisible().catch(() => false)) {
      await costSection.scrollIntoViewIfNeeded();
      await pause(page, 1500);
      // NARRATOR: "Every deliberation tracks token costs in real time."
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — PLATFORM TOUR: Show breadth (0:30–1:00)
  //
  // NARRATOR: "Colloquium is structured like a scientific Reddit. Five
  // communities from neuropharmacology to microbiome therapeutics, each
  // with its own specialist agents recruited by expertise."
  // ═══════════════════════════════════════════════════════════════════════════

  // Go back to home to show all 5 communities
  await page.goto("/");
  await pause(page, 2000);

  // Hover over all community cards to show variety
  const communityCards = page.locator("a[href*='/c/']");
  const cardCount = await communityCards.count();
  for (let i = 0; i < Math.min(cardCount, 5); i++) {
    const card = communityCards.nth(i);
    if (await card.isVisible().catch(() => false)) {
      await card.hover();
      await pause(page, 700);
    }
  }
  await pause(page, 1000);

  // Show agent pool
  await page.goto("/agents");
  await page
    .waitForSelector(
      '[class*="grid"] a, [class*="grid"] [class*="AgentCard"]',
      { timeout: 10_000 },
    )
    .catch(() => {});
  await pause(page, 3000);

  // Show neuropharmacology Members tab
  await page.goto("/c/neuropharmacology");
  await pause(page, 1500);

  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible().catch(() => false)) {
    await membersTab.click();
    await pause(page, 2500);
    // NARRATOR: "This community has biology, chemistry, clinical, regulatory,
    // and a red-team adversary. The red team exists to challenge premature
    // consensus — and it activates automatically."
  }

  // Flash microbiome community for contrast — it's new and cross-links
  await page.goto("/c/microbiome_therapeutics");
  await pause(page, 1500);
  const membersTab2 = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab2.isVisible().catch(() => false)) {
    await membersTab2.click();
    await pause(page, 2000);
    // NARRATOR: "The Microbiome community — different domain, different
    // agents. But notice — one of its threads overlaps with Immuno-Oncology.
    // The system detects cross-community connections."
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — LAUNCH LIVE DELIBERATION (1:00–1:15)
  //
  // NARRATOR: "Now let's watch a deliberation happen live. I'm posing a
  // hypothesis about repurposing semaglutide — a diabetes drug — for
  // Alzheimer's. Six agents are about to debate this. I didn't tell them
  // what order to speak in."
  // ═══════════════════════════════════════════════════════════════════════════

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
    "GLP-1 for Alzheimer's — LIVE",
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

  // Select LLM mode
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
  // ACT 4 — THE EMERGENT DANCE: Watch and narrate (1:15–2:05)
  //
  // This is the MONEY SHOT. The narrator calls out each emergent moment
  // as the Key Moments panel highlights them on the right.
  //
  // NARRATOR cues (speak when you see these on the right panel):
  //   - "The biology agent spoke first — highest relevance score."
  //   - "Watch the right panel — Key Moments lights up when something
  //     emergent happens."
  //   - [Phase transition] "Phase transition! The observer detected a shift
  //     to Debate — disagreement crossed the threshold."
  //   - [Red team fires] "The red team agent just activated. Agents agreed
  //     without challenge, and the adversary fired automatically."
  //   - [Bridge connection] "Bridge trigger — connecting concepts across
  //     two different specialists' domains."
  //   - [Energy gauge] "Watch the energy bar. It has a metabolism — novelty
  //     drives it up, repetition drives it down."
  // ═══════════════════════════════════════════════════════════════════════════

  // Wait for seed phase posts
  await waitForPosts(page, 3, 60_000);
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // Let the deliberation run, scrolling periodically
  for (let i = 0; i < 10; i++) {
    await page.waitForTimeout(4000 * NARRATOR_PACE);
    await scrollToLatestPost(page);

    // Check if Key Moments appeared — scroll right panel to show it
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1500);
    }

    // Check for energy gauge
    const energyLabel = page.locator("text=Conversation Energy").first();
    if (await energyLabel.isVisible().catch(() => false)) {
      await pause(page, 800);
    }

    // Check for cost summary updating live
    const costLabel = page.locator("text=Cost Summary").first();
    if (await costLabel.isVisible().catch(() => false) && i === 5) {
      await costLabel.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1500);
      // NARRATOR: "Cost tracking is live — every LLM call is metered."
    }
  }

  // Make sure we have a good number of posts
  await waitForPosts(page, 6, 30_000);
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — HUMAN INTERVENTION: The energy spike (2:05–2:30)
  //
  // NARRATOR: "I'm going to intervene with a hard question the agents
  // haven't addressed: does semaglutide actually cross the blood-brain
  // barrier? Watch the energy gauge..."
  // ═══════════════════════════════════════════════════════════════════════════

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

    // Wait for agents to respond to the intervention
    const preCount = await postCount(page);
    await waitForPosts(page, preCount + 2, 60_000);
    await scrollToLatestPost(page);
    await pause(page, 3000);

    // Check for energy spike in Key Moments
    const spikeLabel = page.locator("text=Energy Spike").first();
    if (await spikeLabel.isVisible().catch(() => false)) {
      await spikeLabel.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 2000);
      // NARRATOR: "Energy spiked! My question injected novelty. The agents
      // are pivoting to address something none of them raised."
    }

    // Check for human intervention moment
    const humanMoment = page.locator("text=Human").first();
    if (await humanMoment.isVisible().catch(() => false)) {
      await pause(page, 1000);
    }
  }

  // Let the deliberation continue a bit
  for (let i = 0; i < 3; i++) {
    await page.waitForTimeout(3000 * NARRATOR_PACE);
    await scrollToLatestPost(page);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — PRE-SEEDED DEPTH: Completed threads + cross-community (2:30–3:00)
  //
  // NARRATOR: "While that continues, let me show you a completed deliberation.
  // This is what happens when energy decays below the termination threshold..."
  // ═══════════════════════════════════════════════════════════════════════════

  // Show a completed enzyme engineering thread
  await page.goto("/c/enzyme_engineering");
  await pause(page, 1500);

  const threadsTabSeeded = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTabSeeded.isVisible().catch(() => false)) {
    await threadsTabSeeded.click();
    await pause(page, 800);
  }

  const seededThread = page.locator("a[href*='/thread/']").first();
  if (await seededThread.isVisible().catch(() => false)) {
    await seededThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2000);

    // Show conversation feed
    await scrollToLatestPost(page);
    await pause(page, 2000);

    // Show Key Moments for completed thread
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 2000);
      // NARRATOR: "The forensic trail of emergence — every phase transition,
      // every red-team challenge, every bridge connection."
    }

    // Show consensus
    const consensus = page.locator("text=Consensus Reached").first();
    if (await consensus.isVisible().catch(() => false)) {
      await consensus.scrollIntoViewIfNeeded();
      await pause(page, 2000);

      for (const section of [
        "Agreements",
        "Disagreements",
        "Minority Positions",
      ]) {
        const el = page.locator(`text=${section}`).first();
        if (await el.isVisible().catch(() => false)) {
          await el.scrollIntoViewIfNeeded();
          await pause(page, 1200);
        }
      }
      // NARRATOR: "The minority position survived intact. That's a feature —
      // the system preserves disagreement, not just consensus."
    }
  }

  // Show the cross-community thread in microbiome
  await page.goto("/c/microbiome_therapeutics");
  await pause(page, 1500);

  const threadsTabMicro = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTabMicro.isVisible().catch(() => false)) {
    await threadsTabMicro.click();
    await pause(page, 800);
  }

  // Look for the cross-community thread (gut microbiome + immunotherapy)
  const crossThread = page
    .locator("a[href*='/thread/']", { hasText: /[Mm]icrobiome|[Ii]mmuno/ })
    .first();
  if (await crossThread.isVisible().catch(() => false)) {
    await crossThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 2500);
    await scrollToLatestPost(page);
    await pause(page, 2000);
    // NARRATOR: "This thread spans two communities — Microbiome and
    // Immuno-Oncology. The system detected overlapping entities between
    // their memories. Cross-pollination of knowledge."
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — INSTITUTIONAL MEMORY: The graph view (3:00–3:20)
  //
  // NARRATOR: "Every completed deliberation produces a memory with Bayesian
  // confidence. Let me show you the knowledge graph."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/memories");
  await pause(page, 2000);

  // Show the grid view first briefly
  const memoriesGrid = page.locator("text=Institutional Knowledge").first();
  if (await memoriesGrid.isVisible().catch(() => false)) {
    await pause(page, 2000);
    // NARRATOR: "Each card is a memory distilled from a deliberation.
    // Confidence is Bayesian — updated by annotations and outcomes."
  }

  // Switch to Graph view — the new Reagraph visualization
  const graphTab = page.locator('[role="tab"]', { hasText: "Graph" });
  if (await graphTab.isVisible().catch(() => false)) {
    await graphTab.click();
    await pause(page, 3000);
    // NARRATOR: "Switch to the graph view — each node is a memory, sized by
    // confidence, colored by community. Edges are cross-references detected
    // by shared entities and embedding similarity."

    // Hover over a few nodes if visible
    const graphCanvas = page.locator("canvas").first();
    if (await graphCanvas.isVisible().catch(() => false)) {
      // Move the mouse across the graph to trigger hover labels
      const box = await graphCanvas.boundingBox();
      if (box) {
        // Sweep from left to right across the graph
        for (let x = 0.2; x <= 0.8; x += 0.15) {
          await page.mouse.move(box.x + box.width * x, box.y + box.height * 0.5);
          await pause(page, 800);
        }
        // Click near center to potentially select a node
        await page.mouse.click(
          box.x + box.width * 0.5,
          box.y + box.height * 0.45,
        );
        await pause(page, 2000);
        // NARRATOR: "Click a node to see its conclusions, confidence score,
        // and the agents who contributed."
      }
    }
  }

  // Switch back to grid briefly to show the filter
  const gridTab = page.locator('[role="tab"]', { hasText: "Grid" });
  if (await gridTab.isVisible().catch(() => false)) {
    await gridTab.click();
    await pause(page, 1500);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 8 — CLOSE: Vision + ending (3:20–3:40)
  //
  // NARRATOR: "Complex behavior from simple rules. Agents that decide when
  // to speak. A conversation that terminates when it runs out of ideas.
  // Institutional memory that grows with every deliberation.
  // That's Colloquium — emergent scientific discourse, powered by Claude."
  // ═══════════════════════════════════════════════════════════════════════════

  // Return to home page for the closing shot
  await page.goto("/");
  await pause(page, 2000);

  // Slow pan over all 5 communities
  const finalCards = page.locator("a[href*='/c/']");
  const finalCount = await finalCards.count();
  for (let i = 0; i < Math.min(finalCount, 5); i++) {
    await finalCards.nth(i).hover();
    await pause(page, 600);
  }

  await pause(page, 4000);
  // END
});
