"""Subreddit mission parsing and rendering.

Inspired by Karpathy's autoresearch ``program.md`` — humans write a markdown
directive at the subreddit level, and we:

1. Parse H2 ``## Objective: ...`` headings into structured
   :class:`colloquip.models.MissionObjective` records (with optional
   ``- metric:`` / ``- target:`` bullets).
2. Render the full directive + objective list as a ``## Subreddit Mission``
   section that's prepended to agent system prompts.

Objectives without metric/target bullets are tracked qualitatively — progress
is reported as a human-review-only item from the dashboard.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

from colloquip.models import MissionObjective, ObjectiveProgress, Post

logger = logging.getLogger(__name__)

# ``## Objective: <title>`` — the title is captured and slugified into an id.
_OBJECTIVE_HEADING_RE = re.compile(
    r"^##\s*Objective\s*:\s*(?P<title>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_METRIC_RE = re.compile(
    r"^\s*[-*]\s*metric\s*:\s*(?P<metric>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TARGET_RE = re.compile(
    r"^\s*[-*]\s*target\s*:\s*(?P<target>[-+0-9.eE]+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)

_MISSION_MAX_CHARS_DEFAULT = 3000
_OBJECTIVE_BODY_MAX_CHARS = 600


def _slugify(title: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        slug = f"obj-{index}"
    return f"obj-{index + 1}-{slug[:40]}".rstrip("-")


def _extract_section_body(md: str, start: int, end: int) -> str:
    """Return the markdown body between two heading offsets."""
    body = md[start:end].strip()
    # Drop the metric/target bullets from the body description — they are
    # surfaced via structured fields, not prose.
    lines: List[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if _METRIC_RE.match(line) or _TARGET_RE.match(line):
            continue
        lines.append(stripped)
    return "\n".join(line for line in lines if line).strip()[:_OBJECTIVE_BODY_MAX_CHARS]


def parse_objectives(md: Optional[str]) -> List[MissionObjective]:
    """Parse a mission markdown directive into a list of MissionObjective.

    Only ``## Objective: <title>`` headings are extracted. Other headings are
    ignored so the human can write free-form context alongside objectives.
    """
    if not md:
        return []

    matches = list(_OBJECTIVE_HEADING_RE.finditer(md))
    if not matches:
        return []

    objectives: List[MissionObjective] = []
    for i, match in enumerate(matches):
        title = match.group("title").strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        # Truncate body_end at the next heading of any level that isn't ours.
        body_slice = md[body_start:body_end]
        next_heading = _HEADING_RE.search(body_slice)
        if next_heading:
            body_end = body_start + next_heading.start()
            body_slice = md[body_start:body_end]

        metric_match = _METRIC_RE.search(body_slice)
        target_match = _TARGET_RE.search(body_slice)
        metric = metric_match.group("metric").strip() if metric_match else None
        target: Optional[float] = None
        if target_match:
            try:
                target = float(target_match.group("target"))
            except ValueError:
                logger.warning("Failed to parse target value: %r", target_match.group("target"))

        description = _extract_section_body(md, body_start, body_end)
        objectives.append(
            MissionObjective(
                id=_slugify(title, i),
                title=title,
                description=description,
                metric=metric,
                target=target,
            )
        )
    return objectives


def render_mission_for_prompt(
    mission_md: Optional[str],
    objectives: List[MissionObjective],
    max_chars: int = _MISSION_MAX_CHARS_DEFAULT,
) -> str:
    """Render the mission directive + objectives as a system prompt section.

    Returns an empty string when there's no mission so the caller can simply
    concatenate without a conditional.
    """
    if not mission_md and not objectives:
        return ""

    parts: List[str] = ["## Subreddit Mission"]
    body = (mission_md or "").strip()
    # Soft-cap the raw directive so an overly long mission can't dominate
    # the context window.
    if len(body) > max_chars:
        body = body[:max_chars].rstrip() + "\n\n[...truncated...]"
    if body:
        parts.append(body)

    if objectives:
        parts.append("### Objectives")
        for obj in objectives:
            line = f"- **{obj.title}**"
            if obj.metric:
                line += f" — metric: `{obj.metric}`"
                if obj.target is not None:
                    line += f", target: {obj.target}"
            else:
                line += " — qualitative"
            if obj.description:
                line += f"\n  {obj.description.splitlines()[0][:200]}"
            parts.append(line)

    parts.append(
        "Keep the mission in mind as you deliberate. Your posts should visibly "
        "advance one or more objectives where possible."
    )
    return "\n\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Goal progress measurement
# ---------------------------------------------------------------------------

_SUPPORTED_METRICS = {
    "novelty_avg",
    "citation_density",
    "question_rate",
    "disagreement_rate",
    "post_count",
}


def _measure_single(
    objective: MissionObjective,
    posts: Iterable[Post],
) -> ObjectiveProgress:
    posts_list = list(posts)
    progress = ObjectiveProgress(
        objective_id=objective.id,
        title=objective.title,
        metric=objective.metric,
        target=objective.target,
        sample_size=len(posts_list),
    )

    # Qualitative when no metric or unknown metric name
    if not objective.metric or objective.metric not in _SUPPORTED_METRICS:
        progress.qualitative = True
        progress.status = "open"
        progress.detail = "Qualitative — human review only"
        return progress

    if not posts_list:
        progress.measured_value = 0.0
        progress.status = "not_met"
        progress.detail = "No posts yet"
        return progress

    value: float = 0.0
    if objective.metric == "novelty_avg":
        value = sum(p.novelty_score for p in posts_list) / len(posts_list)
    elif objective.metric == "citation_density":
        total_citations = sum(len(p.citations) for p in posts_list)
        value = total_citations / max(len(posts_list), 1)
    elif objective.metric == "question_rate":
        total_qs = sum(len(p.questions_raised) for p in posts_list)
        value = total_qs / max(len(posts_list), 1)
    elif objective.metric == "disagreement_rate":
        from colloquip.models import AgentStance

        disagree = sum(1 for p in posts_list if p.stance == AgentStance.CRITICAL)
        value = disagree / max(len(posts_list), 1)
    elif objective.metric == "post_count":
        value = float(len(posts_list))

    progress.measured_value = value
    if objective.target is not None and value >= objective.target:
        progress.status = "met"
    elif objective.target is not None:
        progress.status = "not_met"
    else:
        progress.status = "open"
    return progress


def measure_objectives(
    objectives: List[MissionObjective],
    posts: Iterable[Post],
) -> List[ObjectiveProgress]:
    """Score each mission objective against a collection of posts.

    Posts are typically the flattened recent posts of a subreddit (across
    threads). Qualitative objectives are passed through unchanged so the UI
    can still surface them as human-review items.
    """
    posts_list = list(posts)
    return [_measure_single(obj, posts_list) for obj in objectives]
