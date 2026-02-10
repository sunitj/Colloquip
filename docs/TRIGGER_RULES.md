# Trigger Rules Specification

Each agent independently evaluates trigger rules to decide whether to respond. This enables emergent conversation patterns — agents speak when they have something to contribute, not when scheduled.

---

## Design Philosophy

### Local Rules, Global Emergence

Like cellular automata, each agent:
- Only sees local context (recent posts, own knowledge base)
- Applies simple rules to decide action
- Has no knowledge of global conversation strategy

Complex patterns (serendipity, phase transitions, consensus) emerge from the intersection of independent local decisions.

### No Rule Says "Create Serendipity"

The trigger rules never explicitly target novel connections. Instead:
- Rule 5 (Bridge Opportunity) fires when an agent genuinely sees a connection
- The connection is serendipitous because it emerges from the agent's unique perspective
- Forcing serendipity would make it artificial

---

## Core Trigger Rules

### Rule 1: RELEVANCE

```
IF post.contains(my_domain_keywords) AND post.age < threshold
THEN consider_responding()
```

**Purpose**: Agents respond when their domain is being discussed.

**Implementation**:
```python
def check_relevance(
    posts: List[Post],
    domain_keywords: List[str],
    window: int = 5,
    min_keyword_matches: int = 2
) -> Tuple[bool, str]:
    """
    Check if recent posts mention this agent's domain.

    Args:
        posts: Full post history
        domain_keywords: Keywords for this agent's domain
        window: Number of recent posts to check
        min_keyword_matches: Minimum matches to trigger

    Returns:
        (should_trigger, reason)
    """
    recent = posts[-window:]
    if not recent:
        return False, ""

    # Combine recent post content
    combined_text = " ".join(p.content.lower() for p in recent)

    # Count keyword matches
    matches = sum(1 for kw in domain_keywords if kw.lower() in combined_text)

    if matches >= min_keyword_matches:
        return True, f"domain_relevance: {matches} keyword matches"

    return False, ""
```

**Configuration**:
```yaml
relevance:
  window: 5
  min_keyword_matches: 2
```

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Lower threshold (1 match) — be more responsive |
| DEBATE | Standard threshold (2 matches) |
| DEEPEN | Higher threshold (3 matches) — only respond if strongly relevant |
| CONVERGE | Higher threshold (3 matches) — only essential responses |

---

### Rule 2: DISAGREEMENT

```
IF post.contradicts(my_knowledge_base)
THEN respond_with_counterevidence()
```

**Purpose**: Agents challenge claims that conflict with their domain knowledge.

**Implementation**:
```python
def check_disagreement(
    posts: List[Post],
    agent_id: str,
    domain_keywords: List[str],
    window: int = 5
) -> Tuple[bool, str]:
    """
    Check if recent posts make claims that warrant challenge.

    Args:
        posts: Full post history
        agent_id: This agent's ID (to exclude own posts)
        domain_keywords: Keywords for this agent's domain
        window: Number of recent posts to check

    Returns:
        (should_trigger, reason)
    """
    recent = posts[-window:]

    for post in recent:
        # Skip own posts
        if post.agent_id == agent_id:
            continue

        # Check if post is in my domain
        is_my_domain = any(
            kw.lower() in post.content.lower()
            for kw in domain_keywords
        )

        if not is_my_domain:
            continue

        # Check if post makes strong claims (assertion indicators)
        assertion_indicators = [
            "clearly", "definitely", "certainly", "must be",
            "is proven", "demonstrates that", "shows that",
            "without doubt", "obviously"
        ]

        has_strong_claim = any(
            indicator in post.content.lower()
            for indicator in assertion_indicators
        )

        if has_strong_claim:
            return True, f"disagreement: strong claim in my domain by {post.agent_id}"

    return False, ""
```

**Note**: This rule triggers on *potential* disagreement (strong claims in my domain). The agent then evaluates whether to actually disagree during response generation.

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Lower threshold — challenge early to diversify |
| DEBATE | Standard threshold — challenge when warranted |
| DEEPEN | Higher threshold — only challenge if critical to thread |
| CONVERGE | Minimal — only challenge factual errors |

---

### Rule 3: QUESTION

```
IF post.contains_question() AND question.in_my_domain()
THEN attempt_answer()
```

**Purpose**: Agents answer questions in their domain.

**Implementation**:
```python
def check_question(
    posts: List[Post],
    agent_id: str,
    domain_keywords: List[str],
    window: int = 5
) -> Tuple[bool, str]:
    """
    Check for unanswered questions in this agent's domain.

    Args:
        posts: Full post history
        agent_id: This agent's ID
        domain_keywords: Keywords for this agent's domain
        window: Number of recent posts to check

    Returns:
        (should_trigger, reason)
    """
    recent = posts[-window:]

    for post in recent:
        # Skip own posts
        if post.agent_id == agent_id:
            continue

        # Check for questions
        if "?" not in post.content:
            continue

        # Extract question context (sentence containing ?)
        sentences = post.content.split(".")
        question_sentences = [s for s in sentences if "?" in s]

        for question in question_sentences:
            # Check if question is in my domain
            is_my_domain = any(
                kw.lower() in question.lower()
                for kw in domain_keywords
            )

            if is_my_domain:
                # Check if question was already answered
                answered = _check_if_answered(posts, question, agent_id)
                if not answered:
                    return True, f"question: unanswered question in my domain"

    return False, ""


def _check_if_answered(
    posts: List[Post],
    question: str,
    agent_id: str
) -> bool:
    """Check if this agent already answered a similar question."""
    question_keywords = set(question.lower().split())

    for post in posts:
        if post.agent_id != agent_id:
            continue
        post_keywords = set(post.content.lower().split())
        overlap = len(question_keywords & post_keywords)
        if overlap > 3:  # Heuristic: shared keywords suggest answer
            return True

    return False
```

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Eager to answer — lower relevance threshold |
| DEBATE | Standard — answer if clearly in domain |
| DEEPEN | Selective — only answer if central to thread |
| CONVERGE | Minimal — only answer if critical for synthesis |

---

### Rule 4: SILENCE_BREAKING

```
IF conversation.length > N AND my_last_post.age > M
AND conversation.still_relevant_to_me()
THEN inject_perspective()
```

**Purpose**: Ensure all agents contribute; prevent domination by subset.

**Implementation**:
```python
def check_silence_breaking(
    posts: List[Post],
    agent_id: str,
    domain_keywords: List[str],
    min_conversation_length: int = 8,
    max_silence: int = 6
) -> Tuple[bool, str]:
    """
    Check if this agent has been silent too long while discussion
    remains relevant.

    Args:
        posts: Full post history
        agent_id: This agent's ID
        domain_keywords: Keywords for this agent's domain
        min_conversation_length: Minimum posts before silence matters
        max_silence: Maximum posts without responding

    Returns:
        (should_trigger, reason)
    """
    if len(posts) < min_conversation_length:
        return False, ""

    # Find last post by this agent
    last_post_index = -1
    for i, post in enumerate(posts):
        if post.agent_id == agent_id:
            last_post_index = i

    if last_post_index == -1:
        # Never posted — definitely should contribute
        return True, "silence_breaking: never contributed"

    posts_since_last = len(posts) - last_post_index - 1

    if posts_since_last < max_silence:
        return False, ""

    # Check if recent discussion is still relevant
    recent = posts[-max_silence:]
    combined_text = " ".join(p.content.lower() for p in recent)
    is_relevant = any(kw.lower() in combined_text for kw in domain_keywords)

    if is_relevant:
        return True, f"silence_breaking: {posts_since_last} posts since last contribution"

    return False, ""
```

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Lower max_silence (4) — encourage broad participation |
| DEBATE | Standard max_silence (6) |
| DEEPEN | Higher max_silence (8) — focused agents dominate |
| CONVERGE | Standard (6) — ensure all voices in synthesis |

---

### Rule 5: BRIDGE_OPPORTUNITY

```
IF post_A.from(other_agent) AND post_B.from(another_agent)
AND I_see_connection(post_A, post_B)
THEN articulate_bridge()
```

**Purpose**: Enable serendipitous cross-domain connections.

**Implementation**:
```python
def check_bridge_opportunity(
    posts: List[Post],
    agent_id: str,
    domain_keywords: List[str],
    knowledge_scope: List[str],
    window: int = 10
) -> Tuple[bool, str]:
    """
    Check if this agent can bridge concepts from different agents.

    This is where serendipity EMERGES — not through detection,
    but through an agent genuinely seeing a connection.

    Args:
        posts: Full post history
        agent_id: This agent's ID
        domain_keywords: Keywords for this agent's domain
        knowledge_scope: Domains this agent can access
        window: Number of recent posts to check

    Returns:
        (should_trigger, reason)
    """
    recent = posts[-window:]

    # Collect posts from different agents
    posts_by_agent = {}
    for post in recent:
        if post.agent_id != agent_id:
            if post.agent_id not in posts_by_agent:
                posts_by_agent[post.agent_id] = []
            posts_by_agent[post.agent_id].append(post)

    # Need at least 2 other agents' posts
    if len(posts_by_agent) < 2:
        return False, ""

    # Look for bridgeable concepts
    for agent_a, posts_a in posts_by_agent.items():
        for agent_b, posts_b in posts_by_agent.items():
            if agent_a >= agent_b:  # Avoid duplicates
                continue

            # Check if both touch my domain from different angles
            bridge = _find_bridge(
                posts_a, posts_b,
                domain_keywords, knowledge_scope
            )

            if bridge:
                return True, f"bridge_opportunity: connecting {agent_a} and {agent_b} via {bridge}"

    return False, ""


def _find_bridge(
    posts_a: List[Post],
    posts_b: List[Post],
    domain_keywords: List[str],
    knowledge_scope: List[str]
) -> Optional[str]:
    """
    Find a bridging concept between two sets of posts.

    A bridge exists when:
    1. Both post sets touch this agent's domain
    2. They approach from different angles
    3. This agent can connect them through their knowledge
    """
    text_a = " ".join(p.content.lower() for p in posts_a)
    text_b = " ".join(p.content.lower() for p in posts_b)

    # Check if both touch my domain
    a_touches_domain = any(kw.lower() in text_a for kw in domain_keywords)
    b_touches_domain = any(kw.lower() in text_b for kw in domain_keywords)

    if not (a_touches_domain or b_touches_domain):
        return None

    # Look for complementary concepts
    bridge_patterns = [
        ("mechanism", "application"),
        ("target", "compound"),
        ("efficacy", "safety"),
        ("preclinical", "clinical"),
        ("pathway", "drug"),
    ]

    for concept_a, concept_b in bridge_patterns:
        if concept_a in text_a and concept_b in text_b:
            return f"{concept_a}-{concept_b}"
        if concept_b in text_a and concept_a in text_b:
            return f"{concept_b}-{concept_a}"

    return None
```

**Key Design Point**: This rule doesn't *detect* serendipity — it creates conditions where an agent might see a connection. The serendipity is *authentic* because it emerges from the agent's unique knowledge scope.

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Lower threshold — encourage early connections |
| DEBATE | Standard — bridges should be evidence-based |
| DEEPEN | Higher threshold — only strong connections |
| CONVERGE | Standard — bridges valuable for synthesis |

---

### Rule 6: UNCERTAINTY_RESPONSE

```
IF post.expresses_uncertainty() AND I_have_relevant_evidence()
THEN offer_evidence()
```

**Purpose**: Agents provide evidence when others express uncertainty.

**Implementation**:
```python
def check_uncertainty_response(
    posts: List[Post],
    agent_id: str,
    domain_keywords: List[str],
    window: int = 5
) -> Tuple[bool, str]:
    """
    Check if recent posts express uncertainty this agent can address.

    Args:
        posts: Full post history
        agent_id: This agent's ID
        domain_keywords: Keywords for this agent's domain
        window: Number of recent posts to check

    Returns:
        (should_trigger, reason)
    """
    recent = posts[-window:]

    uncertainty_indicators = [
        "unclear", "uncertain", "unknown", "not sure",
        "might be", "could be", "possibly", "perhaps",
        "needs more evidence", "insufficient data",
        "open question", "remains to be seen",
        "we don't know", "further research needed"
    ]

    for post in recent:
        if post.agent_id == agent_id:
            continue

        # Check for uncertainty
        has_uncertainty = any(
            indicator in post.content.lower()
            for indicator in uncertainty_indicators
        )

        if not has_uncertainty:
            continue

        # Check if uncertainty is in my domain
        is_my_domain = any(
            kw.lower() in post.content.lower()
            for kw in domain_keywords
        )

        if is_my_domain:
            return True, f"uncertainty_response: can address uncertainty from {post.agent_id}"

    return False, ""
```

**Phase Modulation**:
| Phase | Effect |
|-------|--------|
| EXPLORE | Standard — provide evidence to guide exploration |
| DEBATE | Higher threshold — only high-confidence evidence |
| DEEPEN | Standard — resolve key uncertainties |
| CONVERGE | Lower threshold — clear up final uncertainties |

---

## Red Team: Inverted Rules

The Red Team agent has inverted versions of several rules to maintain contrarian pressure:

### Inverted Rule 1: CONSENSUS_TRIGGER

```python
def check_consensus_forming(
    posts: List[Post],
    window: int = 5,
    supportive_threshold: int = 3
) -> Tuple[bool, str]:
    """
    INVERTED: Trigger when consensus is forming.
    Red Team should push back against premature agreement.
    """
    recent = posts[-window:]

    supportive_count = sum(
        1 for p in recent
        if p.stance == AgentStance.SUPPORTIVE
    )

    if supportive_count >= supportive_threshold:
        return True, "consensus_forming: challenging agreement"

    return False, ""
```

### Inverted Rule 2: CRITICISM_GAP

```python
def check_criticism_gap(
    posts: List[Post],
    window: int = 5,
    max_gap: int = 3
) -> Tuple[bool, str]:
    """
    INVERTED: Trigger when no recent criticism.
    Red Team should prevent echo chambers.
    """
    recent = posts[-window:]

    critical_count = sum(
        1 for p in recent
        if p.stance == AgentStance.CRITICAL
    )

    if critical_count == 0 and len(recent) >= max_gap:
        return True, "criticism_gap: injecting challenge"

    return False, ""
```

### Inverted Rule 3: PREMATURE_CONVERGENCE

```python
def check_premature_convergence(
    posts: List[Post],
    phase: Phase,
    min_debate_posts: int = 15
) -> Tuple[bool, str]:
    """
    INVERTED: Trigger during CONVERGE if debate was insufficient.
    Red Team pushes back against shallow consensus.
    """
    if phase != Phase.CONVERGE:
        return False, ""

    if len(posts) < min_debate_posts:
        return True, "premature_convergence: debate was too short"

    # Check if key disagreements were resolved
    critical_posts = [p for p in posts if p.stance == AgentStance.CRITICAL]
    if len(critical_posts) < 3:
        return True, "premature_convergence: insufficient challenge"

    return False, ""
```

---

## Trigger Evaluation Pipeline

### Full Evaluation

```python
class TriggerEvaluator:
    def __init__(
        self,
        agent_id: str,
        domain_keywords: List[str],
        knowledge_scope: List[str],
        is_red_team: bool = False
    ):
        self.agent_id = agent_id
        self.domain_keywords = domain_keywords
        self.knowledge_scope = knowledge_scope
        self.is_red_team = is_red_team
        self.last_post_index = -1

    def evaluate(
        self,
        posts: List[Post],
        phase: Phase
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate all trigger rules.

        Returns:
            (should_respond, list of triggered rules)
        """
        triggered = []

        # Special case: seed phase
        if not posts:
            return True, ["seed_phase"]

        # Apply phase modulation
        config = self._get_phase_config(phase)

        # Check each rule
        if self._check_relevance(posts, config):
            triggered.append("relevance")

        if self._check_disagreement(posts, config):
            triggered.append("disagreement")

        if self._check_question(posts, config):
            triggered.append("question")

        if self._check_silence_breaking(posts, config):
            triggered.append("silence_breaking")

        if self._check_bridge_opportunity(posts, config):
            triggered.append("bridge_opportunity")

        if self._check_uncertainty_response(posts, config):
            triggered.append("uncertainty_response")

        # Red Team inverted rules
        if self.is_red_team:
            if self._check_consensus_forming(posts, config):
                triggered.append("consensus_forming")
            if self._check_criticism_gap(posts, config):
                triggered.append("criticism_gap")
            if self._check_premature_convergence(posts, phase, config):
                triggered.append("premature_convergence")

        should_respond = len(triggered) > 0
        return should_respond, triggered

    def _get_phase_config(self, phase: Phase) -> dict:
        """Get phase-modulated configuration."""
        base = {
            "relevance_threshold": 2,
            "silence_max": 6,
            "window": 5,
        }

        modulation = {
            Phase.EXPLORE: {"relevance_threshold": 1, "silence_max": 4},
            Phase.DEBATE: {},
            Phase.DEEPEN: {"relevance_threshold": 3, "silence_max": 8},
            Phase.CONVERGE: {"relevance_threshold": 3},
        }

        return {**base, **modulation.get(phase, {})}
```

### Refractory Period

Prevent agents from dominating:

```python
def apply_refractory_period(
    posts: List[Post],
    agent_id: str,
    min_gap: int = 2
) -> bool:
    """
    Check if agent should skip due to refractory period.
    Returns True if agent should NOT respond.
    """
    if len(posts) < min_gap:
        return False

    # Check recent posts
    recent = posts[-min_gap:]
    agent_posts = sum(1 for p in recent if p.agent_id == agent_id)

    # Block if agent posted in recent window
    return agent_posts > 0
```

---

## Configuration Reference

```yaml
trigger_rules:
  # Common settings
  window: 5
  refractory_period: 2

  # Rule-specific thresholds
  relevance:
    min_keyword_matches: 2
    phase_modulation:
      explore: 1
      debate: 2
      deepen: 3
      converge: 3

  disagreement:
    enabled: true

  question:
    enabled: true
    check_answered: true

  silence_breaking:
    min_conversation_length: 8
    max_silence: 6
    phase_modulation:
      explore: 4
      debate: 6
      deepen: 8
      converge: 6

  bridge_opportunity:
    enabled: true
    min_agents: 2

  uncertainty_response:
    enabled: true

  # Red Team specific
  red_team:
    consensus_threshold: 3
    criticism_gap: 3
    min_debate_posts: 15
```

---

## Debugging Triggers

### Logging

```python
import logging

logger = logging.getLogger("triggers")

def evaluate_with_logging(
    agent_id: str,
    posts: List[Post],
    phase: Phase
) -> Tuple[bool, List[str]]:
    should_respond, triggered = evaluator.evaluate(posts, phase)

    logger.debug(
        f"Agent {agent_id} | Phase {phase.value} | "
        f"Triggered: {triggered} | Respond: {should_respond}"
    )

    return should_respond, triggered
```

### Metrics

Track trigger patterns:

```python
trigger_metrics = {
    "relevance": 0,
    "disagreement": 0,
    "question": 0,
    "silence_breaking": 0,
    "bridge_opportunity": 0,
    "uncertainty_response": 0,
    "consensus_forming": 0,  # Red Team
    "criticism_gap": 0,       # Red Team
}

# Update after each evaluation
for trigger in triggered:
    trigger_metrics[trigger] += 1
```

**What to watch:**
- `bridge_opportunity` firing rate → serendipity emergence
- `silence_breaking` dominance → possible staleness
- `consensus_forming` vs `criticism_gap` → Red Team balance

---

*Document created: 2026-02-10*
*Emergent Deliberation System v1.0*
