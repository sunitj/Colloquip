"""Tests for configuration loading."""

from pathlib import Path

import pytest

from colloquip.config import (
    ColloquipConfig,
    EnergyConfig,
    ObserverConfig,
    load_config,
)


class TestDefaults:
    def test_default_engine_config(self):
        config = ColloquipConfig()
        assert config.engine.max_turns == 30
        assert config.engine.min_posts == 12
        assert config.engine.energy_threshold == 0.2

    def test_default_observer_config(self):
        config = ColloquipConfig()
        assert config.observer.hysteresis_threshold == 2
        assert config.observer.window_size == 5

    def test_default_energy_config(self):
        config = ColloquipConfig()
        assert config.energy.weights["novelty"] == 0.4
        assert config.energy.weights["disagreement"] == 0.3

    def test_default_trigger_config(self):
        config = ColloquipConfig()
        assert config.triggers.refractory_period == 2
        assert config.triggers.window == 5


class TestYAMLLoading:
    def test_load_from_yaml(self):
        config = load_config(
            engine_path=Path("config/engine.yaml"),
        )
        assert config.engine.max_turns == 30
        assert config.observer.hysteresis_threshold == 2

    def test_load_nonexistent_uses_defaults(self):
        config = load_config(
            engine_path=Path("nonexistent.yaml"),
        )
        assert config.engine.max_turns == 30


class TestValidation:
    def test_valid_config(self):
        config = EnergyConfig(window=5, min_posts=6)
        assert config.window == 5
        assert config.min_posts == 6

    def test_min_posts_must_be_less_than_max_posts(self):
        with pytest.raises(ValueError, match="min_posts.*must be less than max_posts"):
            EnergyConfig(min_posts=50, max_posts=50)

    def test_min_posts_greater_than_max_posts_fails(self):
        with pytest.raises(ValueError):
            EnergyConfig(min_posts=60, max_posts=50)

    def test_max_open_questions_must_be_positive(self):
        with pytest.raises(ValueError):
            EnergyConfig(max_open_questions=0)

    def test_hysteresis_threshold_must_be_positive(self):
        with pytest.raises(ValueError):
            ObserverConfig(hysteresis_threshold=0)

    def test_energy_threshold_bounds(self):
        with pytest.raises(ValueError):
            EnergyConfig(energy_threshold=1.5)
