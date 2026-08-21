"""Nostr event construction, id derivation, and signing tests."""

import hashlib
import json

import pytest

from colloquip.buzz.events import (
    NostrEvent,
    build_event,
    build_json_event,
    channel_tag,
    reply_tag,
    root_tag,
)
from colloquip.buzz.keys import derive_agent_keypair
from colloquip.buzz.kinds import KIND_CHAT, KIND_COLLOQUIP_POST, is_ephemeral

KEYPAIR = derive_agent_keypair("test-seed", "biology")
OTHER = derive_agent_keypair("test-seed", "chemistry")


class TestSerialization:
    def test_serialization_matches_the_nip01_form(self):
        event = NostrEvent(
            kind=1, content="hello", pubkey=KEYPAIR.public_hex, tags=[["h", "c1"]], created_at=1700
        )
        assert event.serialize() == json.dumps(
            [0, KEYPAIR.public_hex, 1700, 1, [["h", "c1"]], "hello"],
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def test_serialization_has_no_whitespace(self):
        event = NostrEvent(kind=1, content="a b", pubkey=KEYPAIR.public_hex, created_at=1)
        assert ", " not in event.serialize() and ": " not in event.serialize()

    def test_non_ascii_content_is_not_escaped(self):
        """NIP-01 requires raw UTF-8, not \\uXXXX escapes."""
        event = NostrEvent(kind=1, content="mitochondrió — π", pubkey=KEYPAIR.public_hex)
        assert "mitochondrió — π" in event.serialize()
        assert "\\u" not in event.serialize()

    def test_id_is_the_sha256_of_the_serialization(self):
        event = NostrEvent(kind=1, content="x", pubkey=KEYPAIR.public_hex, created_at=5)
        expected = hashlib.sha256(event.serialize().encode("utf-8")).hexdigest()
        assert event.compute_id() == expected

    def test_id_changes_when_any_field_changes(self):
        base = NostrEvent(kind=1, content="x", pubkey=KEYPAIR.public_hex, created_at=5)
        ids = {base.compute_id()}
        for mutate in (
            lambda e: setattr(e, "content", "y"),
            lambda e: setattr(e, "kind", 2),
            lambda e: setattr(e, "created_at", 6),
            lambda e: setattr(e, "tags", [["h", "c"]]),
        ):
            event = NostrEvent(kind=1, content="x", pubkey=KEYPAIR.public_hex, created_at=5)
            mutate(event)
            ids.add(event.compute_id())
        assert len(ids) == 5


class TestSigning:
    def test_signed_events_verify(self):
        event = build_event(KIND_CHAT, "hello", KEYPAIR, created_at=1700)
        assert event.id and event.sig
        assert event.verify()

    def test_signing_is_deterministic_with_the_default_aux(self):
        first = build_event(KIND_CHAT, "hello", KEYPAIR, created_at=1700)
        second = build_event(KIND_CHAT, "hello", KEYPAIR, created_at=1700)
        assert first.id == second.id and first.sig == second.sig

    def test_tampering_with_content_invalidates_the_event(self):
        event = build_event(KIND_CHAT, "original", KEYPAIR, created_at=1700)
        event.content = "tampered"
        assert not event.verify()

    def test_tampering_with_the_signature_invalidates_the_event(self):
        event = build_event(KIND_CHAT, "original", KEYPAIR, created_at=1700)
        event.sig = "00" * 64
        assert not event.verify()

    def test_an_event_signed_by_one_key_fails_under_another(self):
        event = build_event(KIND_CHAT, "hi", KEYPAIR, created_at=1700)
        event.pubkey = OTHER.public_hex
        assert not event.verify()

    def test_signing_with_a_mismatched_keypair_is_refused(self):
        event = NostrEvent(kind=1, content="x", pubkey=OTHER.public_hex)
        with pytest.raises(ValueError, match="cannot sign"):
            event.sign(KEYPAIR)

    def test_unsigned_events_do_not_verify(self):
        assert not NostrEvent(kind=1, content="x", pubkey=KEYPAIR.public_hex).verify()


class TestSerializationRoundTrip:
    def test_to_dict_and_from_dict_preserve_validity(self):
        event = build_event(KIND_CHAT, "hello", KEYPAIR, tags=[channel_tag("c1")])
        restored = NostrEvent.from_dict(event.to_dict())
        assert restored.verify()
        assert restored.id == event.id

    def test_to_dict_has_exactly_the_wire_fields(self):
        event = build_event(KIND_CHAT, "hello", KEYPAIR)
        assert set(event.to_dict()) == {
            "id",
            "pubkey",
            "created_at",
            "kind",
            "tags",
            "content",
            "sig",
        }

    def test_from_dict_tolerates_missing_optional_fields(self):
        restored = NostrEvent.from_dict({"kind": 9, "pubkey": KEYPAIR.public_hex})
        assert restored.content == "" and restored.tags == []


class TestJsonEvents:
    def test_json_payload_round_trips(self):
        payload = {"stance": "support", "novelty_score": 0.7, "key_claims": ["a", "b"]}
        event = build_json_event(KIND_COLLOQUIP_POST, payload, KEYPAIR)
        assert json.loads(event.content) == payload
        assert event.verify()

    def test_json_content_is_compact(self):
        event = build_json_event(KIND_COLLOQUIP_POST, {"a": 1, "b": 2}, KEYPAIR)
        assert event.content == '{"a":1,"b":2}'


class TestTags:
    def test_tag_helpers_produce_the_expected_shapes(self):
        assert channel_tag("c1") == ["h", "c1"]
        assert reply_tag("abc") == ["e", "abc", "", "reply"]
        assert root_tag("abc") == ["e", "abc", "", "root"]

    def test_tag_value_returns_the_first_match(self):
        event = NostrEvent(
            kind=1, content="", pubkey=KEYPAIR.public_hex, tags=[["e", "one"], ["e", "two"]]
        )
        assert event.tag_value("e") == "one"
        assert event.tag_values("e") == ["one", "two"]

    def test_tag_value_returns_none_when_absent(self):
        assert NostrEvent(kind=1, content="", pubkey=KEYPAIR.public_hex).tag_value("h") is None

    def test_channel_property_reads_the_h_tag(self):
        event = NostrEvent(
            kind=1, content="", pubkey=KEYPAIR.public_hex, tags=[channel_tag("chan-9")]
        )
        assert event.channel == "chan-9"

    def test_malformed_tags_do_not_crash_lookups(self):
        event = NostrEvent(kind=1, content="", pubkey=KEYPAIR.public_hex, tags=[["h"], []])
        assert event.tag_value("h") is None


def test_ephemeral_kind_classification():
    assert is_ephemeral(20100)
    assert not is_ephemeral(41000)
    assert not is_ephemeral(9)
