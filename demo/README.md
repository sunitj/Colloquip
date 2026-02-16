# Colloquip Demo — 3-Minute Competition Video

Automated Playwright script that showcases two simultaneous deliberations running concurrently on the Colloquip platform.

## Story Arc — Dual Deliberation

| Time | Act | What Happens |
|------|-----|-------------|
| 0:00–0:25 | **Platform Overview** | Home page, initialize platform, browse agent pool |
| 0:25–1:05 | **Create & Configure** | Enter community, view members, create **both** threads |
| 1:05–1:15 | **Launch Thread 1** | Start the drug repurposing deliberation |
| 1:15–1:50 | **Launch Thread 2** | Open a second tab, launch protein engineering — Thread 1 keeps running |
| 1:50–2:20 | **Cross-cut** | Flip between both live tabs — agents debating concurrently |
| 2:20–2:40 | **Human Intervention** | Inject a question into the protein engineering deliberation |
| 2:40–3:00 | **Consensus Reveal** | Show consensus: agreements, disagreements, minority positions, stances |

## The Two Hypotheses

**Thread 1 — Drug Repurposing:**
> *"Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's disease is a viable therapeutic strategy, given emerging evidence of neuroinflammatory pathway modulation and improved cognitive outcomes in diabetic cohorts."*

**Thread 2 — Protein Engineering:**
> *"Combining machine-learning-guided directed evolution with computational protein design (RFdiffusion / ProteinMPNN) can produce de novo enzymes with catalytic efficiencies rivaling natural enzymes within 3 rounds of experimental screening."*

These were chosen because they:
- Span multiple agent domains (biology, chemistry, clinical, regulatory, red-team)
- Have genuine scientific tension (red-team agents will challenge both)
- Are timely topics that resonate with both specialist and general audiences
- Running both at once showcases concurrency — the platform's key differentiator

## Prerequisites

1. **Backend** running on port 8000:
   ```bash
   uv sync --group dev
   uv run uvicorn colloquip.api:create_app --factory --reload --port 8000
   ```

2. **Frontend** dev server running on port 5173:
   ```bash
   cd web && npm install && npm run dev
   ```

3. **Demo dependencies** installed:
   ```bash
   cd demo && npm install && npx playwright install chromium
   ```

## Running the Demo

### Headed mode (for screen recording)
```bash
cd demo
npm run demo
```

The video is automatically saved to `demo/test-results/`.

### Tips for Recording

- Use OBS or similar to capture the Chromium window
- The script uses two browser tabs (pages) — when recording, capture the whole browser window to show tab switching
- `slowMo: 60` in the config makes interactions feel natural
- Adjust `pause()` durations in `demo.spec.ts` to fine-tune timing
- For a shorter/longer demo, tweak the wait times in Acts 5–7

### Customizing

- **Different hypotheses**: Edit `THREAD_1` and `THREAD_2` constants at the top of the script
- **Faster pacing**: Reduce `pause()` durations and `slowMo` in `playwright.config.ts`
- **Single deliberation**: Comment out Acts 4–6 and use the original single-thread flow
- **Different theme**: Add a theme switch step in Act 1 (visit Settings, click a theme card)
- **Different intervention**: Edit the `typeSlowly` text in Act 6
