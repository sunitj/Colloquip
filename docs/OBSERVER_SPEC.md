# Observer Agent Specification

The Observer is a meta-cognitive agent that watches conversation dynamics and broadcasts phase signals. It does not participate in scientific discussion — it only recognizes emergent patterns and names them.

---

## Design Philosophy

### What the Observer IS

- A pattern recognizer that reads conversation metrics
- A phase signal broadcaster that modulates agent behavior
- A simple rule-based system (not an LLM)
- Stateless between invocations (except hysteresis counter)

### What the Observer IS NOT

- A scientific participant (no content contribution)
- A phase dictator (it recognizes, doesn't decide)
- A complex ML model (simple heuristics suffice)
- A bottleneck (runs fast, in parallel with agents)

---

## Input: Conversation Metrics

The Observer computes these metrics from the post stream:

### 1. Question Rate

```python
def question_rate(posts: List[Post], window: int = 10) -> float:
    """
    Fraction of recent posts containing questions.
    High question rate → EXPLORE phase
    """
    recent = posts[-window:]
    if not recent:
        return 0.0
    questions = sum(1 for p in recent if "?" in p.content)
    return questions / len(recent)
```

**Interpretation:**
- `> 0.3`: Agents are in inquiry mode → EXPLORE
- `0.1 - 0.3`: Normal discourse
- `< 0.1`: Agents are asserting, not asking → DEBATE or CONVERGE

### 2. Disagreement Rate

```python
def disagreement_rate(posts: List[Post], window: int = 10) -> float:
    """
    Fraction of recent posts with CRITICAL stance.
    High disagreement → DEBATE phase
    """
    recent = posts[-window:]
    if not recent:
        return 0.0
    critical = sum(1 for p in recent if p.stance == AgentStance.CRITICAL)
    return critical / len(recent)
```

**Interpretation:**
- `> 0.4`: Active contention → DEBATE
- `0.2 - 0.4`: Healthy challenge
- `< 0.2`: Consensus forming or stagnating → CONVERGE

### 3. Topic Diversity

```python
def topic_diversity(posts: List[Post], window: int = 10) -> float:
    """
    Fraction of agents participating in recent window.
    High diversity → EXPLORE; Low diversity → DEEPEN
    """
    recent = posts[-window:]
    if not recent:
        return 0.0
    unique_agents = len(set(p.agent_id for p in recent))
    return unique_agents / 6  # 6 scientist agents
```

**Interpretation:**
- `> 0.6`: Many voices → EXPLORE
- `0.3 - 0.6`: Normal participation
- `< 0.3`: Focused discussion → DEEPEN

### 4. Citation Density

```python
def citation_density(posts: List[Post], window: int = 10) -> float:
    """
    Average citations per post, normalized.
    High citations + disagreement → DEBATE
    """
    recent = posts[-window:]
    if not recent:
        return 0.0
    total_citations = sum(len(p.citations) for p in recent)
    # Normalize: assume 3 citations per post is "full"
    return min(total_citations / (len(recent) * 3), 1.0)
```

**Interpretation:**
- `> 0.5`: Evidence-heavy discourse → DEBATE
- `0.2 - 0.5`: Normal citation
- `< 0.2`: Speculative discussion → EXPLORE

### 5. Novelty Average

```python
def novelty_average(posts: List[Post], window: int = 10) -> float:
    """
    Average novelty score of recent posts.
    High novelty → DEEPEN on promising threads
    """
    recent = posts[-window:]
    if not recent:
        return 0.0
    return sum(p.novelty_score for p in recent) / len(recent)
```

**Interpretation:**
- `> 0.5`: Novel connections emerging → DEEPEN
- `0.3 - 0.5`: Normal novelty
- `< 0.3`: Routine discussion

### 6. Posts Since Last Novel

```python
def posts_since_novel(posts: List[Post], threshold: float = 0.7) -> int:
    """
    Number of posts since last high-novelty post.
    High count → conversation stagnating → CONVERGE
    """
    count = 0
    for post in reversed(posts):
        if post.novelty_score > threshold:
            break
        count += 1
    return count
```

**Interpretation:**
- `> 8`: Stagnating → CONVERGE
- `5 - 8`: Slowing down
- `< 5`: Active novelty generation

---

## Output: Phase Signal

### Phase Enum

```python
class Phase(str, Enum):
    EXPLORE = "explore"    # Divergent, questioning, speculative
    DEBATE = "debate"      # Adversarial, evidence-heavy, challenging
    DEEPEN = "deepen"      # Focused, high-signal, drilling down
    CONVERGE = "converge"  # Energy dropping, synthesizing
    SYNTHESIS = "synthesis"  # Final explicit phase (not detected, triggered)
```

### Phase Signal Structure

```python
class PhaseSignal(BaseModel):
    current_phase: Phase
    confidence: float  # 0.0 - 1.0
    metrics: ConversationMetrics
    observation: Optional[str]  # Rare meta-observation
```

---

## Detection Algorithm

### Primary Detection Rules

```python
def detect_phase(metrics: ConversationMetrics) -> Phase:
    """
    Simple rule-based phase detection.
    Order matters: more specific conditions first.
    """

    # EXPLORE: High questions + diverse participation
    if metrics.question_rate > 0.3 and metrics.topic_diversity > 0.6:
        return Phase.EXPLORE

    # DEBATE: High disagreement + evidence-heavy
    if metrics.disagreement_rate > 0.4 and metrics.citation_density > 0.5:
        return Phase.DEBATE

    # DEEPEN: Focused (low diversity) + high novelty
    if metrics.topic_diversity < 0.5 and metrics.novelty_avg > 0.5:
        return Phase.DEEPEN

    # CONVERGE: Low energy + stagnating
    if metrics.energy < 0.3 and metrics.posts_since_novel > 5:
        return Phase.CONVERGE

    # Default: no clear signal, maintain current phase
    return None  # Signals "no change"
```

### Hysteresis: Preventing Oscillation

Phase transitions require sustained signal:

```python
class ObserverAgent:
    def __init__(self, hysteresis_threshold: int = 3):
        self.current_phase = Phase.EXPLORE
        self.pending_phase: Optional[Phase] = None
        self.pending_count: int = 0
        self.hysteresis_threshold = hysteresis_threshold

    def update(self, detected: Optional[Phase]) -> Phase:
        """
        Update phase with hysteresis.
        Require `hysteresis_threshold` consecutive signals before changing.
        """
        if detected is None or detected == self.current_phase:
            # No change signal or same phase
            self.pending_phase = None
            self.pending_count = 0
            return self.current_phase

        if detected == self.pending_phase:
            # Continuing signal for pending phase
            self.pending_count += 1
            if self.pending_count >= self.hysteresis_threshold:
                # Transition!
                self.current_phase = detected
                self.pending_phase = None
                self.pending_count = 0
        else:
            # New phase signal, reset counter
            self.pending_phase = detected
            self.pending_count = 1

        return self.current_phase
```

**Why hysteresis?**

Without it, noisy metrics cause rapid oscillation:
```
Turn 1: EXPLORE (question asked)
Turn 2: DEBATE (disagreement)
Turn 3: EXPLORE (another question)
Turn 4: DEBATE (critical stance)
...
```

With hysteresis (threshold=3):
```
Turn 1: EXPLORE (detected DEBATE, count=1)
Turn 2: EXPLORE (detected DEBATE, count=2)
Turn 3: EXPLORE (detected DEBATE, count=3)
Turn 4: DEBATE ← transition after sustained signal
```

---

## Confidence Calculation

```python
def calculate_confidence(
    current_phase: Phase,
    detected_phase: Optional[Phase],
    pending_count: int,
    hysteresis_threshold: int
) -> float:
    """
    Confidence in current phase assessment.
    """
    if detected_phase is None or detected_phase == current_phase:
        # Strong signal for current phase
        return 0.9

    # Pending transition reduces confidence
    progress = pending_count / hysteresis_threshold
    return max(0.5, 0.9 - (progress * 0.3))
```

**Interpretation:**
- `> 0.8`: High confidence, agents can rely on phase signal
- `0.6 - 0.8`: Moderate confidence, phase may shift soon
- `< 0.6`: Low confidence, phase transition imminent

---

## Meta-Observations

The Observer can optionally emit meta-observations when patterns are notable:

```python
def generate_observation(metrics: ConversationMetrics) -> Optional[str]:
    """
    Generate rare meta-observation for the thread.
    These are broadcast to all agents as context.
    """

    if metrics.posts_since_novel > 8:
        return (
            "The conversation appears to be circling. "
            "Consider introducing new evidence or perspectives."
        )

    if metrics.disagreement_rate > 0.6:
        return (
            "Significant disagreement detected. "
            "The points of contention may warrant focused analysis."
        )

    if metrics.novelty_avg > 0.7:
        return (
            "High novelty in recent posts. "
            "Cross-domain connections may be emerging."
        )

    if metrics.topic_diversity < 0.3 and metrics.energy > 0.5:
        return (
            "Discussion is focused but energetic. "
            "Deep analysis of this thread may be valuable."
        )

    return None
```

**Guidelines:**
- Meta-observations should be rare (< 20% of turns)
- They describe dynamics, not content
- They suggest, not direct
- They are phrased as observations, not commands

---

## Integration with Deliberation Loop

```python
async def deliberation_loop(session: Session, posts: List[Post]):
    observer = ObserverAgent()

    while not should_terminate(posts):
        # 1. Observer detects phase
        metrics = calculate_metrics(posts)
        detected = detect_phase(metrics)
        current_phase = observer.update(detected)
        confidence = calculate_confidence(...)
        observation = generate_observation(metrics)

        phase_signal = PhaseSignal(
            current_phase=current_phase,
            confidence=confidence,
            metrics=metrics,
            observation=observation
        )

        # 2. Optional: emit observer post
        if observation:
            yield create_observer_post(observation)

        # 3. Agents evaluate triggers with phase context
        responding_agents = []
        for agent in agents:
            should, reason = agent.should_respond(posts, current_phase)
            if should:
                responding_agents.append(agent)

        # 4. Generate responses
        new_posts = await asyncio.gather(*[
            agent.generate_post(posts, current_phase)
            for agent in responding_agents
        ])

        posts.extend(new_posts)
        for post in new_posts:
            yield post
```

---

## Edge Cases

### No Clear Phase Signal

When metrics don't clearly indicate any phase:

```python
# All metrics in middle ranges
metrics = ConversationMetrics(
    question_rate=0.2,      # Not high enough for EXPLORE
    disagreement_rate=0.3,  # Not high enough for DEBATE
    topic_diversity=0.5,    # Neither high nor low
    novelty_avg=0.4,        # Moderate
    energy=0.4,             # Moderate
    posts_since_novel=3     # Recent novelty
)
```

**Behavior**: Maintain current phase. The conversation is in a "normal" state that doesn't trigger transitions.

### Rapid Phase Cycling

If metrics oscillate rapidly (every 1-2 turns), hysteresis prevents whiplash:

```
Turn 1: EXPLORE (DEBATE signal, count=1)
Turn 2: EXPLORE (EXPLORE signal, reset count)
Turn 3: EXPLORE (DEBATE signal, count=1)
Turn 4: EXPLORE (DEBATE signal, count=2)
Turn 5: EXPLORE (EXPLORE signal, reset count)
```

**Behavior**: Stay in current phase until sustained signal emerges.

### Early Termination Signals

If CONVERGE is detected very early (< 12 posts):

```python
def should_terminate(posts: List[Post], min_posts: int = 12) -> bool:
    if len(posts) < min_posts:
        return False  # Force minimum engagement
    # ... rest of termination logic
```

**Behavior**: Ignore early convergence. Ensure minimum deliberation depth.

### Observer Disagreement with Agent Behavior

If agents behave inconsistently with detected phase:

```
Phase: DEBATE
But agents are asking questions (EXPLORE behavior)
```

**Behavior**: This is fine! Agents have autonomy. The Observer names the *emergent* state, but agents follow their own trigger rules. If enough agents behave differently, the phase will naturally shift.

---

## Configuration

### Default Parameters

```yaml
observer:
  hysteresis_threshold: 3       # Rounds before phase change
  window_size: 10               # Posts to consider for metrics
  min_posts_before_converge: 12 # Minimum deliberation depth
  observation_frequency: 0.2    # Max fraction of turns with observations

thresholds:
  explore:
    question_rate_min: 0.3
    topic_diversity_min: 0.6
  debate:
    disagreement_rate_min: 0.4
    citation_density_min: 0.5
  deepen:
    topic_diversity_max: 0.5
    novelty_avg_min: 0.5
  converge:
    energy_max: 0.3
    posts_since_novel_min: 5
```

### Tuning Guidelines

**If phases transition too slowly:**
- Reduce `hysteresis_threshold` (e.g., 2 instead of 3)
- Lower thresholds for phase detection

**If phases oscillate too much:**
- Increase `hysteresis_threshold` (e.g., 4-5)
- Widen the "dead zone" between thresholds

**If conversations die too quickly:**
- Increase `min_posts_before_converge`
- Raise energy threshold for CONVERGE

**If observations are too frequent:**
- Reduce `observation_frequency`
- Raise thresholds for observation triggers

---

## Implementation Checklist

- [ ] Define `Phase` enum in `models.py`
- [ ] Implement `ConversationMetrics` calculation
- [ ] Implement `ObserverAgent` class with hysteresis
- [ ] Add phase detection rules
- [ ] Add meta-observation generation
- [ ] Integrate Observer into deliberation loop
- [ ] Add phase signal to agent context
- [ ] Test hysteresis behavior
- [ ] Test edge cases (early termination, rapid cycling)
- [ ] Tune thresholds empirically

---

*Document created: 2026-02-10*
*Emergent Deliberation System v1.0*
