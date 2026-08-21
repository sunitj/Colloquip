"""Configuration and gating tests for the Buzz adapter.

The invariant under test: unless Buzz is explicitly enabled *and* fully
configured, ``create_mirror`` returns ``None`` and Colloquip behaves exactly as
it did before the adapter existed.
"""

import pytest

from colloquip.buzz.config import BuzzSettings, create_mirror, load_buzz_settings
from colloquip.buzz.keys import keypair_from_private

VALID_KEY = "67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa"

BUZZ_ENV_VARS = [
    "BUZZ_ENABLED",
    "BUZZ_RELAY_URL",
    "BUZZ_PRIVATE_KEY",
    "BUZZ_AGENT_KEY_SEED",
    "BUZZ_PUBLISH_ENERGY",
    "BUZZ_PUBLISH_PROSE",
    "BUZZ_ACCEPT_INTERVENTIONS",
    "BUZZ_CONNECT_TIMEOUT",
    "BUZZ_PUBLISH_TIMEOUT",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in BUZZ_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def fully_configured(**overrides) -> BuzzSettings:
    fields = {
        "enabled": True,
        "relay_url": "ws://relay.test",
        "private_key": VALID_KEY,
        "agent_key_seed": "seed",
    }
    fields.update(overrides)
    return BuzzSettings(**fields)


class TestDefaults:
    def test_the_adapter_is_off_by_default(self):
        assert load_buzz_settings().enabled is False

    def test_defaults_are_not_considered_configured(self):
        assert BuzzSettings().configured is False

    def test_prose_energy_and_interventions_default_on(self):
        settings = load_buzz_settings()
        assert settings.publish_energy
        assert settings.publish_prose
        assert settings.accept_interventions


class TestEnvironmentLoading:
    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
    def test_truthy_flag_values(self, monkeypatch, value):
        monkeypatch.setenv("BUZZ_ENABLED", value)
        assert load_buzz_settings().enabled is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "maybe"])
    def test_falsy_flag_values(self, monkeypatch, value):
        monkeypatch.setenv("BUZZ_ENABLED", value)
        assert load_buzz_settings().enabled is False

    def test_all_fields_load_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("BUZZ_ENABLED", "true")
        monkeypatch.setenv("BUZZ_RELAY_URL", "wss://buzz.example/relay")
        monkeypatch.setenv("BUZZ_PRIVATE_KEY", VALID_KEY)
        monkeypatch.setenv("BUZZ_AGENT_KEY_SEED", "the-seed")
        monkeypatch.setenv("BUZZ_PUBLISH_ENERGY", "false")
        monkeypatch.setenv("BUZZ_ACCEPT_INTERVENTIONS", "false")
        monkeypatch.setenv("BUZZ_CONNECT_TIMEOUT", "2.5")

        settings = load_buzz_settings()
        assert settings.relay_url == "wss://buzz.example/relay"
        assert settings.private_key == VALID_KEY
        assert settings.agent_key_seed == "the-seed"
        assert settings.publish_energy is False
        assert settings.accept_interventions is False
        assert settings.connect_timeout == 2.5

    def test_non_positive_timeouts_are_rejected(self):
        with pytest.raises(ValueError):
            BuzzSettings(connect_timeout=0)


class TestConfiguredPredicate:
    def test_a_complete_configuration_is_configured(self):
        assert fully_configured().configured is True

    @pytest.mark.parametrize("missing", ["relay_url", "private_key", "agent_key_seed"])
    def test_any_missing_field_leaves_it_unconfigured(self, missing):
        assert fully_configured(**{missing: ""}).configured is False

    def test_disabled_is_never_configured(self):
        settings = fully_configured()
        settings.enabled = False
        assert settings.configured is False


class TestCreateMirror:
    def test_disabled_returns_none(self):
        assert create_mirror(BuzzSettings()) is None

    @pytest.mark.parametrize("missing", ["relay_url", "private_key", "agent_key_seed"])
    def test_incomplete_configuration_returns_none_instead_of_raising(self, missing, caplog):
        assert create_mirror(fully_configured(**{missing: ""})) is None
        assert "mirror disabled" in caplog.text

    def test_an_invalid_private_key_returns_none_instead_of_raising(self, caplog):
        assert create_mirror(fully_configured(private_key="not-a-key")) is None
        assert "Invalid BUZZ_PRIVATE_KEY" in caplog.text

    def test_a_valid_configuration_builds_a_mirror(self):
        mirror = create_mirror(fully_configured())
        assert mirror is not None
        assert mirror.service_pubkey == keypair_from_private(VALID_KEY).public_hex

    def test_an_nsec_private_key_is_accepted(self):
        nsec = keypair_from_private(VALID_KEY).nsec
        mirror = create_mirror(fully_configured(private_key=nsec))
        assert mirror is not None
        assert mirror.service_pubkey == keypair_from_private(VALID_KEY).public_hex

    def test_flags_are_passed_through_to_the_mirror(self):
        mirror = create_mirror(fully_configured(publish_energy=False, publish_prose=False))
        assert mirror._publish_energy is False
        assert mirror._publish_prose is False

    def test_it_reads_the_environment_when_given_no_settings(self, monkeypatch):
        monkeypatch.setenv("BUZZ_ENABLED", "true")
        monkeypatch.setenv("BUZZ_RELAY_URL", "ws://relay.test")
        monkeypatch.setenv("BUZZ_PRIVATE_KEY", VALID_KEY)
        monkeypatch.setenv("BUZZ_AGENT_KEY_SEED", "seed")
        assert create_mirror() is not None


class TestTopLevelSettings:
    def test_buzz_settings_are_part_of_the_application_settings(self):
        from colloquip.settings import load_settings

        assert load_settings().buzz.enabled is False

    def test_enabling_buzz_shows_up_in_application_settings(self, monkeypatch):
        from colloquip.settings import load_settings

        monkeypatch.setenv("BUZZ_ENABLED", "true")
        monkeypatch.setenv("BUZZ_RELAY_URL", "ws://relay.test")
        assert load_settings().buzz.relay_url == "ws://relay.test"
