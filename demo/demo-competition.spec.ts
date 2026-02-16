/**
 * Colloquium Competition Demo — 3-Minute Video
 *
 * Optimized for judging criteria:
 *   - Impact (25%): Real-world potential for scientific deliberation
 *   - Opus 4.6 Use (25%): Emergent agent behavior, self-organizing phases, red-team
 *   - Depth & Execution (20%): Energy model, triggers, institutional memory
 *
 * Story Arc (strict 3:00):
 *   Act 1 (0:00–0:20)  — THE HOOK: Completed consensus reveal
 *   Act 2 (0:20–0:40)  — THE PLATFORM: Communities, agent persona deep-dive
 *   Act 3 (0:40–1:05)  — BUILD: Create community + thread
 *   Act 4 (1:05–1:50)  — THE LIVE EVENT: Launch, watch emergence
 *   Act 5 (1:50–2:15)  — HUMAN IN THE LOOP: Intervene, energy spike
 *   Act 6 (2:15–2:35)  — INSTITUTIONAL MEMORY: Knowledge graph
 *   Act 7 (2:35–3:00)  — THE CLOSE: Final narration + home page
 *
 * Prerequisites:
 *   1. Platform running: docker compose up -d
 *   2. Seed data loaded: uv run python scripts/seed_demo.py [--mock]
 *   3. Run: cd demo && npm run demo:competition
 */

import { test, expect, type Page } from "@playwright/test";

// ─── Configuration ──────────────────────────────────────────────────────────

/** Narrator pace multiplier: 1.0 = normal, 1.2 = breathing room, 0.8 = tight */
const NARRATOR_PACE = 1.0;

/** Use mock LLM for dry runs (set DEMO_MODE=mock env var) */
const USE_MOCK = process.env.DEMO_MODE === "mock";

// ─── Helpers ────────────────────────────────────────────────────────────────

async function pause(page: Page, ms: number) {
  await page.waitForTimeout(ms * NARRATOR_PACE);
}

async function typeSlowly(page: Page, selector: string, text: string) {
  await page.click(selector);
  await page.type(selector, text, { delay: 25 });
}

async function postCount(page: Page): Promise<number> {
  return page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .count();
}

async function scrollToLatestPost(page: Page) {
  const post = page
    .locator('[style*="border-left-width: 3px"], [style*="border-left: 3px"]')
    .last();
  if (await post.isVisible().catch(() => false)) {
    await post.scrollIntoViewIfNeeded();
  }
}

async function waitForPosts(page: Page, n: number, timeout = 60_000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await postCount(page)) >= n) return;
    await page.waitForTimeout(1500);
  }
}

async function spotlight(page: Page, text: string, duration = 1200) {
  const el = page.locator(`text=${text}`).first();
  if (await el.isVisible().catch(() => false)) {
    await el.scrollIntoViewIfNeeded();
    await pause(page, duration);
    return true;
  }
  return false;
}

async function scanCards(page: Page, selector: string, maxCards = 4) {
  const cards = page.locator(selector);
  const count = await cards.count();
  for (let i = 0; i < Math.min(count, maxCards); i++) {
    const card = cards.nth(i);
    if (await card.isVisible().catch(() => false)) {
      await card.hover();
      await pause(page, 400);
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

// ─── The 3-Minute Demo ─────────────────────────────────────────────────────

test("Colloquium — 3-Minute Competition Demo", async ({ page }) => {
  test.setTimeout(USE_MOCK ? 300_000 : 600_000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 1 — THE HOOK (0:00–0:20)
  //
  // NARRATOR: "What happens when you give six AI scientists a controversial
  // hypothesis and let them decide for themselves when to speak? No turns.
  // No choreography. Just rules of engagement — and emergence."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await expect(page.locator("text=Welcome to Colloquium")).toBeVisible();
  await pause(page, 2000);

  // Jump straight into a completed thread
  const neuroLink = page.locator("a", { hasText: "Neuropharmacology" }).first();
  if (await neuroLink.isVisible().catch(() => false)) {
    await neuroLink.click();
    await page.waitForURL(/\/c\/neuropharmacology/);
    await pause(page, 800);

    const threadsTab = page.locator('[role="tab"]', { hasText: "Threads" });
    if (await threadsTab.isVisible().catch(() => false)) {
      await threadsTab.click();
      await pause(page, 400);
    }

    const firstThread = page.locator("a[href*='/thread/']").first();
    if (await firstThread.isVisible().catch(() => false)) {
      await firstThread.click();
      await page.waitForURL(/\/thread\//);
      await pause(page, 1200);

      // Show Key Moments — the hook
      // NARRATOR: "Phase transitions, red-team challenges, bridge
      // connections — none of this was scripted."
      await spotlight(page, "Key Moments", 1800);

      // Flash consensus sections
      const consensusEl = page.locator("text=Consensus Reached").first();
      if (await consensusEl.isVisible().catch(() => false)) {
        await consensusEl.scrollIntoViewIfNeeded();
        await pause(page, 1000);
        await spotlight(page, "Agreements", 800);
        await spotlight(page, "Minority Positions", 1000);
        // NARRATOR: "The system preserves dissent, not just consensus."
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 2 — THE PLATFORM (0:20–0:40)
  //
  // NARRATOR: "Colloquium is like a scientific Reddit. Communities by domain.
  // Persistent agents with real expertise profiles."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await pause(page, 1000);
  await scanCards(page, "a[href*='/c/']", 4);
  await pause(page, 500);

  // Agent pool — quick scan then deep-dive one agent
  await page.goto("/agents");
  await page
    .waitForSelector('[class*="grid"] a', { timeout: 10_000 })
    .catch(() => {});
  await pause(page, 1500);

  // NARRATOR: "Each agent has a distinct scientific identity."

  // Deep-dive: show a persona prompt
  const firstAgent = page.locator("a[href*='/agents/']").first();
  if (await firstAgent.isVisible().catch(() => false)) {
    await firstAgent.click();
    await page.waitForURL(/\/agents\//);
    await pause(page, 1200);

    // NARRATOR: "Not 'you are a biology expert.' A nuanced identity —
    // publication biases, blind spots. Opus 4.6 inhabits a character."
    await spotlight(page, "Persona", 2000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 3 — BUILD (0:40–1:05)
  //
  // NARRATOR: "Let me build something new. A CRISPR therapeutics community
  // with a provocative hypothesis."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await pause(page, 400);

  // Create community
  const createBtn = page.locator("button", { hasText: "Create Community" });
  await createBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 300);

  await typeSlowly(page, 'input[placeholder*="drug_discovery"]', NEW_COMMUNITY.slug);
  await typeSlowly(page, 'input[placeholder*="Drug Discovery"]', NEW_COMMUNITY.displayName);
  await typeSlowly(page, 'textarea[placeholder*="purpose"]', NEW_COMMUNITY.description);
  await typeSlowly(page, 'input[placeholder*="pharmaceutical"]', NEW_COMMUNITY.primaryDomain);
  await pause(page, 300);

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/c\//, { timeout: 10_000 });
  await pause(page, 800);

  // Flash members tab — show auto-recruitment
  // NARRATOR: "Auto-recruited by expertise. Every community must have
  // a red-team adversary."
  const membersTab = page.locator('[role="tab"]', { hasText: "Members" });
  if (await membersTab.isVisible().catch(() => false)) {
    await membersTab.click();
    await pause(page, 1500);
    await page.locator('[role="tab"]', { hasText: "Threads" }).click();
    await pause(page, 300);
  }

  // Create thread
  const newThreadBtn = page
    .locator("button", { hasText: /New Thread|Create First Thread/ })
    .first();
  await newThreadBtn.click();
  await expect(page.locator('[role="dialog"]')).toBeVisible();
  await pause(page, 300);

  await typeSlowly(page, 'input[placeholder="Deliberation title"]', NEW_THREAD.title);
  await typeSlowly(page, 'textarea[placeholder*="hypothesis"]', NEW_THREAD.hypothesis);
  await pause(page, 400);

  // NARRATOR: "Can in-vivo base editing cure sickle cell — in three years?
  // That timeline will trigger the red-team agent."

  await page.locator('[role="dialog"] button[type="submit"]').click();
  await page.waitForURL(/\/thread\//, { timeout: 10_000 });
  await pause(page, 600);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 4 — THE LIVE EVENT (1:05–1:50)
  //
  // NARRATOR: "Launching. Watch the right panel — Key Moments lights up
  // when something emergent happens."
  // ═══════════════════════════════════════════════════════════════════════════

  // Select LLM mode
  const modeSelect = page.locator('button[role="combobox"]');
  if (await modeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await modeSelect.click();
    const modeLabel = USE_MOCK ? "Mock" : "claude-opus-4-6";
    await page.locator('[role="option"]', { hasText: modeLabel }).click();
    await pause(page, 200);
  }

  // Launch
  const launchBtn = page.locator("button", { hasText: "Launch Deliberation" });
  await expect(launchBtn).toBeVisible({ timeout: 5_000 });
  await launchBtn.click();

  // Wait for first post
  await page.waitForSelector(
    '[style*="border-left-width: 3px"], [style*="border-left: 3px"]',
    { timeout: USE_MOCK ? 30_000 : 120_000 },
  );
  await pause(page, 1200);

  // NARRATOR: "Biology agent speaks first — highest relevance score.
  // No one told it to go first."

  // Wait for seed posts
  await waitForPosts(page, 3, USE_MOCK ? 30_000 : 120_000);
  await scrollToLatestPost(page);
  await pause(page, 1500);

  // Main deliberation loop — 5 iterations, spotlight key panels
  for (let i = 0; i < 5; i++) {
    await page.waitForTimeout(3500 * NARRATOR_PACE);
    await scrollToLatestPost(page);

    // Spotlight Key Moments
    const keyMoments = page.locator("text=Key Moments").first();
    if (await keyMoments.isVisible().catch(() => false)) {
      await keyMoments.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1000);
    }

    // At iteration 2, spotlight energy gauge
    if (i === 2) {
      const energyLabel = page.locator("text=Energy").first();
      if (await energyLabel.isVisible().catch(() => false)) {
        await energyLabel.scrollIntoViewIfNeeded().catch(() => {});
        await pause(page, 1200);
        // NARRATOR: "The energy bar has a metabolism:
        // 0.4*novelty + 0.3*disagreement + 0.2*questions - 0.1*staleness.
        // Below 0.2 for three turns, the conversation terminates itself."
      }
    }

    // At iteration 4, spotlight phase progress
    if (i === 4) {
      const phaseLabel = page.locator("text=Phase Progress").first();
      if (await phaseLabel.isVisible().catch(() => false)) {
        await phaseLabel.scrollIntoViewIfNeeded().catch(() => {});
        await pause(page, 1000);
        // NARRATOR: "Phase transitions — detected from metrics, not
        // scripted. The system can oscillate back."
      }
    }

    await scrollToLatestPost(page);
  }

  await waitForPosts(page, 5, USE_MOCK ? 20_000 : 120_000);
  await scrollToLatestPost(page);
  await pause(page, 1000);

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 5 — HUMAN IN THE LOOP (1:50–2:15)
  //
  // NARRATOR: "Now I'll challenge them on off-target editing — something
  // none of them raised. Watch the energy gauge."
  // ═══════════════════════════════════════════════════════════════════════════

  const interventionBar = page.locator('textarea[placeholder*="Intervene"]');
  if (await interventionBar.isVisible().catch(() => false)) {
    await typeSlowly(page, 'textarea[placeholder*="Intervene"]', INTERVENTION);
    await pause(page, 800);

    await page.locator("button", { hasText: "Send" }).click();
    await pause(page, 800);

    // Wait for agent responses
    const preCount = await postCount(page);
    await waitForPosts(page, preCount + 2, USE_MOCK ? 30_000 : 120_000);
    await scrollToLatestPost(page);
    await pause(page, 2000);

    // NARRATOR: "Agents pivoting independently — clinical specialist
    // with safety data, red team amplifying, biology defending.
    // Each decided to respond via trigger matching."

    // Show energy spike if visible
    const spikeLabel = page.locator("text=Energy Spike").first();
    if (await spikeLabel.isVisible().catch(() => false)) {
      await spikeLabel.scrollIntoViewIfNeeded().catch(() => {});
      await pause(page, 1500);
      // NARRATOR: "Energy spiked. The deliberation got a second wind."
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 6 — INSTITUTIONAL MEMORY (2:15–2:35)
  //
  // NARRATOR: "Every deliberation produces a memory with Bayesian
  // confidence — 120-day half-life, updated by annotations and outcomes."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/memories");
  await pause(page, 1500);

  // Quick grid scan
  await scanCards(page, '[class*="grid"] > *', 3);

  // Switch to Graph view — the visual payoff
  const graphTab = page.locator('[role="tab"]', { hasText: "Graph" });
  if (await graphTab.isVisible().catch(() => false)) {
    await graphTab.click();
    await pause(page, 2500);

    // NARRATOR: "The knowledge graph. Nodes sized by confidence,
    // colored by community. Cross-references detected automatically."

    // Quick sweep across graph
    const graphCanvas = page.locator("canvas").first();
    if (await graphCanvas.isVisible().catch(() => false)) {
      const box = await graphCanvas.boundingBox();
      if (box) {
        for (let x = 0.25; x <= 0.75; x += 0.15) {
          await page.mouse.move(
            box.x + box.width * x,
            box.y + box.height * 0.5,
          );
          await pause(page, 500);
        }
        await page.mouse.click(
          box.x + box.width * 0.5,
          box.y + box.height * 0.45,
        );
        await pause(page, 1500);
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACT 7 — THE CLOSE (2:35–3:00)
  //
  // NARRATOR: "Complex behavior from simple rules. Agents that decide
  // when to speak. A conversation that terminates when it runs out of
  // ideas. A red team that fires when consensus forms too quickly.
  // Institutional memory that grows with every deliberation.
  //
  // This is Colloquium — emergent scientific discourse, powered by
  // Claude Opus 4.6. Not a chatbot. A deliberation engine."
  // ═══════════════════════════════════════════════════════════════════════════

  await page.goto("/");
  await pause(page, 1500);

  // Slow pan over communities — the closing shot
  await scanCards(page, "a[href*='/c/']", 5);
  await pause(page, 3000);

  // END
});
