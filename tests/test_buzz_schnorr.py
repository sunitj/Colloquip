"""BIP-340 Schnorr signature tests.

The authoritative test vectors from the BIP itself live in
``tests/fixtures/bip340_test_vectors.csv``. They cover the cases that break
naive implementations: point at infinity, non-quadratic-residue nonces,
out-of-range r/s values, and public keys not on the curve.
"""

import csv
from pathlib import Path

import pytest

from colloquip.buzz.schnorr import (
    N,
    P,
    SchnorrError,
    has_even_y,
    lift_x,
    point_add,
    point_mul,
    pubkey_from_privkey,
    schnorr_sign,
    schnorr_verify,
    tagged_hash,
)

VECTORS_PATH = Path(__file__).parent / "fixtures" / "bip340_test_vectors.csv"


def load_vectors():
    with VECTORS_PATH.open() as handle:
        return list(csv.DictReader(handle))


VECTORS = load_vectors()


def test_vectors_file_is_present_and_complete():
    assert len(VECTORS) >= 15, "BIP-340 vector fixture looks truncated"


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: f"vec{v['index']}")
def test_bip340_verification_vectors(vector):
    """Every vector must verify (or fail to) exactly as the BIP says."""
    expected = vector["verification result"] == "TRUE"
    try:
        result = schnorr_verify(
            bytes.fromhex(vector["message"]),
            bytes.fromhex(vector["public key"]),
            bytes.fromhex(vector["signature"]),
        )
    except ValueError:
        result = False
    assert result is expected, vector["comment"]


@pytest.mark.parametrize(
    "vector", [v for v in VECTORS if v["secret key"]], ids=lambda v: f"vec{v['index']}"
)
def test_bip340_signing_vectors(vector):
    """Signing must reproduce the BIP's signatures byte for byte."""
    derived = pubkey_from_privkey(bytes.fromhex(vector["secret key"]))
    assert derived.hex().upper() == vector["public key"]

    signature = schnorr_sign(
        bytes.fromhex(vector["message"]),
        bytes.fromhex(vector["secret key"]),
        bytes.fromhex(vector["aux_rand"]),
    )
    assert signature.hex().upper() == vector["signature"]


def test_sign_and_verify_round_trip():
    privkey = bytes.fromhex(f"{12345:064x}")
    pubkey = pubkey_from_privkey(privkey)
    message = b"\x42" * 32
    assert schnorr_verify(message, pubkey, schnorr_sign(message, privkey))


def test_signature_does_not_verify_for_a_different_message():
    privkey = bytes.fromhex(f"{999:064x}")
    pubkey = pubkey_from_privkey(privkey)
    signature = schnorr_sign(b"\x01" * 32, privkey)
    assert not schnorr_verify(b"\x02" * 32, pubkey, signature)


def test_signature_does_not_verify_for_a_different_key():
    message = b"\x07" * 32
    signature = schnorr_sign(message, bytes.fromhex(f"{111:064x}"))
    other = pubkey_from_privkey(bytes.fromhex(f"{222:064x}"))
    assert not schnorr_verify(message, other, signature)


def test_aux_rand_changes_the_signature_but_not_validity():
    privkey = bytes.fromhex(f"{31337:064x}")
    pubkey = pubkey_from_privkey(privkey)
    message = b"\x11" * 32

    first = schnorr_sign(message, privkey, b"\x00" * 32)
    second = schnorr_sign(message, privkey, b"\xff" * 32)

    assert first != second
    assert schnorr_verify(message, pubkey, first)
    assert schnorr_verify(message, pubkey, second)


def test_default_aux_rand_is_deterministic():
    """Colloquip relies on this for reproducible event ids in tests."""
    privkey = bytes.fromhex(f"{7:064x}")
    assert schnorr_sign(b"\x05" * 32, privkey) == schnorr_sign(b"\x05" * 32, privkey)


def test_arbitrary_length_messages_are_supported():
    privkey = bytes.fromhex(f"{2024:064x}")
    pubkey = pubkey_from_privkey(privkey)
    for message in (b"", b"short", b"x" * 1000):
        assert schnorr_verify(message, pubkey, schnorr_sign(message, privkey))


@pytest.mark.parametrize("bad_key", [b"\x00" * 32, N.to_bytes(32, "big")])
def test_out_of_range_private_keys_are_rejected(bad_key):
    with pytest.raises(SchnorrError):
        pubkey_from_privkey(bad_key)


def test_wrong_length_inputs_are_rejected():
    with pytest.raises(SchnorrError):
        schnorr_sign(b"\x00" * 32, b"\x01" * 31)
    with pytest.raises(SchnorrError):
        schnorr_sign(b"\x00" * 32, b"\x01" * 32, aux_rand=b"\x00" * 16)


def test_malformed_signatures_and_pubkeys_return_false():
    assert not schnorr_verify(b"\x00" * 32, b"\x01" * 31, b"\x00" * 64)
    assert not schnorr_verify(b"\x00" * 32, b"\x01" * 32, b"\x00" * 63)


def test_tagged_hash_matches_the_bip_definition():
    import hashlib

    tag_hash = hashlib.sha256(b"BIP0340/aux").digest()
    expected = hashlib.sha256(tag_hash + tag_hash + b"payload").digest()
    assert tagged_hash("BIP0340/aux", b"payload") == expected


def test_lift_x_returns_the_even_y_point():
    point = lift_x(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798)
    assert point is not None and has_even_y(point)


def test_lift_x_rejects_coordinates_off_the_curve():
    assert lift_x(P) is None  # out of field range
    assert lift_x(0) is None  # y^2 = 7 has no square root mod p


def test_point_arithmetic_identities():
    from colloquip.buzz.schnorr import G

    assert point_add(None, G) == G
    assert point_add(G, None) == G
    # G + (-G) is the point at infinity
    assert point_add(G, (G[0], P - G[1])) is None
    # scalar multiplication by the group order wraps to infinity
    assert point_mul(G, N) is None


def test_scalar_multiplication_edge_cases():
    """Guards the Jacobian fast path against the cases that break it."""
    from colloquip.buzz.schnorr import G

    assert point_mul(G, 0) is None
    assert point_mul(None, 5) is None
    assert point_mul(G, 1) == G
    # doubling and repeated addition must agree
    assert point_add(point_mul(G, 3), point_mul(G, 3)) == point_mul(G, 6)
    # addition is associative over the group
    assert point_add(point_mul(G, 5), point_mul(G, 7)) == point_mul(G, 12)
    # multiplication composes
    assert point_mul(point_mul(G, 3), 4) == point_mul(G, 12)
    # n+1 wraps back around to G
    assert point_mul(G, N + 1) == G
