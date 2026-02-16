# Colloquium Demo — 3-Minute Competition Video

Automated Playwright script that showcases two simultaneous deliberations in **different communities** running concurrently on the Colloquium platform.

## Story Arc — Dual Community Deliberation

| Time | Act | What Happens |
|------|-----|-------------|
| 0:00–0:20 | **Platform Overview** | Home page, initialize platform, browse agent pool |
| 0:20–0:55 | **Create Community 1** | Create "Neuropharmacology" community, view recruited agents, create GLP-1 thread |
| 0:55–1:30 | **Create Community 2** | Create "Enzyme Engineering" community (different agents!), create PETase thread |
| 1:30–1:40 | **Launch Thread 1** | Start the drug repurposing deliberation |
| 1:40–2:00 | **Launch Thread 2** | Open a second tab, launch PETase deliberation — Thread 1 keeps running |
| 2:00–2:20 | **Cross-cut** | Flip between both live tabs — agents debating concurrently across communities |
| 2:20–2:40 | **Human Intervention** | Inject questions into **both** threads — challenge the PETase timeline, probe BBB for GLP-1 |
| 2:40–3:00 | **Consensus Reveal** | Show consensus: agreements, disagreements, minority positions, stances |

## The Two Communities & Hypotheses

**Community: Neuropharmacology** (domain: `drug_discovery`)
> *"Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's disease is a viable therapeutic strategy, given emerging evidence of neuroinflammatory pathway modulation and improved cognitive outcomes in diabetic cohorts."*

**Community: Enzyme Engineering** (domain: `protein_engineering`)
> *"Engineered PETase variants (via directed evolution and computational redesign) can achieve sufficient catalytic efficiency and thermostability to serve as a commercially viable industrial process for PET plastic degradation, replacing mechanical recycling within 5 years."*

These were chosen because they:
- Live in **different communities** with different recruited agent pools
- The PETase hypothesis has a deliberately aggressive timeline — the red-team agent and domain experts are likely to reason against it
- The GLP-1 hypothesis has a real biological question (blood-brain barrier penetration) that the human intervention probes
- Both are timely topics that resonate with specialist and general audiences
- Running both at once across communities showcases platform concurrency and domain-scoped agent recruitment

## Human Interventions

The demo includes human participation in **both** deliberations:
1. **Thread 2 (PETase)**: A skeptical challenge — *"I'm skeptical about the 5-year timeline..."* — designed to provoke the model into reasoning against the hypothesis's feasibility claims
2. **Thread 1 (GLP-1)**: A probing scientific question — *"What about the blood-brain barrier?"* — designed to surface nuanced biological reasoning

## Prerequisites

### 1. Clean prior state

```bash
# From repo root — removes databases, caches, prior recordings
./scripts/reset-demo.sh
```

### 2. Start the platform (Docker Compose)

```bash
# From the repo root — builds and starts everything (app + PostgreSQL + Redis)
docker compose up -d

# Verify the app is healthy
docker compose ps
curl http://localhost:8000/health
```

The app serves the React SPA + REST API + WebSocket all on `http://localhost:8000`. No separate frontend server is needed.

> **Without Docker:** If you prefer running locally without containers, start the backend and frontend separately:
> ```bash
> # Terminal 1: Backend
> uv sync --group dev
> uv run uvicorn colloquip.api:create_app --factory --reload --port 8000
>
> # Terminal 2: Frontend (dev server on port 5173)
> cd web && npm install && npm run dev
> ```
> Then update `baseURL` in `playwright.config.ts` to `http://localhost:5173`.

### 3. Install demo dependencies

```bash
cd demo
npm install
npx playwright install chromium
```

## Running the Demo

### Headed mode (for screen recording)
```bash
cd demo
npm run demo
```

The video is automatically saved to `demo/test-results/`.

### Tips for Recording

- Use OBS or Loom to capture the Chromium window
- The script uses two browser tabs (pages) — when recording, capture the whole browser window to show tab switching
- `slowMo: 60` in the config makes interactions feel natural
- Adjust `pause()` durations in `demo.spec.ts` to fine-tune timing
- **Add voiceover** — without narration, judges won't understand the energy model, phase transitions, or trigger-based agent selection

### Customizing

- **Different hypotheses**: Edit `THREAD_1` and `THREAD_2` constants in the script
- **Different communities**: Edit `COMMUNITY_1` and `COMMUNITY_2` constants
- **Faster pacing**: Reduce `pause()` durations and `slowMo` in `playwright.config.ts`
- **Different interventions**: Edit `INTERVENTION_1` and `INTERVENTION_2` constants
- **Different theme**: Add a theme switch step in Act 1 (visit Settings, click a theme card)

### Teardown

```bash
# Stop the platform
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```
