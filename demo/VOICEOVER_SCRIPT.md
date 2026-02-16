# Colloquium Demo — Voiceover Script (3 minutes)

**Recording setup**: Playwright drives the browser. You record your screen (OBS/QuickTime/Loom) and narrate live. Speak during the pauses — the script has breathing room built in. If the browser is ahead of your narration, that's fine — the pauses will catch up.

**Run command**:
```bash
# 1. Start backend
uv run uvicorn colloquip.api:create_app --factory --port 8000

# 2. Seed demo data (run once)
uv run python scripts/seed_demo.py          # real mode (needs ANTHROPIC_API_KEY)
uv run python scripts/seed_demo.py --mock   # mock mode (no keys, fast)

# 3. Start recording your screen + microphone

# 4. Launch Playwright (it will drive the browser)
cd demo && npx playwright test demo-v2.spec.ts --headed
```

---

## ACT 1 — THE HOOK (0:00–0:25)
*[Screen: Home page with pre-seeded communities, then into a completed thread]*

> Multi-agent AI today is choreographed. Agent A speaks, then B, then C, repeat. The output is predictable because the process is predictable.
>
> What if instead, agents decided *for themselves* when to speak — and the conversation organized itself?
>
> This is Colloquium. And this [gesture at consensus on screen] is what it produces — structured scientific consensus with preserved minority positions. None of this was scripted.

*[Playwright scrolls through the consensus sections — agreements, disagreements, minority positions]*

---

## ACT 2 — PLATFORM TOUR (0:25–0:50)
*[Screen: Home page showing all communities, then agent pool, then community members]*

> Colloquium is structured like a scientific Reddit. Communities scope deliberations by domain — here we have Neuropharmacology, Enzyme Engineering, Immuno-Oncology, Synthetic Biology.
>
> [Agent pool appears] Each community recruits from a shared pool of specialist agents. Biology, chemistry, clinical, regulatory, computational — and every community must have a red-team adversary.

*[Playwright shows neuropharmacology Members tab]*

> This community has six agents recruited by expertise. The red-team agent exists for one reason: to challenge premature consensus. It activates *automatically* when other agents agree too easily.

*[Playwright flashes immuno-oncology members for contrast]*

> Different community, different agent roster. Same deliberation engine underneath.

---

## ACT 3 — LAUNCH LIVE (0:50–1:05)
*[Screen: Thread creation, then launch]*

> Now let's watch a deliberation happen live. I'm posing a hypothesis about repurposing semaglutide — a GLP-1 diabetes drug — for Alzheimer's disease.
>
> Six agents are about to debate this. I didn't assign turns. I didn't choreograph who speaks when. Let's see what happens.

*[Playwright launches deliberation, first posts start appearing]*

---

## ACT 4 — THE EMERGENT DANCE (1:05–1:50)
*[Screen: Live deliberation running, posts arriving, right panel updating]*

**This is the most important section. Narrate what you see on screen. These are your cue phrases — speak them when you see the corresponding event in the "Key Moments" panel on the right:**

### When the first posts arrive:
> The biology agent spoke first — it had the highest relevance score for this hypothesis. No one told it to go first.

### When a phase transition appears (Key Moments: "Phase: Explore → Debate"):
> Phase transition! The observer detected a shift to Debate. This happened because disagreement crossed the threshold — not because anyone told the system to change phases.

### When red team fires (Key Moments: "Red Team: [name]"):
> There — the red team agent just activated. Three agents agreed without challenge, and it fired *automatically*. That's the consensus-forming trigger. The adversary exists to prevent premature convergence.

### When a bridge connection appears (Key Moments: "Bridge: [name]"):
> Bridge trigger — this agent just connected concepts across two different specialists' domains. That's a novel synthesis that neither agent would have produced alone.

### When you see the energy gauge declining:
> Watch the energy bar on the right. It's been declining as arguments repeat and novelty decreases. The conversation has a metabolism — it runs out of steam naturally.

### General filler if needed:
> Notice only [N] agents responded this round. The others stayed silent — nothing triggered them. They'll speak when they have something relevant to add.

---

## ACT 5 — HUMAN INTERVENTION (1:50–2:15)
*[Screen: Typing intervention into the bar, energy spike visible]*

> I'm going to ask a hard question the agents haven't addressed: does semaglutide actually cross the blood-brain barrier?

*[Playwright types and submits the question]*

> Watch the energy gauge...

*[Pause — wait for the agents to respond and energy to update]*

> Energy spiked. My question injected novelty into the conversation. The agents are now responding to something none of them raised on their own. The deliberation just got new life.

---

## ACT 6 — PRE-SEEDED DEPTH (2:15–2:40)
*[Screen: Navigating to a completed enzyme engineering thread]*

> While that deliberation continues, let me show you a completed one in a different community — Enzyme Engineering, debating whether PETases can degrade plastic at industrial scale.

*[Playwright shows the completed thread and Key Moments]*

> Look at the Key Moments panel — you can see every phase transition, every red-team challenge, every bridge connection that happened during this deliberation. This is the forensic trail of emergence.

*[Playwright scrolls through consensus]*

> The consensus preserves disagreement. These aren't averaged opinions — the minority position that PETases need at least a decade, not five years, survived the deliberation intact. That's a feature, not a bug.

---

## ACT 7 — CLOSE (2:40–3:00)
*[Screen: Home page with all communities]*

> Every conclusion just became a memory with Bayesian confidence. The next deliberation in this community will build on what these agents learned today.
>
> Complex behavior from simple rules. Agents that decide when to speak. A conversation that terminates when it runs out of ideas, not when it runs out of turns.
>
> That's Colloquium — emergent scientific discourse, powered by Claude.

*[Hold on home page for 3 seconds, then stop recording]*

---

## TIPS FOR RECORDING

1. **Don't try to be word-perfect.** The script is a guide, not a teleprompter. Natural delivery beats precise wording.

2. **React to what you see.** If the red team fires early, great — call it out. If it fires late, adapt. The emergent moments are real and unpredictable.

3. **Slow down for the "aha" moments.** When the Key Moments panel lights up, pause your narration for a beat so viewers can see it. Then explain what just happened.

4. **Don't panic if timing is off.** The Playwright pauses are generous. If the deliberation runs slow (real LLM mode), the script waits. You may need to stretch or compress your narration.

5. **Do a dry run with `--mock` first.** Run the whole thing once in mock mode to practice timing. Then do the real recording in real LLM mode for authentic content.

6. **Energy gauge is your visual anchor.** When you don't know what to say, talk about the energy gauge — it's always changing and always meaningful.
