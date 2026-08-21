"""Key derivation, encoding, and identity tests for the Buzz adapter."""

import pytest

from colloquip.buzz.bech32 import (
    Bech32Error,
    bech32_decode,
    bech32_encode,
    from_npub,
    from_nsec,
    to_npub,
    to_nsec,
)
from colloquip.buzz.keys import (
    BuzzKeypair,
    derive_agent_keypair,
    keypair_from_private,
    normalize_pubkey,
)
from colloquip.buzz.schnorr import SchnorrError, schnorr_verify

# Test vectors published in NIP-19.
NIP19_PUBKEY_HEX = "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"
NIP19_NPUB = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
NIP19_PRIVKEY_HEX = "67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa"
NIP19_NSEC = "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe5"


class TestBech32:
    def test_npub_matches_the_nip19_vector(self):
        assert to_npub(NIP19_PUBKEY_HEX) == NIP19_NPUB

    def test_nsec_matches_the_nip19_vector(self):
        assert to_nsec(NIP19_PRIVKEY_HEX) == NIP19_NSEC

    def test_npub_decodes_back_to_hex(self):
        assert from_npub(NIP19_NPUB) == NIP19_PUBKEY_HEX

    def test_nsec_decodes_back_to_hex(self):
        assert from_nsec(NIP19_NSEC) == NIP19_PRIVKEY_HEX

    def test_round_trip_for_arbitrary_payloads(self):
        payload = bytes(range(32))
        hrp, decoded = bech32_decode(bech32_encode("npub", payload))
        assert hrp == "npub" and decoded == payload

    def test_checksum_errors_are_detected(self):
        corrupted = NIP19_NPUB[:-1] + ("q" if NIP19_NPUB[-1] != "q" else "p")
        with pytest.raises(Bech32Error):
            bech32_decode(corrupted)

    def test_mixed_case_is_rejected(self):
        with pytest.raises(Bech32Error):
            bech32_decode("npub1QQQQ")

    def test_wrong_prefix_is_rejected(self):
        with pytest.raises(Bech32Error):
            from_npub(NIP19_NSEC)
        with pytest.raises(Bech32Error):
            from_nsec(NIP19_NPUB)

    def test_wrong_payload_length_is_rejected(self):
        with pytest.raises(Bech32Error):
            from_npub(bech32_encode("npub", b"\x01" * 16))


class TestKeypairFromPrivate:
    def test_accepts_hex(self):
        keypair = keypair_from_private(NIP19_PRIVKEY_HEX)
        assert keypair.private_hex == NIP19_PRIVKEY_HEX
        assert len(keypair.public_hex) == 64

    def test_accepts_nsec(self):
        assert keypair_from_private(NIP19_NSEC).private_hex == NIP19_PRIVKEY_HEX

    def test_hex_and_nsec_produce_the_same_identity(self):
        assert (
            keypair_from_private(NIP19_NSEC).public_hex
            == keypair_from_private(NIP19_PRIVKEY_HEX).public_hex
        )

    def test_accepts_a_0x_prefix_and_surrounding_whitespace(self):
        assert keypair_from_private(f"  0x{NIP19_PRIVKEY_HEX}  ").private_hex == NIP19_PRIVKEY_HEX

    def test_rejects_non_hex(self):
        with pytest.raises(SchnorrError):
            keypair_from_private("nothexatall" * 6)

    def test_rejects_wrong_length(self):
        with pytest.raises(SchnorrError):
            keypair_from_private("ab" * 16)

    def test_repr_does_not_leak_the_private_key(self):
        keypair = keypair_from_private(NIP19_PRIVKEY_HEX)
        assert NIP19_PRIVKEY_HEX not in repr(keypair)
        assert keypair.public_hex in repr(keypair)


class TestAgentKeyDerivation:
    def test_derivation_is_deterministic(self):
        first = derive_agent_keypair("seed-a", "biology")
        second = derive_agent_keypair("seed-a", "biology")
        assert first == second

    def test_different_agents_get_different_identities(self):
        seed = "seed-a"
        pubkeys = {
            derive_agent_keypair(seed, agent).public_hex
            for agent in ("biology", "chemistry", "clinical", "red_team")
        }
        assert len(pubkeys) == 4

    def test_different_seeds_rotate_every_identity(self):
        assert (
            derive_agent_keypair("seed-a", "biology").public_hex
            != derive_agent_keypair("seed-b", "biology").public_hex
        )

    def test_an_empty_seed_is_rejected(self):
        with pytest.raises(SchnorrError):
            derive_agent_keypair("", "biology")

    def test_derived_keys_can_sign_verifiably(self):
        keypair = derive_agent_keypair("seed-a", "biology")
        digest = b"\x09" * 32
        signature = keypair.sign(digest)
        assert schnorr_verify(digest, bytes.fromhex(keypair.public_hex), bytes.fromhex(signature))

    def test_npub_and_nsec_round_trip(self):
        keypair = derive_agent_keypair("seed-a", "biology")
        assert from_npub(keypair.npub) == keypair.public_hex
        assert from_nsec(keypair.nsec) == keypair.private_hex


class TestNormalizePubkey:
    def test_accepts_npub(self):
        assert normalize_pubkey(NIP19_NPUB) == NIP19_PUBKEY_HEX

    def test_accepts_hex_in_any_case(self):
        assert normalize_pubkey(NIP19_PUBKEY_HEX.upper()) == NIP19_PUBKEY_HEX

    def test_rejects_short_hex(self):
        with pytest.raises(Bech32Error):
            normalize_pubkey("abcd")

    def test_rejects_non_hex(self):
        with pytest.raises(ValueError):
            normalize_pubkey("z" * 64)


def test_keypair_is_hashable_and_comparable():
    """Keypairs land in sets and dicts inside the mirror."""
    a = BuzzKeypair(private_hex="01" * 32, public_hex="02" * 32)
    b = BuzzKeypair(private_hex="01" * 32, public_hex="02" * 32)
    assert a == b and len({a, b}) == 1
