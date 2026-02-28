# Energy Model & Termination Logic

> **Wiki**: See [Core Concepts](https://github.com/sunitj/Colloquip/wiki/Core-Concepts) for a concise overview of the energy model. See [Deliberation Engine](https://github.com/sunitj/Colloquip/wiki/Deliberation-Engine) for configuration parameters. This document contains the complete calculation implementations and calibration guidelines.

The Energy Model determines when a conversation naturally winds down. Instead of fixed round counts, we measure "conversation energy" — the vitality of ongoing discourse — and terminate when energy decays below threshold.

---

## Design Philosophy

### Why Energy-Based Termination?

Fixed-round termination has problems:
- **Too short**: Important threads cut off prematurely
- **Too long**: Circular arguments continue past value
- **One-size-fits-all**: Different hypotheses need different depths

Energy-based termination:
- **Adaptive**: Contentious topics run longer naturally
- **Natural**: Conversations end when agents have nothing new to say
- **Self-regulating**: High-signal threads sustain themselves

### Energy as a Metaphor

Think of conversation energy like thermodynamics:
- **Novel ideas** inject energy (heat)
- **Disagreements** create energy through friction
- **Questions** represent potential energy
- **Repetition** dissipates energy (entropy)
- **Convergence** is cooling toward equilibrium

Termination = thermal equilibrium = no more useful work can be extracted.

---

## Energy Calculation

### Core Formula

```python
def calculate_energy(posts: List[Post], window: int = 10) -> float:
    """
    Calculate conversation energy from recent posts.

    Energy = (novelty * 0.4) + (disagreement * 0.3) + (questions * 0.2)
             - (staleness * 0.1)

    Returns: 0.0 to 1.0
    """
    recent = posts[-window:]
    if not recent:
        return 1.0  # Full energy at start

    # Component 1: Novelty (new ideas, cross-domain connections)
    novelty = _calculate_novelty_component(recent)

    # Component 2: Disagreement (productive tension)
    disagreement = _calculate_disagreement_component(recent)

    # Component 3: Open Questions (unresolved inquiry)
    questions = _calculate_question_component(recent, posts)

    # Component 4: Staleness Penalty (repetition, circular arguments)
    staleness = _calculate_staleness_penalty(recent, posts)

    # Weighted combination
    energy = (
        0.4 * novelty +
        0.3 * disagreement +
        0.2 * questions -
        0.1 * staleness
    )

    return max(0.0, min(1.0, energy))
```

### Component 1: Novelty

```python
def _calculate_novelty_component(recent: List[Post]) -> float:
    """
    Novelty component from novelty scores.

    High novelty = new ideas emerging
    Low novelty = rehashing known ground
    """
    if not recent:
        return 0.0

    # Average novelty score
    avg_novelty = sum(p.novelty_score for p in recent) / len(recent)

    # Bonus for NOVEL_CONNECTION stance
    novel_connections = sum(
        1 for p in recent
        if p.stance == AgentStance.NOVEL_CONNECTION
    )
    connection_bonus = min(novel_connections * 0.1, 0.3)

    return min(avg_novelty + connection_bonus, 1.0)
```

**Interpretation:**
- `> 0.7`: High novelty — conversation is generative
- `0.4 - 0.7`: Moderate novelty — normal discourse
- `< 0.4`: Low novelty — may be stagnating

### Component 2: Disagreement

```python
def _calculate_disagreement_component(recent: List[Post]) -> float:
    """
    Disagreement component from stance distribution.

    Productive disagreement = energy
    Total agreement = may indicate premature consensus
    Total disagreement = may indicate unresolvable conflict
    """
    if not recent:
        return 0.0

    stances = [p.stance for p in recent]

    critical = sum(1 for s in stances if s == AgentStance.CRITICAL)
    supportive = sum(1 for s in stances if s == AgentStance.SUPPORTIVE)
    total = len(stances)

    # Optimal: some disagreement but not total
    # Peak energy at ~40% disagreement
    disagreement_rate = critical / total

    if disagreement_rate < 0.2:
        # Too little disagreement — may be echo chamber
        return 0.5 * disagreement_rate / 0.2
    elif disagreement_rate < 0.5:
        # Optimal range
        return 0.5 + 0.5 * (disagreement_rate - 0.2) / 0.3
    else:
        # Too much disagreement — may be unproductive conflict
        return 1.0 - 0.5 * (disagreement_rate - 0.5) / 0.5

    # Result: peaks at 0.4-0.5 disagreement rate
```

**Interpretation:**
- `> 0.8`: Optimal productive tension
- `0.5 - 0.8`: Healthy discourse
- `< 0.5`: Either echo chamber or unproductive conflict

### Component 3: Open Questions

```python
def _calculate_question_component(
    recent: List[Post],
    all_posts: List[Post]
) -> float:
    """
    Open questions component.

    Unanswered questions = potential energy
    Answered questions = work done (reduce count)
    """
    # Count questions in recent posts
    recent_questions = []
    for post in recent:
        # Extract question sentences
        sentences = post.content.split(".")
        for sentence in sentences:
            if "?" in sentence:
                recent_questions.append((post, sentence))

    if not recent_questions:
        return 0.0

    # Check which are answered in subsequent posts
    unanswered = 0
    for q_post, question in recent_questions:
        q_index = all_posts.index(q_post)
        subsequent = all_posts[q_index + 1:]

        # Heuristic: question answered if keywords appear in later posts
        q_keywords = set(question.lower().split())
        answered = False
        for post in subsequent:
            p_keywords = set(post.content.lower().split())
            if len(q_keywords & p_keywords) > 3:
                answered = True
                break

        if not answered:
            unanswered += 1

    # More unanswered questions = more potential energy
    return min(unanswered / 5, 1.0)  # Cap at 5 open questions
```

**Interpretation:**
- `> 0.6`: Many open questions — inquiry is active
- `0.3 - 0.6`: Some open threads
- `< 0.3`: Most questions resolved

### Component 4: Staleness Penalty

```python
def _calculate_staleness_penalty(
    recent: List[Post],
    all_posts: List[Post]
) -> float:
    """
    Staleness penalty for repetition and circular arguments.

    Repetition = entropy = energy dissipation
    """
    if len(recent) < 3:
        return 0.0

    penalties = []

    # Penalty 1: Posts since last high-novelty post
    posts_since_novel = 0
    for post in reversed(all_posts):
        if post.novelty_score > 0.7:
            break
        posts_since_novel += 1

    novelty_penalty = min(posts_since_novel / 10, 1.0)
    penalties.append(novelty_penalty)

    # Penalty 2: Semantic repetition (same concepts repeated)
    repetition_penalty = _detect_repetition(recent)
    penalties.append(repetition_penalty)

    # Penalty 3: Agent participation stagnation
    unique_agents = len(set(p.agent_id for p in recent))
    participation_penalty = 1.0 - (unique_agents / 6)
    penalties.append(participation_penalty)

    return sum(penalties) / len(penalties)


def _detect_repetition(posts: List[Post]) -> float:
    """
    Detect semantic repetition in posts.

    Uses simple keyword overlap as proxy for repetition.
    """
    if len(posts) < 3:
        return 0.0

    # Extract key phrases from each post
    post_keywords = []
    for post in posts:
        words = post.content.lower().split()
        # Simple: take top frequent words as "keywords"
        keywords = set(words)
        post_keywords.append(keywords)

    # Calculate pairwise overlap
    overlaps = []
    for i in range(len(post_keywords)):
        for j in range(i + 1, len(post_keywords)):
            intersection = len(post_keywords[i] & post_keywords[j])
            union = len(post_keywords[i] | post_keywords[j])
            if union > 0:
                overlaps.append(intersection / union)

    if not overlaps:
        return 0.0

    avg_overlap = sum(overlaps) / len(overlaps)

    # High overlap = high repetition = high penalty
    return min(avg_overlap * 2, 1.0)
```

**Interpretation:**
- `> 0.6`: Significant staleness — conversation circling
- `0.3 - 0.6`: Some repetition
- `< 0.3`: Minimal staleness — fresh content

---

## Termination Logic

### Primary Termination Condition

```python
def should_terminate(
    posts: List[Post],
    energy_history: List[float],
    config: TerminationConfig
) -> Tuple[bool, str]:
    """
    Determine if deliberation should end.

    Returns:
        (should_terminate, reason)
    """
    # Guard: minimum posts before allowing termination
    if len(posts) < config.min_posts:
        return False, ""

    # Condition 1: Energy below threshold for N consecutive turns
    if len(energy_history) >= config.low_energy_rounds:
        recent_energy = energy_history[-config.low_energy_rounds:]
        if all(e < config.energy_threshold for e in recent_energy):
            return True, f"low_energy: energy < {config.energy_threshold} for {config.low_energy_rounds} rounds"

    # Condition 2: Maximum turns reached (hard cap)
    if len(posts) >= config.max_posts:
        return True, f"max_posts: reached {config.max_posts}"

    # Condition 3: All agents have contributed and energy is dropping
    unique_agents = len(set(p.agent_id for p in posts))
    if unique_agents >= 6:
        if len(energy_history) >= 3:
            # Check for declining trend
            trend = energy_history[-1] - energy_history[-3]
            if trend < -0.2 and energy_history[-1] < 0.4:
                return True, "declining_energy: all agents contributed, energy declining"

    return False, ""
```

### Configuration

```python
@dataclass
class TerminationConfig:
    min_posts: int = 12           # Minimum deliberation depth
    max_posts: int = 50           # Hard cap
    energy_threshold: float = 0.2 # Low energy threshold
    low_energy_rounds: int = 3    # Consecutive low-energy rounds
```

### Termination State Machine

```
                    ┌─────────────┐
                    │   ACTIVE    │
                    │ energy > 0.3│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ COOLING  │ │ COOLING  │ │ COOLING  │
        │ round 1  │ │ round 2  │ │ round 3  │
        │ e < 0.3  │ │ e < 0.3  │ │ e < 0.3  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
    energy   │    energy  │    energy  │
    > 0.3    │    > 0.3   │    < 0.3   │
             │            │            │
             ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ ACTIVE   │ │ ACTIVE   │ │TERMINATE │
        │(reset)   │ │(reset)   │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

---

## Energy Injection

### External Energy Sources

Energy can be injected to prevent premature death:

```python
def inject_energy(
    source: EnergySource,
    current_energy: float
) -> float:
    """
    Inject energy from external sources.
    """
    injection = {
        EnergySource.NEW_KNOWLEDGE: 0.3,      # New paper added to KB
        EnergySource.HUMAN_INTERVENTION: 0.4,  # Human asks question
        EnergySource.NOVEL_POST: 0.2,          # High-novelty post
        EnergySource.RED_TEAM_CHALLENGE: 0.15, # Red Team triggers
    }

    boost = injection.get(source, 0.0)
    return min(current_energy + boost, 1.0)
```

### Human Intervention

Humans can:
- **Extend**: Add question/data that injects energy
- **Terminate**: Force synthesis regardless of energy
- **Redirect**: Shift focus, which can inject energy

```python
def handle_human_intervention(
    intervention: HumanIntervention,
    energy_history: List[float]
) -> float:
    """
    Process human intervention effects on energy.
    """
    if intervention.type == "question":
        return inject_energy(EnergySource.HUMAN_INTERVENTION, energy_history[-1])
    elif intervention.type == "data":
        return inject_energy(EnergySource.NEW_KNOWLEDGE, energy_history[-1])
    elif intervention.type == "terminate":
        return 0.0  # Force termination
    elif intervention.type == "extend":
        return max(energy_history[-1], 0.5)  # Boost to at least 0.5

    return energy_history[-1]
```

---

## Energy Visualization

### Energy Timeline

For the frontend, track and display energy over time:

```typescript
interface EnergyPoint {
  turn: number;
  energy: float;
  novelty: float;
  disagreement: float;
  questions: float;
  staleness: float;
}

// Display as line chart
<EnergyChart
  data={energyHistory}
  threshold={0.2}
  currentPhase={phase}
/>
```

### Energy Indicator

Simple visual indicator:

```typescript
const EnergyIndicator: React.FC<{ energy: float }> = ({ energy }) => {
  const level = energy > 0.6 ? 'high' : energy > 0.3 ? 'medium' : 'low';
  const color = { high: 'green', medium: 'yellow', low: 'red' }[level];

  return (
    <div className={`energy-indicator bg-${color}-500`}>
      <span>Energy: {(energy * 100).toFixed(0)}%</span>
      {level === 'low' && <span className="ml-2">⚠️ Converging</span>}
    </div>
  );
};
```

---

## Calibration

### Expected Energy Patterns

**Healthy Deliberation:**
```
Energy
1.0 │    ╭─────╮
    │   ╱      ╲
0.7 │  ╱        ╲
    │ ╱          ╲
0.4 │╱            ╲───────╮
    │              ╲      │
0.2 │               ╲─────┴─ terminate
    └────────────────────────────►
        Seed  Debate  Deepen  Converge
```

**Contentious Hypothesis:**
```
Energy
1.0 │    ╭───────────────╮
    │   ╱                 ╲
0.7 │  ╱                   ╲
    │ ╱                     ╲
0.4 │╱                       ╲───╮
    │                         ╲  │
0.2 │                          ╲─┴─ terminate
    └──────────────────────────────►
        Extended DEBATE phase
```

**Shallow Consensus:**
```
Energy
1.0 │  ╭─╮
    │ ╱   ╲
0.7 │╱     ╲
    │       ╲
0.4 │        ╲
    │         ╲
0.2 │          ╲───── terminate (may be premature)
    └───────────────►
        Red Team should push back
```

### Threshold Tuning

| Symptom | Adjustment |
|---------|------------|
| Conversations end too quickly | Lower `energy_threshold` (0.15) |
| Conversations drag on | Raise `energy_threshold` (0.25) |
| Missing important threads | Increase `min_posts` (15-20) |
| Repetitive late-stage | Increase staleness weight |
| Shallow consensus | Red Team rules more aggressive |

---

## Integration

### In Deliberation Loop

```python
class EmergentDeliberationEngine:
    def __init__(self, config: TerminationConfig):
        self.config = config
        self.energy_history: List[float] = []

    async def run_deliberation(
        self,
        session: Session,
        hypothesis: str
    ) -> AsyncIterator[Post]:
        posts: List[Post] = []

        # Seed phase
        async for post in self._run_seed_phase(session, hypothesis):
            posts.append(post)
            yield post

        # Emergent loop
        while True:
            # Calculate energy
            energy = calculate_energy(posts)
            self.energy_history.append(energy)

            # Check termination
            should_stop, reason = should_terminate(
                posts, self.energy_history, self.config
            )

            if should_stop:
                logger.info(f"Terminating: {reason}")
                break

            # Observer phase detection
            phase = self.observer.detect_phase(posts)

            # Agent responses...
            new_posts = await self._run_turn(posts, phase)
            posts.extend(new_posts)
            for post in new_posts:
                yield post

        # Synthesis
        synthesis = await self._run_synthesis(posts)
        yield synthesis
```

### Metrics Export

```python
def export_energy_metrics(
    energy_history: List[float],
    posts: List[Post]
) -> dict:
    """Export energy metrics for analysis."""
    return {
        "final_energy": energy_history[-1],
        "peak_energy": max(energy_history),
        "mean_energy": sum(energy_history) / len(energy_history),
        "energy_at_termination": energy_history[-1],
        "total_posts": len(posts),
        "unique_agents": len(set(p.agent_id for p in posts)),
        "termination_reason": determine_termination_reason(energy_history),
    }
```

---

## Configuration Reference

```yaml
energy:
  # Component weights
  weights:
    novelty: 0.4
    disagreement: 0.3
    questions: 0.2
    staleness: -0.1

  # Calculation parameters
  window: 10
  novelty_bonus_per_connection: 0.1
  max_novelty_bonus: 0.3
  optimal_disagreement_rate: 0.4
  max_open_questions: 5

  # Staleness detection
  staleness:
    posts_since_novel_threshold: 10
    repetition_weight: 2.0

termination:
  min_posts: 12
  max_posts: 50
  energy_threshold: 0.2
  low_energy_rounds: 3

energy_injection:
  new_knowledge: 0.3
  human_intervention: 0.4
  novel_post: 0.2
  red_team_challenge: 0.15
```

---

*Document created: 2026-02-10*
*Emergent Deliberation System v1.0*
