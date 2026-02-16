# Colloquium Demo — Voiceover Script (~3.5 minutes)

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

## ACT 1 — THE HOOK (0:00–0:30)
*[Screen: Home page with 5 pre-seeded communities, then into a completed thread]*

> Multi-agent AI today is choreographed. Agent A speaks, then B, then C, repeat. The output is predictable because the process is predictable.
>
> What if instead, agents decided *for themselves* when to speak — and the conversation organized itself?
>
> This is Colloquium. And this [gesture at right panel] is what it produces.

*[Playwright opens a completed thread and shows Key Moments panel]*

> Look at this trail — phase transitions detected from conversation metrics, a red-team agent that fired automatically when others agreed too easily, bridge connections across domains. None of this was scripted.

*[Playwright scrolls to consensus, then Agreements and Minority Positions]*

> Structured consensus with preserved minority positions. And every token is metered — you can see the cost right here.

*[Playwright scrolls to Cost Summary in right panel]*

---

## ACT 2 — PLATFORM TOUR (0:30–1:00)
*[Screen: Home page showing all 5 communities, then agent pool, then community members]*

> Colloquium is structured like a scientific Reddit. Five communities — Neuropharmacology, Enzyme Engineering, Immuno-Oncology, Synthetic Biology, and Microbiome Therapeutics. Each scopes deliberations by domain.

*[Playwright hovers over all 5 community cards]*

> [Agent pool appears] Each community recruits from a shared pool of specialist agents. Biology, chemistry, clinical, regulatory, computational — and every community must have a red-team adversary.

*[Playwright shows neuropharmacology Members tab]*

> This community has six agents recruited by expertise. The red-team agent exists for one reason: to challenge premature consensus. It activates *automatically* when other agents agree too easily.

*[Playwright flashes microbiome community members]*

> The Microbiome community — different domain, different agent roster. But notice — one of its threads overlaps with Immuno-Oncology. The system can detect cross-community connections through shared entities and embedding similarity.

---

## ACT 3 — LAUNCH LIVE (1:00–1:15)
*[Screen: Thread creation, then launch]*

> Now let's watch a deliberation happen live. I'm posing a hypothesis about repurposing semaglutide — a GLP-1 diabetes drug — for Alzheimer's disease.
>
> Six agents are about to debate this. I didn't assign turns. I didn't choreograph who speaks when. Let's see what happens.

*[Playwright launches deliberation, first posts start appearing]*

---

## ACT 4 — THE EMERGENT DANCE (1:15–2:05)
*[Screen: Live deliberation running, posts arriving, right panel updating]*

**This is the most important section. Narrate what you see on screen. These are your cue phrases — speak them when you see the corresponding event in the "Key Moments" panel on the right:**

### When the first posts arrive:
> The biology agent spoke first — it had the highest relevance score for this hypothesis. No one told it to go first.

### When a phase transition appears (Key Moments: "Phase: Explore → Debate"):
> Phase transition! The observer detected a shift to Debate. This happened because disagreement crossed the threshold — not because anyone told the system to change phases.

### When red team fires (Key Moments: "Red Team: [name]"):
> There — the red team agent just activated. Agents agreed without challenge, and the adversary fired *automatically*. That's the consensus-forming trigger.

### When a bridge connection appears (Key Moments: "Bridge: [name]"):
> Bridge trigger — this agent just connected concepts across two different specialists' domains. Novel synthesis that neither agent would have produced alone.

### When you see the energy gauge declining:
> Watch the energy bar on the right. It has a metabolism — novelty drives it up, repetition drives it down. The conversation runs out of steam naturally.

### When Cost Summary updates mid-deliberation (~halfway through):
> And every single LLM call is tracked. You can see the token count and estimated cost updating in real time.

### General filler if needed:
> Notice only [N] agents responded this round. The others stayed silent — nothing triggered them. They'll speak when they have something relevant to add.

---

## ACT 5 — HUMAN INTERVENTION (2:05–2:30)
*[Screen: Typing intervention into the bar, energy spike visible]*

> I'm going to ask a hard question the agents haven't addressed: does semaglutide actually cross the blood-brain barrier?

*[Playwright types and submits the question]*

> Watch the energy gauge...

*[Pause — wait for the agents to respond and energy to update]*

> Energy spiked. My question injected novelty into the conversation. The agents are now responding to something none of them raised on their own. The deliberation just got new life.

*[If "Human →" appears in Key Moments]*

> The Key Moments panel picked it up — human intervention triggered new agent responses.

---

## ACT 6 — PRE-SEEDED DEPTH + CROSS-COMMUNITY (2:30–3:00)
*[Screen: Navigating to a completed enzyme engineering thread]*

> While that deliberation continues, let me show you a completed one — Enzyme Engineering, debating whether PETases can degrade plastic at industrial scale.

*[Playwright shows the completed thread, Key Moments, and consensus]*

> Look at the Key Moments panel — every phase transition, every red-team challenge. This is the forensic trail of emergence.

*[Playwright scrolls through consensus sections]*

> The consensus preserves disagreement. The minority position survived the deliberation intact. That's a feature, not a bug.

*[Playwright navigates to microbiome community, clicks cross-community thread]*

> Now here's something powerful — this thread in the Microbiome community overlaps with Immuno-Oncology. Gut microbiome signatures as predictors of immunotherapy response. The system detects shared entities between communities' memories — cross-pollination of institutional knowledge.

---

## ACT 7 — INSTITUTIONAL MEMORY: THE GRAPH (3:00–3:20)
*[Screen: /memories page, grid view then graph view]*

> Every completed deliberation produces a memory with Bayesian confidence — it starts from the synthesis and gets updated by human annotations and real-world outcomes.

*[Playwright switches to Graph tab]*

> Switch to the graph view. Each node is a memory — sized by confidence, colored by community. Edges are cross-references detected by shared entities and embedding similarity.

*[Playwright sweeps mouse across graph, clicks a node]*

> Click a node and you see the full memory — conclusions, confidence score, the agents who contributed. This is how institutional knowledge accumulates — not just stored, but connected.

*[Playwright switches back to grid]*

---

## ACT 8 — CLOSE (3:20–3:40)
*[Screen: Home page with all 5 communities]*

> Complex behavior from simple rules. Agents that decide when to speak. A conversation that terminates when it runs out of ideas, not when it runs out of turns. Institutional memory that grows and connects with every deliberation. Real-time cost tracking so you know what you're spending.
>
> That's Colloquium — emergent scientific discourse, powered by Claude.

*[Hold on home page for 4 seconds, then stop recording]*

---

## TIPS FOR RECORDING

1. **Don't try to be word-perfect.** The script is a guide, not a teleprompter. Natural delivery beats precise wording.

2. **React to what you see.** If the red team fires early, great — call it out. If it fires late, adapt. The emergent moments are real and unpredictable.

3. **Slow down for the "aha" moments.** When the Key Moments panel lights up, pause your narration for a beat so viewers can see it. Then explain what just happened.

4. **Don't panic if timing is off.** The Playwright pauses are generous. If the deliberation runs slow (real LLM mode), the script waits. You may need to stretch or compress your narration.

5. **Do a dry run with `--mock` first.** Run the whole thing once in mock mode to practice timing. Then do the real recording in real LLM mode for authentic content.

6. **Energy gauge is your visual anchor.** When you don't know what to say, talk about the energy gauge — it's always changing and always meaningful.

7. **The graph view is your closer.** The memory graph is visually striking — let it speak for itself for a moment before narrating over it.

8. **Cost summary is a credibility signal.** Judges care about cost awareness. Mention it at least once during the live deliberation and once on the completed thread.
