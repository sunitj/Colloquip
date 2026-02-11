"""Rich terminal output for deliberation events."""

from typing import Dict, Optional

from colloquip.models import (
    AgentStance,
    ConsensusMap,
    EnergyUpdate,
    Phase,
    PhaseSignal,
    Post,
)

# Agent color map for terminal output
AGENT_COLORS: Dict[str, str] = {
    "biology": "green",
    "chemistry": "blue",
    "admet": "yellow",
    "clinical": "cyan",
    "regulatory": "magenta",
    "redteam": "red",
    "human": "white",
}

STANCE_SYMBOLS: Dict[AgentStance, str] = {
    AgentStance.SUPPORTIVE: "+",
    AgentStance.CRITICAL: "-",
    AgentStance.NEUTRAL: "~",
    AgentStance.NOVEL_CONNECTION: "*",
}

PHASE_STYLES: Dict[Phase, str] = {
    Phase.EXPLORE: "bold green",
    Phase.DEBATE: "bold red",
    Phase.DEEPEN: "bold blue",
    Phase.CONVERGE: "bold yellow",
    Phase.SYNTHESIS: "bold magenta",
}


class RichDisplay:
    """Rich terminal display for deliberation events.

    Requires the `rich` optional dependency:
        pip install colloquip[cli]
    """

    def __init__(self, max_content_width: int = 200):
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
        except ImportError:
            raise ImportError(
                "The 'rich' package is required for rich display. "
                "Install it with: pip install colloquip[cli]"
            )

        self.console = Console()
        self.max_content_width = max_content_width
        self._post_count = 0
        self._current_phase = Phase.EXPLORE

    def show_header(self, hypothesis: str) -> None:
        from rich.panel import Panel
        from rich.text import Text

        title = Text("COLLOQUIP", style="bold white")
        subtitle = Text("Emergent Multi-Agent Deliberation", style="dim")
        content = Text()
        content.append(title)
        content.append("\n")
        content.append(subtitle)
        content.append("\n\n")
        content.append("Hypothesis: ", style="bold")
        content.append(hypothesis)

        self.console.print(Panel(content, border_style="bright_blue", padding=(1, 2)))

    def show_post(self, post: Post) -> None:
        from rich.panel import Panel
        from rich.text import Text

        self._post_count += 1
        agent_color = AGENT_COLORS.get(post.agent_id, "white")
        stance_symbol = STANCE_SYMBOLS.get(post.stance, "?")

        # Title line
        title = Text()
        title.append(f"[{self._post_count:02d}] ", style="dim")
        title.append(post.agent_id.upper(), style=f"bold {agent_color}")
        title.append(f" {stance_symbol} ", style="bold")
        title.append(post.stance.value.upper(), style=agent_color)

        # Triggers
        triggers = ", ".join(post.triggered_by) if post.triggered_by else "seed"

        # Content (truncated for display)
        content = post.content
        if len(content) > self.max_content_width:
            content = content[:self.max_content_width] + "..."

        body = Text()
        body.append(f"Triggers: {triggers}\n", style="dim")
        body.append(f"Novelty: {post.novelty_score:.2f}\n", style="dim")
        body.append(content)

        self.console.print(Panel(
            body,
            title=title,
            title_align="left",
            border_style=agent_color,
            padding=(0, 1),
        ))

    def show_phase_transition(self, signal: PhaseSignal) -> None:
        from rich.text import Text

        if signal.current_phase == self._current_phase:
            return

        self._current_phase = signal.current_phase
        phase_style = PHASE_STYLES.get(signal.current_phase, "bold")

        text = Text()
        text.append(">>> PHASE: ", style="bold")
        text.append(signal.current_phase.value.upper(), style=phase_style)
        text.append(f" (confidence: {signal.confidence:.2f})", style="dim")

        self.console.print(text)

        if signal.observation:
            obs_text = Text()
            obs_text.append("    Observer: ", style="bold dim")
            obs_text.append(signal.observation, style="italic")
            self.console.print(obs_text)

        self.console.print()

    def show_energy(self, update: EnergyUpdate) -> None:
        from rich.text import Text

        bar_len = 30
        filled = int(update.energy * bar_len)
        empty = bar_len - filled

        # Color based on energy level
        if update.energy > 0.6:
            bar_color = "green"
        elif update.energy > 0.3:
            bar_color = "yellow"
        else:
            bar_color = "red"

        text = Text()
        text.append("  Energy [", style="dim")
        text.append("#" * filled, style=bar_color)
        text.append("." * empty, style="dim")
        text.append(f"] {update.energy:.3f}", style="dim")

        # Show components inline
        if update.components:
            parts = []
            for key, value in update.components.items():
                parts.append(f"{key}={value:.2f}")
            text.append(f"  ({', '.join(parts)})", style="dim")

        self.console.print(text)
        self.console.print()

    def show_consensus(self, consensus: ConsensusMap) -> None:
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        # Summary panel
        self.console.print(Panel(
            consensus.summary,
            title="SYNTHESIS - Consensus Map",
            title_align="center",
            border_style="bright_magenta",
            padding=(1, 2),
        ))

        # Agreements & Disagreements table
        if consensus.agreements or consensus.disagreements:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Agreements", style="green", ratio=1)
            table.add_column("Disagreements", style="red", ratio=1)

            max_rows = max(len(consensus.agreements), len(consensus.disagreements))
            for i in range(max_rows):
                agree = consensus.agreements[i] if i < len(consensus.agreements) else ""
                disagree = consensus.disagreements[i] if i < len(consensus.disagreements) else ""
                table.add_row(f"+ {agree}" if agree else "", f"- {disagree}" if disagree else "")

            self.console.print(table)

        # Minority positions
        if consensus.minority_positions:
            self.console.print()
            self.console.print("[bold]Minority Positions:[/bold]")
            for pos in consensus.minority_positions:
                self.console.print(f"  ? {pos}", style="yellow")

        # Final stances
        if consensus.final_stances:
            self.console.print()
            stances_text = Text()
            stances_text.append("Final Stances: ", style="bold")
            for agent_id, stance in consensus.final_stances.items():
                color = AGENT_COLORS.get(agent_id, "white")
                symbol = STANCE_SYMBOLS.get(stance, "?")
                stances_text.append(f"{agent_id}", style=f"bold {color}")
                stances_text.append(f"({symbol}) ", style=color)
            self.console.print(stances_text)

    def show_footer(self, post_count: int, token_usage: Optional[dict] = None) -> None:
        from rich.text import Text

        self.console.print()
        text = Text()
        text.append(f"Deliberation complete: {post_count} posts generated.", style="bold")
        if token_usage:
            text.append(
                f"  Tokens: {token_usage['total_tokens']:,} "
                f"({token_usage['input_tokens']:,} in / "
                f"{token_usage['output_tokens']:,} out) "
                f"over {token_usage['calls']} calls",
                style="dim",
            )
        self.console.print(text)


class PlainDisplay:
    """Plain text fallback display when Rich is not available."""

    def __init__(self):
        self._post_count = 0
        self._current_phase = Phase.EXPLORE

    def show_header(self, hypothesis: str) -> None:
        print(f"\n{'='*70}")
        print("COLLOQUIP - Emergent Deliberation")
        print(f"{'='*70}")
        print(f"Hypothesis: {hypothesis}")
        print(f"{'='*70}\n")

    def show_post(self, post: Post) -> None:
        self._post_count += 1
        stance_label = post.stance.value.upper()
        agent_label = post.agent_id.upper()
        triggers = ", ".join(post.triggered_by) if post.triggered_by else "seed"

        print(f"[{self._post_count:02d}] {agent_label} | {post.phase.value.upper()} | {stance_label}")
        print(f"     Triggers: {triggers}")
        print(f"     Novelty: {post.novelty_score:.2f}")
        content = post.content[:200] + "..." if len(post.content) > 200 else post.content
        print(f"     {content}")
        print()

    def show_phase_transition(self, signal: PhaseSignal) -> None:
        if signal.current_phase == self._current_phase:
            return
        self._current_phase = signal.current_phase
        print(f"  >>> PHASE TRANSITION: {self._current_phase.value.upper()} "
              f"(confidence: {signal.confidence:.2f})")
        if signal.observation:
            print(f"  >>> Observer: {signal.observation}")
        print()

    def show_energy(self, update: EnergyUpdate) -> None:
        bar_len = int(update.energy * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)
        print(f"  Energy [{bar}] {update.energy:.3f}")
        print()

    def show_consensus(self, consensus: ConsensusMap) -> None:
        print(f"\n{'='*70}")
        print("SYNTHESIS - Consensus Map")
        print(f"{'='*70}")
        print(f"\nSummary: {consensus.summary}\n")
        if consensus.agreements:
            print("Agreements:")
            for a in consensus.agreements:
                print(f"  + {a}")
        if consensus.disagreements:
            print("\nDisagreements:")
            for d in consensus.disagreements:
                print(f"  - {d}")
        if consensus.minority_positions:
            print("\nMinority Positions:")
            for m in consensus.minority_positions:
                print(f"  ? {m}")
        print(f"\nFinal Stances: {consensus.final_stances}")
        print(f"\n{'='*70}")

    def show_footer(self, post_count: int, token_usage: Optional[dict] = None) -> None:
        msg = f"\nDeliberation complete: {post_count} posts generated."
        if token_usage:
            msg += (
                f"  Tokens: {token_usage['total_tokens']:,} "
                f"({token_usage['input_tokens']:,} in / {token_usage['output_tokens']:,} out)"
            )
        print(msg)


def create_display(use_rich: bool = True) -> "RichDisplay | PlainDisplay":
    """Create a display instance, falling back to plain text if Rich is not available."""
    if use_rich:
        try:
            return RichDisplay()
        except ImportError:
            pass
    return PlainDisplay()
