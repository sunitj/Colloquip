/**
 * Colloquium Competition Demo — "Emergent Scientific Discourse"
 *
 * A comprehensive 3.5-minute automated demo optimized for judging criteria:
 *   - Impact (25%): Real-world potential for scientific deliberation
 *   - Opus 4.6 Use (25%): Emergent agent behavior, self-organizing phases, red-team
 *   - Depth & Execution (20%): Energy model, triggers, institutional memory, calibration
 *
 * Story Arc:
 *   Act 1 (0:00–0:25)  — THE HOOK: Show a completed consensus reveal immediately
 *   Act 2 (0:25–0:55)  — THE PLATFORM: Tour communities, agent pool, agent deep-dive
 *   Act 3 (0:55–1:25)  — BUILD: Create community + thread from scratch
 *   Act 4 (1:25–2:15)  — THE LIVE EVENT: Launch deliberation, watch emergence unfold
 *   Act 5 (2:15–2:45)  — HUMAN IN THE LOOP: Intervene, watch energy spike + pivot
 *   Act 6 (2:45–3:10)  — INSTITUTIONAL MEMORY: Knowledge graph, cross-references
 *   Act 7 (3:10–3:30)  — THE CLOSE: Consensus + closing shot
 *
 * Prerequisites:
 *   1. Platform running: docker compose up -d (or local dev servers)
 *   2. Seed data loaded: uv run python scripts/seed_demo.py [--mock]
 *   3. Run: cd demo && npx playwright test demo-competition.spec.ts --headed
 *
 * Narrator: Start OBS/Loom recording BEFORE running the script.
 */

import { test, expect, type Page } from "@playwright/test";

// ─── Configuration ──────────────────────────────────────────────────────────

/** Narrator pace multiplier: 1.0 = normal, 1.3 = breathing room, 0.8 = tight */
const NARRATOR_PACE = 1.0;

/** Use mock LLM for dry runs (set DEMO_MODE=mock env var) */
const USE_MOCK = process.env.DEMO_MODE === "mock";

/** Theme to switch to during the demo for visual flair */
const DEMO_THEME: "dark" | "light" | "pastel" = "dark";

// ─── Helpers ────────────────────────────────────────────────────────────────

async function pause(page: Page, ms: number) {
  await page.waitForTimeout(ms * NARRATOR_PACE);
}

async function typeSlowly(page: Page, selector: string, text: string) {
  await page.click(selector);
  await page.type(selector, text, { delay: 28 });
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

/** Wait for at least N posts to appear */
async function waitForPosts(page: Page, n: number, timeout = 60_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await postCount(page)) >= n) return;
    await page.waitForTimeout(1500);
  }
}

/** Smoothly scroll an element into view and pause for the camera */
async function spotlight(page: Page, textOrSelector: string, duration = 1500) {
  // Try text match first, then CSS selector
  let el = page.locator(`text=${textOrSelector}`).first();
  if (!(await el.isVisible().catch(() => false))) {
    el = page.locator(textOrSelector).first();
  }
  if (await el.isVisible().catch(() => false)) {
    await el.scrollIntoViewIfNeeded();
    await pause(page, duration);
    return true;
  }
  return false;
}

/** Hover over cards in a grid to create a visual scanning effect */
async function scanCards(page: Page, selector: string, maxCards = 5) {
  const cards = page.locator(selector);
  const count = await cards.count();
  for (let i = 0; i < Math.min(count, maxCards); i++) {
    const card = cards.nth(i);
    if (await card.isVisible().catch(() => false)) {
      await card.hover();
      await pause(page, 500);
    }
  }
}

// ─── Demo Content ───────────────────────────────────────────────────────────

const NEW_COMMUNITY = {
  slug: "crispr_therapeutics",
  displayName: "CRISPR Therapeutics",
  description:
    "Base editing, prime editing, and in-vivo delivery strategies for genetic diseases. " +
    "Bridging preclinical promise with clinical translation challenges.",
  primaryDomain: "gene_therapy",
};

const NEW_THREAD = {
  title: "In-Vivo Base Editing for Sickle Cell Disease",
  hypothesis:
    "In-vivo adenine base editing delivered via lipid nanoparticles can achieve " +
    "durable therapeutic correction of the sickle cell mutation (HBB E6V) without " +
    "requiring myeloablative conditioning or ex-vivo cell manipulation, making " +
    "curative gene therapy accessible in resource-limited settings within 3 years.",
};

const INTERVENTION =
  "What about off-target editing? Recent whole-genome sequencing studies have " +
  "found bystander edits at rates of 0.1-1% at homologous loci. For a therapy " +
  "targeting hematopoietic stem cells, even rare off-targets could be " +
  "oncogenic. How do we square the urgency of access with the precautionary " +
  "principle?";

// ─── The Competition Demo ───────────────────────────────────────────────────

test("Colloquium Competition Demo — Emergent Scientific Discourse", async ({
  page,
}) => {
  test.setTimeout(USE_MOCK ? 300_000 : 600_000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — THE HOOK: Show what the platform produces (0:00–0:25)
  //
  // NARRATOR: "What happens when you give six AI scientists a controversial
  // hypothesis and let them decide for themselves when to speak? No turns.
  // No choreography. Just rules of engagement — and emergence."
  // ═══════════════════════════════════════════════════════════════════════════

  // Land on home page — pre-seeded communities visible
  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible();
  await pause(page, 2500);

  // Navigate to a completed thread to show the end product first
  const neuroLink = page.locator("a", { hasText: "Neuropharmacology" }).first();
  if (await neuroLink.isVisible().catch(() => false)) {
    await neuroLink.click();
    await page.waitForURL(/\/c\/neuropharmacology/);
    await pause(page, 1200);

    // Click Threads tab and open the first completed thread
    const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
    if (await threadsTab.isVisible().catch(() => false)) {
      await threadsTab.click();
      await pause(page, 600);
    }

    const firstThread = page.locator("a[href*='/thread/']").first();
    if (await firstThread.isVisible().catch(() => false)) {
      await firstThread.click();
      await page.waitForURL(/\/thread\//);
      await pause(page, 1500);

      // NARRATOR: "This is the output: six agents debated GLP-1 agonists for
      // Alzheimer's. Let me show you what emerged."

      // Show the Key Moments panel first — the hook
      await spotlight(page, "Key Moments", 2000);

      // NARRATOR: "Phase transitions detected by an observer from conversation
      // metrics. A red-team agent that fired automatically when consensus
      // formed too quickly. Bridge connections across domains. None of this
      // was scripted."

      // Scroll to consensus
      const consensusEl = page.locator("text=Consensus Reached").first();
      if (await consensusEl.isVisible().catch(() => false)) {
        await consensusEl.scrollIntoViewIfNeeded();
        await pause(page, 1500);

        // Walk through consensus sections
        for (const section of ["Agreements", "Disagreements", "Minority Positions"]) {
          await spotlight(page, section, 1200);
        }

        // NARRATOR: "Agreements, disagreements, and critically — minority
        // positions that survived. The system preserves dissent."
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — THE PLATFORM: Tour the ecosystem (0:25–0:55)
  //
  // NARRATOR: "Colloquium is structured like a scientific Reddit. Communities
  // scoped by domain. Persistent agent identities with real expertise profiles.
  // Institutional memory that grows with every deliberation."
  // ═══════════════════════════════════════════════════════════════════════════

  // Home page — show all communities
  await page.goto("/");
  await pause(page, 1500);

  // Scan across community cards
  await scanCards(page, "a[href*='/c/']", 5);
  await pause(page, 800);

  // NARRATOR: "Five communities — from neuropharmacology to enzyme
  // engineering. Each recruits its own specialist agents."

  // Agent pool — the cast of characters
  await page.goto("/agents");
  await page
    .waitForSelector(
      '[class*="grid"] a, [class*="grid"] [class*="AgentCard"]',
      { timeout: 10_000 },
    )
    .catch(() => {});
  await pause(page, 2000);

  // NARRATOR: "The agent pool. Each agent has a distinct persona, phase
  // mandates, and evaluation criteria — all authored by Opus 4.6."

  // Deep-dive into an agent profile to show the persona
  const firstAgent = page.locator("a[href*='/agents/']").first();
  if (await firstAgent.isVisible().catch(() => false)) {
    await firstAgent.click();
    await page.waitForURL(/\/agents\//);
    await pause(page, 2000);

    // Show persona prompt
    await spotlight(page, "Persona", 2500);

    // NARRATOR: "Look at this persona prompt. It's not 'you are a biology
    // expert.' It's a nuanced scientific identity with publication biases,
    // intellectual commitments, and blind spots. Opus 4.6 doesn't just
    // follow instructions — it inhabits a character."

    // Show expertise tab
    const expertiseTab = page.locator('[role="tab"]', { hasText: "Expertise" });
    if (await expertiseTab.isVisible().catch(() => false)) {
      await expertiseTab.click();
      await pause(page, 1800);
      // NARRATOR: "Domain keywords, evaluation criteria — the trigger system
      // uses these to determine when this agent should speak."
    }
  }

  // Show a community members panel — different agents for different domains
  await page.goto("/c/neuropharmacology");
  await pause(page, 800);

  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible().catch(() => false)) {
    await membersTab.click();
    await pause(page, 2000);
    // NARRATOR: "Biology, chemistry, clinical, regulatory, and a red-team
    // adversary. The red team exists to challenge premature consensus —
    // and it activates automatically via inverted trigger rules."
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — BUILD: Create a new community + thread from scratch (0:55–1:25)
  //
  // NARRATOR: "Let me build something new. A CRISPR therapeutics community
  // with a provocative hypothesis: can in-vivo base editing cure sickle cell
  // disease without myeloablative conditioning — in three years?"
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await pause(page, 600);

  // Create community
  const createBtn = page.locator("button", { hasText: "Create Community" });
  await createBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 400);

  await typeSlowly(page, 'input[placeholder*="drug_discovery"]', NEW_COMMUNITY.slug);
  await typeSlowly(page, 'input[placeholder*="Drug Discovery"]', NEW_COMMUNITY.displayName);
  await typeSlowly(page, 'textarea[placeholder*="purpose"]', NEW_COMMUNITY.description);
  await typeSlowly(page, 'input[placeholder*="pharmaceutical"]', NEW_COMMUNITY.primaryDomain);
  await pause(page, 500);

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/c\//, { timeout: 10_000 });
  await pause(page, 1200);

  // NARRATOR: "Community created. The platform auto-recruited agents based
  // on expertise matching — biology, chemistry, clinical specialists, and
  // a red-team adversary."

  // Show auto-recruited members
  const newMembersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await newMembersTab.isVisible().catch(() => false)) {
    await newMembersTab.click();
    await pause(page, 2000);

    // Switch back to threads
    await page.locator('[role="tab"]', { hasText: "Threads" }).click();
    await pause(page, 500);
  }

  // Create thread
  const newThreadBtn = page
    .locator("button", { hasText: /New Thread|Create First Thread/ })
    .first();
  await newThreadBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 400);

  await typeSlowly(
    page,
    'input[placeholder="Deliberation title"]',
    NEW_THREAD.title,
  );
  await typeSlowly(
    page,
    'textarea[placeholder*="hypothesis"]',
    NEW_THREAD.hypothesis,
  );
  await pause(page, 600);

  // NARRATOR: "The hypothesis is deliberately provocative. That '3 years'
  // claim is designed to trigger the red-team agent. And the clinical
  // specialist will have concerns about off-target editing. Let's see
  // what Opus 4.6 does with this."

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });
  await pause(page, 1000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — THE LIVE EVENT: Watch emergence unfold (1:25–2:15)
  //
  // NARRATOR: "I'm launching the deliberation now. Watch the right panel —
  // Key Moments will light up when something emergent happens."
  // ═══════════════════════════════════════════════════════════════════════════

  // Select LLM mode
  const modeSelect = page.locator('button[role="combobox"]');
  if (await modeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await modeSelect.click();
    const modeLabel = USE_MOCK ? "Mock" : "claude-opus-4-6";
    await page.locator('[role="option"]', { hasText: modeLabel }).click();
    await pause(page, 300);
  }

  // Launch
  const launchBtn = page.locator("button", { hasText: "Launch Deliberation" });
  await expect(launchBtn).toBeVisible({ timeout: 5_000 });
  await launchBtn.click();

  // Wait for the first post
  const firstPostTimeout = USE_MOCK ? 30_000 : 120_000;
  await page.waitForSelector(
    '[style*="border-left-width: 3px"], [style*="border-left: 3px"]',
    { timeout: firstPostTimeout },
  );
  await pause(page, 1500);

  // NARRATOR: "The biology agent spoke first — highest relevance score
  // on the trigger evaluator. No one told it to go first."

  // Watch seed phase posts arrive
  await waitForPosts(page, 3, USE_MOCK ? 30_000 : 120_000);
  await scrollToLatestPost(page);
  await pause(page, 2000);

  // NARRATOR: "Three seed posts from three different specialists.
  // Now the observer will analyze these metrics and detect which
  // phase the conversation is in."

  // Main deliberation loop — scroll and spotlight emergent events
  for (let i = 0; i < 8; i++) {
    await page.waitForTimeout(4000 * NARRATOR_PACE);
    await scrollToLatestPost(page);

    // Spotlight Key Moments panel when it populates
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1200);
    }

    // At iteration 3, spotlight the energy gauge
    if (i === 3) {
      const energyLabel = page.locator("text=Energy").first();
      if (await energyLabel.isVisible().catch(() => false)) {
        await energyLabel.scrollIntoViewIfNeeded().catch(() => {});
        await pause(page, 1500);
        // NARRATOR: "The energy bar. It has a metabolism:
        // E = 0.4*novelty + 0.3*disagreement + 0.2*questions - 0.1*staleness.
        // When energy decays below 0.2 for three consecutive turns,
        // the deliberation terminates itself."
      }
    }

    // At iteration 5, spotlight the phase timeline
    if (i === 5) {
      const phaseLabel = page.locator("text=Phase Progress").first();
      if (await phaseLabel.isVisible().catch(() => false)) {
        await phaseLabel.scrollIntoViewIfNeeded().catch(() => {});
        await pause(page, 1500);
        // NARRATOR: "Phase transitions. Explore to Debate — disagreement
        // crossed the threshold. The observer detected this from metrics,
        // not from a scripted sequence. The system can oscillate back."
      }
    }

    // At iteration 6, spotlight the agent stage
    if (i === 6) {
      const agentsLabel = page.locator("text=Agents").first();
      if (await agentsLabel.isVisible().catch(() => false)) {
        await agentsLabel.scrollIntoViewIfNeeded().catch(() => {});
        await pause(page, 1200);
        // NARRATOR: "Agent participation. Some agents are more active than
        // others — not because we told them to be, but because the trigger
        // evaluator found their expertise more relevant."
      }
    }

    // Scroll back to feed for next post
    await scrollToLatestPost(page);
  }

  // Ensure we have enough posts for a meaningful deliberation
  await waitForPosts(page, 6, USE_MOCK ? 20_000 : 120_000);
  await scrollToLatestPost(page);
  await pause(page, 1500);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — HUMAN IN THE LOOP: Intervene and watch the pivot (2:15–2:45)
  //
  // NARRATOR: "Now I'm going to do something the agents haven't addressed:
  // challenge them on off-target editing. This is a real concern that could
  // sink the entire thesis. Watch the energy gauge when I inject this."
  // ═══════════════════════════════════════════════════════════════════════════

  const interventionBar = page.locator(
    'textarea[placeholder*="Intervene"]',
  );
  if (await interventionBar.isVisible().catch(() => false)) {
    await typeSlowly(
      page,
      'textarea[placeholder*="Intervene"]',
      INTERVENTION,
    );
    await pause(page, 1500);

    // NARRATOR: "Submitting a human intervention — a question about
    // off-target editing risks. The backend injects this as a post
    // and boosts energy via the HUMAN_INTERVENTION source."

    // Submit
    await page.locator("button", { hasText: "Send" }).click();
    await pause(page, 1000);

    // Wait for agent responses to the intervention
    const preCount = await postCount(page);
    await waitForPosts(page, preCount + 2, USE_MOCK ? 30_000 : 120_000);
    await scrollToLatestPost(page);
    await pause(page, 2500);

    // NARRATOR: "The agents are pivoting. The clinical specialist is
    // responding with data. The red-team agent is amplifying the concern.
    // The biology agent is defending with recent literature. This is
    // emergent behavior — each agent decided independently to respond."

    // Spotlight the energy spike in Key Moments
    const spikeLabel = page.locator("text=Energy Spike").first();
    if (await spikeLabel.isVisible().catch(() => false)) {
      await spikeLabel.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 2000);
      // NARRATOR: "Energy spiked! My question injected novelty into a
      // converging discussion. The deliberation just got a second wind."
    }

    // Show cost tracking is live
    const costLabel = page.locator("text=Cost Summary").first();
    if (await costLabel.isVisible().catch(() => false)) {
      await costLabel.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1500);
      // NARRATOR: "Every LLM call is metered in real time. Token counts,
      // dollar costs, call counts — full transparency."
    }
  }

  // Let the deliberation continue
  for (let i = 0; i < 3; i++) {
    await page.waitForTimeout(3000 * NARRATOR_PACE);
    await scrollToLatestPost(page);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — INSTITUTIONAL MEMORY: The knowledge graph (2:45–3:10)
  //
  // NARRATOR: "Every completed deliberation produces a synthesis memory
  // with Bayesian confidence. Confidence decays over time — a 120-day
  // half-life — and updates when new evidence arrives."
  // ═══════════════════════════════════════════════════════════════════════════

  // Navigate to memories page
  await page.goto("/memories");
  await pause(page, 2000);

  // Show grid view
  const memoriesTitle = page.locator("text=Institutional Knowledge").first();
  if (await memoriesTitle.isVisible().catch(() => false)) {
    await pause(page, 1500);
    // NARRATOR: "Each card is a memory distilled from a deliberation.
    // Confidence is a Beta distribution — updated by annotations and
    // outcome reports."
  }

  // Scan memory cards
  await scanCards(page, '[class*="grid"] > *', 4);

  // Switch to Graph view
  const graphTab = page.locator('[role="tab"]', { hasText: "Graph" });
  if (await graphTab.isVisible().catch(() => false)) {
    await graphTab.click();
    await pause(page, 3000);

    // NARRATOR: "The knowledge graph. Nodes sized by confidence, colored
    // by community. Edges are cross-references — detected by shared
    // entities and embedding similarity. Knowledge doesn't stay siloed."

    // Interact with the graph canvas
    const graphCanvas = page.locator("canvas").first();
    if (await graphCanvas.isVisible().catch(() => false)) {
      const box = await graphCanvas.boundingBox();
      if (box) {
        // Sweep across the graph
        for (let x = 0.2; x <= 0.8; x += 0.12) {
          await page.mouse.move(
            box.x + box.width * x,
            box.y + box.height * 0.5,
          );
          await pause(page, 600);
        }
        // Click center to select a node
        await page.mouse.click(
          box.x + box.width * 0.5,
          box.y + box.height * 0.45,
        );
        await pause(page, 2000);
        // NARRATOR: "Click a node to see its conclusions and the agents
        // who contributed. This is institutional memory — it persists
        // across deliberations and informs future discussions."
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — THE CLOSE: Show depth + closing shot (3:10–3:30)
  //
  // NARRATOR: "Let me show you one more thing — a completed deliberation
  // in enzyme engineering. Different community, different agents, same
  // emergent dynamics."
  // ═══════════════════════════════════════════════════════════════════════════

  // Show a completed thread from a different community for contrast
  await page.goto("/c/enzyme_engineering");
  await pause(page, 1200);

  const threadsTabFinal = page.locator('[role="tab"]', { hasText: "Threads" });
  if (await threadsTabFinal.isVisible().catch(() => false)) {
    await threadsTabFinal.click();
    await pause(page, 600);
  }

  const completedThread = page.locator("a[href*='/thread/']").first();
  if (await completedThread.isVisible().catch(() => false)) {
    await completedThread.click();
    await page.waitForURL(/\/thread\//);
    await pause(page, 1500);

    // Scroll through the conversation quickly
    await scrollToLatestPost(page);
    await pause(page, 1500);

    // Show consensus if available
    const consensus = page.locator("text=Consensus Reached").first();
    if (await consensus.isVisible().catch(() => false)) {
      await consensus.scrollIntoViewIfNeeded();
      await pause(page, 1500);

      await spotlight(page, "Minority Positions", 1500);
      // NARRATOR: "The minority position survived intact — a dissenting
      // view on the 5-year timeline for industrial PETases. That's a
      // feature, not a bug. The system preserves intellectual diversity."
    }

    // Show Key Moments for this completed thread
    await spotlight(page, "Key Moments", 1500);
  }

  // ─── CLOSING SHOT ─────────────────────────────────────────────────────────

  // NARRATOR: "Complex behavior from simple rules. Agents that decide when
  // to speak. A conversation that terminates when it runs out of ideas.
  // A red team that fires when consensus forms too quickly. Institutional
  // memory that grows with every deliberation. And a human who can intervene
  // at any moment to challenge assumptions.
  //
  // This is Colloquium — emergent scientific discourse, powered by
  // Claude Opus 4.6. Not a chatbot. A deliberation engine."

  // Return to home page for the closing shot
  await page.goto("/");
  await pause(page, 2000);

  // Slow pan over all communities
  await scanCards(page, "a[href*='/c/']", 6);
  await pause(page, 3000);

  // END
});
