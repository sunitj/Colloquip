"""Tests for energy calculator and termination logic."""

import pytest

from colloquip.energy import EnergyCalculator
from colloquip.models import AgentStance, EnergySource, Phase

from tests.conftest import create_post


class TestEnergyCalculation:
    def test_empty_posts_returns_full_energy(self, energy_calculator):
        assert energy_calculator.calculate_energy([]) == 1.0

    def test_high_novelty_gives_high_energy(self, energy_calculator):
        posts = [create_post(novelty_score=0.8) for _ in range(5)]
        energy = energy_calculator.calculate_energy(posts)
        assert energy > 0.2

    def test_all_supportive_low_disagreement(self, energy_calculator):
        posts = [
            create_post(stance=AgentStance.SUPPORTIVE, novelty_score=0.5)
            for _ in range(5)
        ]
        energy = energy_calculator.calculate_energy(posts)
        # With 0% disagreement, disagreement component is 0
        # Energy should come primarily from novelty
        assert energy > 0.0

    def test_mixed_stances_moderate_energy(self, energy_calculator):
        posts = [
            create_post(stance=AgentStance.SUPPORTIVE, novelty_score=0.5),
            create_post(stance=AgentStance.CRITICAL, novelty_score=0.5, agent_id="chemistry"),
            create_post(stance=AgentStance.SUPPORTIVE, novelty_score=0.5, agent_id="admet"),
            create_post(stance=AgentStance.CRITICAL, novelty_score=0.5, agent_id="clinical"),
            create_post(stance=AgentStance.NEUTRAL, novelty_score=0.5, agent_id="regulatory"),
        ]
        energy = energy_calculator.calculate_energy(posts)
        assert 0.0 < energy < 1.0

    def test_energy_always_clamped(self, energy_calculator):
        # Even extreme inputs should be clamped
        posts = [create_post(novelty_score=0.0, stance=AgentStance.SUPPORTIVE) for _ in range(10)]
        energy = energy_calculator.calculate_energy(posts)
        assert 0.0 <= energy <= 1.0

    def test_novel_connection_bonus(self, energy_calculator):
        posts_without = [create_post(novelty_score=0.5) for _ in range(5)]
        posts_with = [
            create_post(novelty_score=0.5, stance=AgentStance.NOVEL_CONNECTION)
            for _ in range(5)
        ]
        e_without = energy_calculator.calculate_energy(posts_without)
        e_with = energy_calculator.calculate_energy(posts_with)
        assert e_with > e_without


class TestStaleness:
    def test_repetitive_content_increases_staleness(self, energy_calculator):
        # Same content repeated = high staleness
        same_posts = [
            create_post(content="The mechanism involves receptor binding", novelty_score=0.3)
            for _ in range(5)
        ]
        diverse_posts = [
            create_post(content=f"Unique topic number {i} about different things", novelty_score=0.3)
            for i in range(5)
        ]
        e_same = energy_calculator.calculate_energy(same_posts)
        e_diverse = energy_calculator.calculate_energy(diverse_posts)
        # Diverse content should have more energy (less staleness penalty)
        assert e_diverse >= e_same

    def test_no_recent_novelty_increases_staleness(self, energy_calculator):
        posts = [create_post(novelty_score=0.1) for _ in range(10)]
        energy = energy_calculator.calculate_energy(posts)
        # Low novelty = high staleness penalty
        assert energy < 0.5


class TestTermination:
    def test_no_termination_before_min_posts(self, energy_calculator):
        posts = [create_post() for _ in range(5)]  # Below min_posts (12)
        energy_history = [0.1, 0.1, 0.1]  # Below threshold
        should_stop, _ = energy_calculator.should_terminate(posts, energy_history)
        assert not should_stop

    def test_terminates_on_sustained_low_energy(self, energy_calculator):
        posts = [create_post() for _ in range(15)]
        energy_history = [0.5, 0.4, 0.3, 0.15, 0.1, 0.1]
        should_stop, reason = energy_calculator.should_terminate(posts, energy_history)
        assert should_stop
        assert "low_energy" in reason

    def test_terminates_on_max_posts(self, energy_calculator):
        posts = [create_post() for _ in range(50)]  # max_posts default
        energy_history = [0.5]
        should_stop, reason = energy_calculator.should_terminate(posts, energy_history)
        assert should_stop
        assert "max_posts" in reason

    def test_no_termination_with_high_energy(self, energy_calculator):
        posts = [create_post() for _ in range(15)]
        energy_history = [0.7, 0.65, 0.6]
        should_stop, _ = energy_calculator.should_terminate(posts, energy_history)
        assert not should_stop

    def test_declining_energy_with_all_agents(self, energy_calculator):
        agents = ["biology", "chemistry", "admet", "clinical", "regulatory", "redteam"]
        posts = [create_post(agent_id=a) for a in agents] + [create_post() for _ in range(8)]
        # Trend: 0.35 - 0.7 = -0.35 < -0.2, and last value 0.35 < 0.4
        energy_history = [0.8, 0.7, 0.5, 0.35]
        should_stop, reason = energy_calculator.should_terminate(posts, energy_history)
        assert should_stop
        assert "declining_energy" in reason


class TestEnergyInjection:
    def test_human_intervention_boost(self, energy_calculator):
        result = energy_calculator.inject_energy(EnergySource.HUMAN_INTERVENTION, 0.3)
        assert result == pytest.approx(0.7, abs=0.01)

    def test_injection_capped_at_one(self, energy_calculator):
        result = energy_calculator.inject_energy(EnergySource.HUMAN_INTERVENTION, 0.9)
        assert result == 1.0

    def test_novel_post_boost(self, energy_calculator):
        result = energy_calculator.inject_energy(EnergySource.NOVEL_POST, 0.5)
        assert result == pytest.approx(0.7, abs=0.01)


class TestEnergyUpdate:
    def test_energy_update_has_components(self, energy_calculator):
        posts = [create_post(novelty_score=0.6) for _ in range(5)]
        update = energy_calculator.calculate_energy_update(posts, turn=1)
        assert "novelty" in update.components
        assert "disagreement" in update.components
        assert "questions" in update.components
        assert "staleness" in update.components
        assert 0.0 <= update.energy <= 1.0
