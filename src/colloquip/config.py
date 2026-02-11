"""Configuration loading and defaults for Colloquip."""

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

from colloquip.models import EngineConfig, Phase


class ObserverConfig(BaseModel):
    hysteresis_threshold: int = Field(default=3, ge=1)
    window_size: int = Field(default=10, ge=1)
    min_posts_before_converge: int = 12
    observation_frequency: float = 0.2

    # Phase detection thresholds
    explore_question_rate_min: float = 0.3
    explore_topic_diversity_min: float = 0.6
    debate_disagreement_rate_min: float = 0.4
    debate_citation_density_min: float = 0.5
    deepen_topic_diversity_max: float = 0.5
    deepen_novelty_avg_min: float = 0.5
    converge_energy_max: float = 0.3
    converge_posts_since_novel_min: int = 5


class EnergyConfig(BaseModel):
    window: int = 10
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "novelty": 0.4,
        "disagreement": 0.3,
        "questions": 0.2,
        "staleness": -0.1,
    })
    novelty_bonus_per_connection: float = 0.1
    max_novelty_bonus: float = 0.3
    optimal_disagreement_rate: float = 0.4
    max_open_questions: int = Field(default=5, ge=1)
    posts_since_novel_threshold: int = 10
    repetition_weight: float = 2.0

    # Termination
    min_posts: int = Field(default=12, ge=1)
    max_posts: int = Field(default=50, ge=1)
    energy_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    low_energy_rounds: int = Field(default=3, ge=1)

    # Energy injection amounts
    injection: Dict[str, float] = Field(default_factory=lambda: {
        "new_knowledge": 0.3,
        "human_intervention": 0.4,
        "novel_post": 0.2,
        "red_team_challenge": 0.15,
    })

    @model_validator(mode="after")
    def validate_post_bounds(self) -> "EnergyConfig":
        if self.min_posts >= self.max_posts:
            raise ValueError(
                f"min_posts ({self.min_posts}) must be less than max_posts ({self.max_posts})"
            )
        return self


class TriggerConfig(BaseModel):
    window: int = 5
    refractory_period: int = 2

    relevance_min_keyword_matches: int = 2
    relevance_phase_modulation: Dict[str, int] = Field(default_factory=lambda: {
        "explore": 1,
        "debate": 2,
        "deepen": 3,
        "converge": 3,
    })

    silence_min_conversation_length: int = 8
    silence_max: int = 6
    silence_phase_modulation: Dict[str, int] = Field(default_factory=lambda: {
        "explore": 4,
        "debate": 6,
        "deepen": 8,
        "converge": 6,
    })

    bridge_min_agents: int = 2

    red_team_consensus_threshold: int = 3
    red_team_criticism_gap: int = 3
    red_team_min_debate_posts: int = 15


class ColloquipConfig(BaseModel):
    """Top-level configuration combining all sub-configs."""
    engine: EngineConfig = Field(default_factory=EngineConfig)
    observer: ObserverConfig = Field(default_factory=ObserverConfig)
    energy: EnergyConfig = Field(default_factory=EnergyConfig)
    triggers: TriggerConfig = Field(default_factory=TriggerConfig)


def load_config(
    engine_path: Optional[Path] = None,
    agents_path: Optional[Path] = None,
) -> ColloquipConfig:
    """Load configuration from YAML files, merging with defaults."""
    config_data: Dict = {}

    if engine_path and engine_path.exists():
        with open(engine_path) as f:
            config_data = yaml.safe_load(f) or {}

    return ColloquipConfig(**config_data)


def load_agents_config(path: Optional[Path] = None) -> Dict:
    """Load agent configurations from YAML."""
    if path and path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
            return data.get("agents", {})
    return {}
