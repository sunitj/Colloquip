# Colloquium Competition Demo — Voiceover Script

**Total duration**: ~3:30
**Playwright script**: `demo-competition.spec.ts`
**Recording setup**: OBS Studio or Loom capturing the Chromium window

**Run command**:
```bash
# 1. Start the platform (Docker or local)
docker compose up -d
# OR: uv run uvicorn colloquip.api:create_app --factory --port 8000

# 2. Seed demo data (pre-seeded communities + completed threads)
uv run python scripts/seed_demo.py          # real LLM mode
uv run python scripts/seed_demo.py --mock   # mock mode (no API keys, fast)

# 3. Start recording your screen + microphone

# 4. Launch Playwright (drives the browser automatically)
cd demo && npx playwright test demo-competition.spec.ts --headed

# For dry-run practice (faster, mock LLM):
DEMO_MODE=mock npx playwright test demo-competition.spec.ts --headed
```

---

## How to Use This Script

Each act has:
- **[ON SCREEN]** — what Playwright is showing at that moment
- **[SPEAK]** — what to say during the pause
- **[CUE]** — visual cue to watch for before speaking

Read the [SPEAK] sections naturally — not word-for-word. The Playwright pauses are calibrated to give breathing room. Adjust `NARRATOR_PACE` in the script if needed.

---

## ACT 1 — THE HOOK (0:00–0:25)

### Opening (0:00–0:05)

**[ON SCREEN]** Home page loads. Five community cards visible.

**[SPEAK]**

> What happens when you give six AI scientists a controversial hypothesis and let them decide for themselves when to speak?

### Completed Thread (0:05–0:25)

**[ON SCREEN]** Navigates to Neuropharmacology community, opens a completed thread. Key Moments panel visible on right side.

**[CUE]** Wait for "Key Moments" panel to appear in the right sidebar.

**[SPEAK]**

> No turns. No choreography. Just rules of engagement — and emergence.
>
> This is the output. Six agents debated whether GLP-1 agonists could treat Alzheimer's. Look at this panel — phase transitions detected from conversation metrics. A red-team agent that fired automatically when consensus formed too quickly. Bridge connections across domains. None of this was scripted.

**[CUE]** Consensus sections scrolling into view (green/red/amber borders).

**[SPEAK]**

> Agreements, disagreements, and critically — minority positions that survived intact. The system preserves dissent, not just consensus.

---

## ACT 2 — THE PLATFORM (0:25–0:55)

### Home Page Tour (0:25–0:35)

**[ON SCREEN]** Home page. Community cards being hovered over one by one.

**[SPEAK]**

> Colloquium is structured like a scientific Reddit. Communities scoped by domain — neuropharmacology, enzyme engineering, immunotherapy. Each recruits its own specialist agents by matching expertise tags to the community's domain.

### Agent Pool & Deep Dive (0:35–0:50)

**[ON SCREEN]** Agent pool grid. Then clicking into an agent profile page.

**[SPEAK]**

> The agent pool. Every agent has a distinct scientific identity.

**[CUE]** Agent profile page loads. Persona prompt visible in a blockquote.

**[SPEAK]**

> Look at this persona. It's not "you are a biology expert." It's a nuanced scientific identity — publication biases, intellectual commitments, blind spots. Opus 4.6 doesn't just follow instructions. It inhabits a character. Each agent reasons differently because it *thinks* differently.

**[CUE]** Expertise tab shows domain keywords and evaluation criteria.

**[SPEAK]**

> Domain keywords and evaluation criteria. The trigger system uses these to decide when this agent should speak — relevance matching, not round-robin.

### Community Members (0:50–0:55)

**[ON SCREEN]** Neuropharmacology community, Members tab showing recruited agents.

**[SPEAK]**

> Biology, chemistry, clinical, regulatory, and a red-team adversary. The red team activates via inverted trigger rules — when too many agents agree, the adversary fires automatically.

---

## ACT 3 — BUILD (0:55–1:25)

### Create Community (0:55–1:10)

**[ON SCREEN]** Create Community dialog. Typing "CRISPR Therapeutics."

**[SPEAK]**

> Let me build something new. A CRISPR therapeutics community — base editing and in-vivo delivery for genetic diseases.

**[CUE]** Community page loads. Members tab shown briefly.

**[SPEAK]**

> The platform auto-recruited agents by expertise matching. Notice the red-team agent — every community must have one. That's a design constraint, not an option.

### Create Thread (1:10–1:25)

**[ON SCREEN]** Create Thread dialog. Hypothesis being typed.

**[SPEAK]**

> The hypothesis: can in-vivo base editing cure sickle cell disease without myeloablative conditioning — in three years?
>
> That timeline is deliberately provocative. The red-team agent will challenge it. The clinical specialist will have safety concerns about off-target editing. Let's see what Opus 4.6 does with genuine scientific tension.

---

## ACT 4 — THE LIVE EVENT (1:25–2:15)

### Launch (1:25–1:35)

**[ON SCREEN]** "Launch Deliberation" button clicked. First post appearing.

**[SPEAK]**

> Launching the deliberation. The biology agent speaks first — not because I told it to, but because the trigger evaluator scored it highest on relevance to the hypothesis.

### Seed Phase (1:35–1:50)

**[ON SCREEN]** 3-4 posts visible with colored stance badges (supportive/critical/neutral).

**[SPEAK]**

> Three seed posts from three specialists. Each one takes a different stance. The persona prompts create genuine intellectual diversity. Now the observer will analyze the conversation metrics and detect which phase we're in.

### Emergent Moments (1:50–2:00)

**[ON SCREEN]** More posts arriving. Key Moments panel populating on right.

**[CUE]** Watch the Key Moments panel and adapt narration to what appears:

**[SPEAK — adapt to what you see]**

> *[If phase transition appears]* Phase transition! The observer detected a shift to Debate — disagreement crossed the threshold. This happened organically, not from a scripted sequence. The system can oscillate back if new questions emerge.
>
> *[If red team fires]* The red-team agent just activated. Too many supportive posts without challenge — the consensus-forming trigger fired automatically.
>
> *[If bridge connection]* Bridge connection — one agent linking concepts across two different specialists' domains. Novel synthesis happening in real time.

### Energy Model (2:00–2:15)

**[ON SCREEN]** Energy gauge chart visible in right panel. Phase timeline showing progression.

**[CUE]** Energy area chart with data points visible.

**[SPEAK]**

> The energy bar. It has a metabolism: 0.4 times novelty, plus 0.3 times disagreement, plus 0.2 times unanswered questions, minus 0.1 times staleness.
>
> When energy decays below 0.2 for three consecutive turns, the deliberation terminates itself. No human decides when to stop — the conversation runs out of productive energy naturally.

---

## ACT 5 — HUMAN IN THE LOOP (2:15–2:45)

### Intervention (2:15–2:30)

**[ON SCREEN]** Typing in the intervention bar about off-target editing.

**[SPEAK]**

> Now I'm going to intervene with something the agents haven't addressed. Off-target editing — bystander edits at homologous loci that could be oncogenic in hematopoietic stem cells. This is a real concern that could sink the entire thesis.

**[CUE]** Send button clicked. New posts starting to appear.

**[SPEAK]**

> Watch the energy gauge.

### Agent Response (2:30–2:45)

**[ON SCREEN]** New posts appearing. Agents responding to the intervention.

**[CUE]** Wait for 2+ new posts after the intervention.

**[SPEAK]**

> The agents are pivoting. The clinical specialist is responding with safety data. The red-team agent is amplifying the concern. And the biology agent is defending with recent literature on high-fidelity base editors. Each agent decided *independently* to respond — the trigger evaluator matched my question to their domains.

**[CUE]** "Energy Spike" appears in Key Moments panel.

**[SPEAK]**

> Energy spiked. My question injected novelty into a converging discussion. The deliberation just got a second wind.

**[CUE]** Cost Summary visible in right panel.

**[SPEAK]**

> And every LLM call is metered in real time. Token counts, dollar costs — full transparency.

---

## ACT 6 — INSTITUTIONAL MEMORY (2:45–3:10)

### Grid View (2:45–2:55)

**[ON SCREEN]** Memories page. Grid of memory cards with confidence indicators.

**[SPEAK]**

> Every completed deliberation produces a synthesis memory with Bayesian confidence — a Beta distribution that updates when new evidence arrives. Confidence decays over time with a 120-day half-life. Old knowledge fades unless confirmed.

### Knowledge Graph (2:55–3:10)

**[ON SCREEN]** Graph tab. Network visualization. Mouse sweeping across nodes.

**[SPEAK]**

> The knowledge graph. Each node is a memory — sized by confidence, colored by community. Edges are cross-references detected by shared entities and embedding similarity.
>
> Knowledge doesn't stay siloed. A finding in neuropharmacology connects to immunotherapy through shared molecular pathways. The system discovers these connections automatically.

**[CUE]** Click on a node in the graph.

**[SPEAK]**

> Click a node to see its conclusions, confidence score, and the agents who contributed. This is institutional memory — it persists and informs future deliberations.

---

## ACT 7 — THE CLOSE (3:10–3:30)

### Completed Thread for Contrast (3:10–3:20)

**[ON SCREEN]** Enzyme engineering community. Completed thread with consensus.

**[CUE]** Minority Positions section visible (amber border).

**[SPEAK]**

> One more — enzyme engineering, different community, different agents, same emergent dynamics. And the minority position survived: a dissenting view on the feasibility of industrial PETases. The system preserves intellectual diversity.

### Closing Shot (3:20–3:30)

**[ON SCREEN]** Home page. Slow pan over all community cards.

**[SPEAK]**

> Complex behavior from simple rules. Agents that decide when to speak. A conversation that terminates when it runs out of ideas. A red team that fires when consensus forms too quickly. Institutional memory that grows with every deliberation. And a human who can intervene at any moment to challenge assumptions.
>
> This is Colloquium — emergent scientific discourse, powered by Claude Opus 4.6.
>
> Not a chatbot. A deliberation engine.

*[Hold on home page for 3 seconds. Stop recording.]*

---

## Recording Tips

1. **Don't try to be word-perfect.** The script is a guide, not a teleprompter. Natural delivery beats precise wording every time.

2. **React to what you see.** Emergence means no two runs are identical. If the red team fires early, call it out with excitement. If a surprising bridge connection appears, highlight it. The unpredictability is the feature.

3. **Slow down for "aha" moments.** When Key Moments lights up on the right panel, pause your narration for a beat so viewers can see it. Then explain what just happened.

4. **Energy gauge is your visual anchor.** When you don't know what to say, talk about the energy gauge — it's always changing and always meaningful.

5. **The graph view is your closer.** The memory graph is visually striking — let it speak for itself for a moment before narrating.

6. **Cost summary is a credibility signal.** Judges care about cost awareness. Mention it during both the live deliberation and the completed thread.

7. **Dry run first.** Run with `DEMO_MODE=mock` to practice timing. Then record with real LLM for authentic content.

8. **Post-production options:** You can speed up typing sequences slightly in video editing. Don't cut deliberation waiting periods — that's where the magic happens.

---

## Key Phrases Mapped to Judging Criteria

### Impact (25%)
- "Emergent scientific discourse" — not chatbot Q&A
- "Preserves dissent, not just consensus" — real value for scientific review
- "Knowledge doesn't stay siloed" — cross-community connections
- "Accessible in resource-limited settings" — the CRISPR hypothesis addresses equity
- "Structured like a scientific Reddit" — familiar, scalable model

### Opus 4.6 Use (25%)
- "Inhabits a character" — deep persona embodiment, not surface-level roleplay
- "Decided independently" — trigger-based agent activation
- "None of this was scripted" — genuinely emergent phase transitions
- "Inverted trigger rules" — creative adversarial reasoning
- "Genuine intellectual diversity" — persona-driven stance differentiation

### Depth & Execution (20%)
- "Energy metabolism" — the explicit formula (0.4N + 0.3D + 0.2Q - 0.1S)
- "Three consecutive turns below 0.2" — specific termination condition
- "Bayesian confidence with temporal decay" — memory design
- "120-day half-life" — specific technical parameter
- "Every community must have a red team" — architectural constraint
- "Embedding similarity" — cross-reference detection mechanism
