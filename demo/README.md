# Colloquip Demo — 3-Minute Competition Video

Automated Playwright script that walks through the full Colloquip experience for a competition demo recording.

## Story Arc

| Time | Act | What Happens |
|------|-----|-------------|
| 0:00–0:30 | **Platform Overview** | Home page, initialize platform, browse agent pool |
| 0:30–1:00 | **Create & Configure** | Enter community, view members, create a deliberation thread |
| 1:00–2:20 | **Live Deliberation** | Launch session, watch agents debate in real-time with energy/phase tracking |
| 2:20–2:40 | **Human Intervention** | Inject a question mid-deliberation, see agents respond |
| 2:40–3:00 | **Consensus Reveal** | Final consensus: agreements, disagreements, minority positions, stances |

## Demo Hypothesis

> *"Repurposing GLP-1 receptor agonists (semaglutide) for Alzheimer's disease is a viable therapeutic strategy, given emerging evidence of neuroinflammatory pathway modulation and improved cognitive outcomes in diabetic cohorts."*

This was chosen because it:
- Spans multiple agent domains (biology, chemistry, clinical, regulatory)
- Has genuine scientific tension (red-team will challenge)
- Is timely and compelling for a general audience
- Triggers all 5 deliberation phases

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
- The script includes built-in pauses for readability
- `slowMo: 60` in the config makes interactions feel natural
- Adjust `pause()` durations in `demo.spec.ts` to fine-tune timing
- For a shorter/longer demo, change `maxWatchTime` in Act 3

### Customizing

- **Different hypothesis**: Edit the `typeSlowly` call in Act 2
- **Faster pacing**: Reduce `pause()` durations and `slowMo` in config
- **Skip intervention**: Comment out Act 4 section
- **Different theme**: Add a theme switch step in Act 1 (visit Settings, click theme)
