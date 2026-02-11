# Polish & Completion Plan

Five workstreams covering the remaining items. All can be implemented without an API key.

---

## 1. Dashboard Session Picker

**Goal**: Users can browse past deliberations and replay them in the dashboard.

### Backend: Already done
- `GET /api/deliberations` returns `{sessions: [{id, hypothesis, status, phase, created_at}]}` — no changes needed.
- `GET /api/deliberations/{id}/history` returns full session data (posts, energy_history, consensus) — no changes needed.

### Frontend Changes

**1a. New `SessionList` component** (`web/src/components/SessionList.tsx`)
- Fetches `GET /api/deliberations` on mount.
- Renders a compact list of past sessions: truncated hypothesis (50 chars), status badge (completed/running/pending), phase pill, relative timestamp.
- Each row is clickable. Clicking emits `onSelect(sessionId)`.
- A "New Deliberation" button at top returns to the start form.
- Shows an empty state ("No past sessions") if the list is empty.
- Styled consistently with existing dark theme (`.session-list`, `.session-item`, etc.).

**1b. Add `loadSession` to `useDeliberation` hook** (`web/src/hooks/useDeliberation.ts`)
- New function: `loadSession(sessionId: string)`.
- Fetches `GET /api/deliberations/{sessionId}/history`.
- Populates state (posts, energyHistory, consensus, phase, status, hypothesis) from the response — same shape as live events but in bulk.
- Does NOT connect a WebSocket (historical replay is read-only).
- Adds `phaseHistory` reconstruction: walks the posts to detect phase changes (posts are ordered, each has `phase`).

**1c. Update `App.tsx` layout**
- Add a `view` state: `'home' | 'session'`.
- Left panel gets a tab/toggle at top: "Agents" vs "History".
- When "History" tab is active, left panel shows `SessionList` instead of `AgentRoster`.
- Clicking a session calls `loadSession()` and switches to `'session'` view.
- Add a small "Back" button in ControlBar when viewing a historical session.
- When status is 'completed' AND consensus is loaded, center panel already shows ConsensusView (existing behavior).

**1d. CSS additions** (`web/src/App.css`)
- `.session-list` container styles.
- `.session-item` with hover effect, left border color based on status (green=completed, blue=running, gray=pending).
- `.session-hypothesis` truncated with ellipsis.
- `.session-meta` row for status + time.
- `.tab-toggle` for the Agents/History toggle.

**Tests**:
- Add a test to `test_api.py`: `test_list_deliberations` — create 2 sessions, verify list returns both sorted by created_at.
- Add a test: `test_session_history_endpoint` — create + run a session, then fetch history and verify posts/energy/consensus present.

---

## 2. EnergyChart Hover Breakdown

**Goal**: Hovering over a point on the SVG sparkline shows a tooltip with energy component breakdown for that turn.

### Changes to `EnergyChart.tsx`

**2a. Add interactive hover circles**
- Render transparent circles (r=6, fill=transparent) at each data point on the sparkline. These serve as hit targets.
- On `mouseEnter` of a circle, set `hoveredIndex` state.
- On `mouseLeave`, clear `hoveredIndex`.

**2b. Add tooltip overlay**
- When `hoveredIndex !== null`, render a positioned tooltip `<div>` above the hovered point.
- Tooltip content:
  - **Turn N** header
  - **Energy: XX%** (color-coded)
  - Component breakdown: novelty, disagreement, questions, staleness — each with value and mini bar (reuse `.component-bar-*` styles).
- Position the tooltip using the SVG coordinate → DOM coordinate mapping (the SVG is `viewBox`-based, so use `getBoundingClientRect()` of the SVG element + proportional calculation).
- Flip tooltip to left side when near the right edge.

**2c. Highlight hovered point**
- The hovered circle gets a larger radius (r=5) and a glow effect.
- Draw a vertical guide line from the hovered point down to the x-axis.

**2d. CSS additions**
- `.energy-tooltip` — positioned absolute, dark bg (`#1e293b`), border, rounded corners, shadow, z-index.
- `.energy-tooltip-header` — turn label.
- `.energy-tooltip-value` — large energy percentage.
- `.energy-tooltip-components` — reuses component bar layout but compact.
- `.sparkline-guide` — vertical dashed line in SVG.

---

## 3. Integration Test: Full Stack Verification

**Goal**: Verify backend API + WebSocket + frontend data flow work end-to-end using a single test that exercises the full deliberation lifecycle.

### New test file: `tests/test_integration_e2e.py`

**3a. Full lifecycle via REST + WebSocket**
- Create session via `POST /api/deliberations`.
- Connect WebSocket to `/ws/deliberations/{id}`.
- Send `{"type": "start"}`.
- Collect all events until `done`.
- Assertions:
  - Received at least one `post` event with valid Post shape.
  - Received at least one `energy_update` event with components dict.
  - Received `session_complete` with ConsensusMap shape (summary, agreements, final_stances).
  - Event sequence numbers are monotonically increasing.
  - All post `agent_id` values are from the known set.

**3b. WebSocket reconnection replay**
- Connect, receive some events, disconnect.
- Reconnect, send `{"type": "replay", "since": last_seq}`.
- Verify replayed events have correct seq numbers and no duplicates.

**3c. Session list + history round-trip**
- After deliberation completes, call `GET /api/deliberations` — verify session appears.
- Call `GET /api/deliberations/{id}/history` — verify posts match what was received via WebSocket.

**3d. Intervention during deliberation**
- Start deliberation, wait for first post.
- Send intervention via WebSocket `{"type": "intervene", "intervention_type": "question", "content": "..."}`.
- Verify subsequent posts arrive (intervention doesn't crash the loop).

All tests use `MockLLM`, no API key required. Mark with `@pytest.mark.integration`.

---

## 4. Prompt Tuning Framework

**Goal**: Build the infrastructure to tune prompts systematically, even without a live API key.

### Changes

**4a. Prompt template registry** (`src/colloquip/agents/prompts.py`)
- Add a `PromptVersion` dataclass: `version: str`, `phase_mandates: dict`, `response_guidelines: str`, `notes: str`.
- Add a `PROMPT_VERSIONS` dict with at least two versions:
  - `v1` (current prompts, baseline)
  - `v2` (improved prompts with tighter structure — see below)
- Add `get_prompts(version: str = "v1") -> PromptVersion` function.
- Modify `build_system_prompt` to accept optional `prompt_version` parameter.

**4b. Improved v2 prompts**
Key improvements for v2:
- **Structured output enforcement**: Add explicit JSON-block instructions so real LLM output parses more reliably. Wrap the response format in a fenced code block template the LLM should fill in.
- **Phase mandates tightened**: EXPLORE should explicitly encourage cross-domain connections. DEBATE should cite specific post numbers. CONVERGE should be limited to 1 paragraph.
- **Agent personas enhanced**: Add domain-specific vocabulary expectations to each agent's persona (e.g., biology agent should reference pathways, targets, mechanisms; chemistry agent should reference SAR, binding affinity, selectivity).
- **Red Team sharpened**: Explicit instruction to identify logical fallacies, confirmation bias, and gaps in evidence chains.

**4c. Prompt evaluation harness** (`src/colloquip/eval/prompt_eval.py`)
- New module that runs a mock deliberation with a given prompt version and evaluates quality metrics:
  - `stance_diversity`: How many distinct stances across all posts.
  - `question_rate`: Average questions per post.
  - `claim_rate`: Average claims per post.
  - `phase_coverage`: How many phases were reached.
  - `energy_curve_shape`: Did energy decline naturally?
  - `red_team_engagement`: Did red team post?
- Returns a `PromptEvalResult` dataclass with these metrics.
- This works with MockLLM — the mock already returns structured output, so the metrics exercise the pipeline even without real LLM responses.

**4d. CLI command for prompt evaluation**
- Add `--eval-prompts` flag to `colloquip` CLI.
- Runs both v1 and v2 with MockLLM (seed=42), prints a comparison table of metrics.
- This gives us the framework to immediately evaluate real LLM output when an API key becomes available.

**4e. Config integration**
- Add `prompt_version` field to the YAML config (`config/defaults.yaml`).
- Thread it through `create_default_agents()` → `build_system_prompt()`.
- Default remains `v1` for backward compatibility.

---

## 5. Partial Implementation Completions (No API Key Required)

### 5a. Post entry animations (Phase 5, Step 5.3)
- Posts already have a `fadeIn` animation. Enhance:
  - Add visual distinction for seed phase posts: a subtle "SEED" badge or different left border style (dashed) for posts where `triggered_by` includes `seed_phase`.

### 5b. Agent roster dimming during refractory (Phase 5, Step 5.4)
- Already partially done (`.agent-card.refractory { opacity: 0.5 }`). Add:
  - Persona tooltip on hover: show the agent's domain description from `AGENT_META`. Add a `title` attribute or a CSS tooltip.

### 5c. Phase transition visual feedback (Phase 5, Step 5.6)
- Add CSS transition to the phase timeline: when a phase becomes `current`, pulse the dot briefly.
- Add a `@keyframes phaseActivate` animation on `.phase-item.current`.

### 5d. Filterable trigger log (Phase 5, Step 5.7)
- Add filter chips above the trigger log: one per agent (colored).
- Clicking a chip toggles visibility of that agent's triggers.
- "All" chip to reset.
- Small state in `TriggerLog` component.

### 5e. Keyboard shortcuts (Phase 5, Step 5.9)
- Global `useEffect` with `keydown` listener:
  - `Space` when status is pending → start deliberation.
  - `Escape` → focus intervention bar.
  - `1-5` → no-op for now (reserved for tab switching).
- No external dependency needed.

### 5f. Seed vs emergent post distinction (Phase 5, Step 5.3)
- In `ConversationStream`, check `post.triggered_by.includes('seed_phase')`.
- Render a small "SEED" tag in the post header for seed posts.
- Use dashed left border instead of solid for seed posts.

### 5g. Energy injection visual marker (Phase 5, Step 5.5)
- In `EnergyChart`, detect when `post.triggered_by` includes `human_intervention` (from the posts list — we'll need to pass it as a prop or use the energy_update turn number).
- Alternative: mark turns where energy increased significantly (>0.1 jump from previous). Draw a small upward arrow marker on the sparkline at those points.

---

## Execution Order

1. **Session Picker** (1a-1d) — highest demo impact, exercises persistence layer
2. **EnergyChart Hover** (2a-2d) — directly addresses Phase 5 gate criterion
3. **Partial Completions** (5a-5g) — batch of small CSS/component changes
4. **Integration Tests** (3a-3d) — validates everything works together
5. **Prompt Tuning Framework** (4a-4e) — prepares for real LLM usage

Each workstream is independent and can be committed separately.
