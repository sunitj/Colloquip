"""BIP-340 Schnorr signatures over secp256k1 — pure Python, zero dependencies.

Nostr events are signed with BIP-340 Schnorr signatures over x-only public
keys. Rather than pull in a native extension (``coincurve`` / ``secp256k1``)
just to talk to a relay, we implement the curve arithmetic directly. Colloquip
signs a handful of events per deliberation turn, so the ~5 ms cost of a pure
Python scalar multiplication is irrelevant next to an LLM call.

This follows the reference implementation published in BIP-340. The official
BIP-340 test vectors are exercised in ``tests/test_buzz_schnorr.py``.
"""

import hashlib
from typing import Optional, Tuple

# secp256k1 domain parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)

Point = Optional[Tuple[int, int]]


class SchnorrError(ValueError):
    """Raised when a key, nonce, or signature is not usable."""


def _x(point: Point) -> int:
    assert point is not None
    return point[0]


def _y(point: Point) -> int:
    assert point is not None
    return point[1]


def point_add(p1: Point, p2: Point) -> Point:
    """Add two points on secp256k1 (``None`` is the point at infinity)."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if _x(p1) == _x(p2) and _y(p1) != _y(p2):
        return None
    if p1 == p2:
        lam = (3 * _x(p1) * _x(p1) * pow(2 * _y(p1), P - 2, P)) % P
    else:
        lam = ((_y(p2) - _y(p1)) * pow(_x(p2) - _x(p1), P - 2, P)) % P
    x3 = (lam * lam - _x(p1) - _x(p2)) % P
    return (x3, (lam * (_x(p1) - x3) - _y(p1)) % P)


# Jacobian coordinates: (X, Y, Z) represents the affine point (X/Z², Y/Z³).
# Working projectively lets scalar multiplication defer modular inversion to a
# single conversion at the end instead of one per point addition, which is the
# difference between ~90 ms and ~5 ms per operation in pure Python.
_JacobianPoint = Optional[Tuple[int, int, int]]


def _jacobian_double(point: _JacobianPoint) -> _JacobianPoint:
    if point is None:
        return None
    x, y, z = point
    if y == 0:
        return None
    a = (y * y) % P
    b = (4 * x * a) % P
    c = (8 * a * a) % P
    d = (3 * x * x) % P  # secp256k1 has a = 0, so no a*Z^4 term
    x3 = (d * d - 2 * b) % P
    y3 = (d * (b - x3) - c) % P
    z3 = (2 * y * z) % P
    return (x3, y3, z3)


def _jacobian_add(p1: _JacobianPoint, p2: _JacobianPoint) -> _JacobianPoint:
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1, z1 = p1
    x2, y2, z2 = p2

    z1_sq = (z1 * z1) % P
    z2_sq = (z2 * z2) % P
    u1 = (x1 * z2_sq) % P
    u2 = (x2 * z1_sq) % P
    s1 = (y1 * z2_sq * z2) % P
    s2 = (y2 * z1_sq * z1) % P

    if u1 == u2:
        if s1 != s2:
            return None  # p1 == -p2, so the sum is the point at infinity
        return _jacobian_double(p1)

    h = (u2 - u1) % P
    r = (s2 - s1) % P
    h_sq = (h * h) % P
    h_cu = (h_sq * h) % P
    u1_h_sq = (u1 * h_sq) % P

    x3 = (r * r - h_cu - 2 * u1_h_sq) % P
    y3 = (r * (u1_h_sq - x3) - s1 * h_cu) % P
    z3 = (h * z1 * z2) % P
    return (x3, y3, z3)


def _to_affine(point: _JacobianPoint) -> Point:
    if point is None:
        return None
    x, y, z = point
    if z == 0:
        return None
    z_inv = pow(z, P - 2, P)
    z_inv_sq = (z_inv * z_inv) % P
    return ((x * z_inv_sq) % P, (y * z_inv_sq * z_inv) % P)


def point_mul(point: Point, scalar: int) -> Point:
    """Multiply ``point`` by ``scalar``.

    Double-and-add over Jacobian coordinates, converted back to affine once at
    the end. Verified against the BIP-340 vectors in ``tests/``.
    """
    if point is None or scalar % N == 0:
        return None

    accumulator: _JacobianPoint = None
    addend: _JacobianPoint = (point[0], point[1], 1)
    while scalar:
        if scalar & 1:
            accumulator = _jacobian_add(accumulator, addend)
        addend = _jacobian_double(addend)
        scalar >>= 1
    return _to_affine(accumulator)


def bytes_from_int(value: int) -> bytes:
    return value.to_bytes(32, byteorder="big")


def bytes_from_point(point: Point) -> bytes:
    """Serialize a point as its 32-byte x-only representation."""
    return bytes_from_int(_x(point))


def lift_x(x: int) -> Point:
    """Recover the even-y point with the given x coordinate, or ``None``."""
    if x >= P:
        return None
    y_sq = (pow(x, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None
    return (x, y if y & 1 == 0 else P - y)


def has_even_y(point: Point) -> bool:
    assert point is not None
    return _y(point) % 2 == 0


def tagged_hash(tag: str, msg: bytes) -> bytes:
    """BIP-340 tagged hash: ``sha256(sha256(tag) || sha256(tag) || msg)``."""
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + msg).digest()


def pubkey_from_privkey(privkey: bytes) -> bytes:
    """Derive the 32-byte x-only public key for a 32-byte private key."""
    d0 = int.from_bytes(privkey, "big")
    if not 1 <= d0 <= N - 1:
        raise SchnorrError("private key must be in [1, n-1]")
    point = point_mul(G, d0)
    assert point is not None
    return bytes_from_point(point)


def schnorr_sign(msg: bytes, privkey: bytes, aux_rand: bytes = b"\x00" * 32) -> bytes:
    """Produce a 64-byte BIP-340 signature over ``msg``.

    ``aux_rand`` defaults to zeros, which yields deterministic signatures.
    That is permitted by BIP-340 and makes mirrored events reproducible in
    tests; pass ``os.urandom(32)`` when signing in production.
    """
    if len(privkey) != 32:
        raise SchnorrError("private key must be 32 bytes")
    if len(aux_rand) != 32:
        raise SchnorrError("aux_rand must be 32 bytes")

    d0 = int.from_bytes(privkey, "big")
    if not 1 <= d0 <= N - 1:
        raise SchnorrError("private key must be in [1, n-1]")

    point = point_mul(G, d0)
    assert point is not None
    d = d0 if has_even_y(point) else N - d0

    t = d ^ int.from_bytes(tagged_hash("BIP0340/aux", aux_rand), "big")
    rand = tagged_hash("BIP0340/nonce", bytes_from_int(t) + bytes_from_point(point) + msg)
    k0 = int.from_bytes(rand, "big") % N
    if k0 == 0:
        raise SchnorrError("derived nonce is zero (astronomically unlikely)")

    r_point = point_mul(G, k0)
    assert r_point is not None
    k = k0 if has_even_y(r_point) else N - k0

    e = (
        int.from_bytes(
            tagged_hash(
                "BIP0340/challenge",
                bytes_from_point(r_point) + bytes_from_point(point) + msg,
            ),
            "big",
        )
        % N
    )

    sig = bytes_from_point(r_point) + bytes_from_int((k + e * d) % N)
    if not schnorr_verify(msg, bytes_from_point(point), sig):
        raise SchnorrError("produced an invalid signature")
    return sig


def schnorr_verify(msg: bytes, pubkey: bytes, sig: bytes) -> bool:
    """Verify a 64-byte BIP-340 signature against a 32-byte x-only pubkey."""
    if len(pubkey) != 32 or len(sig) != 64:
        return False

    point = lift_x(int.from_bytes(pubkey, "big"))
    if point is None:
        return False

    r = int.from_bytes(sig[0:32], "big")
    s = int.from_bytes(sig[32:64], "big")
    if r >= P or s >= N:
        return False

    e = int.from_bytes(tagged_hash("BIP0340/challenge", sig[0:32] + pubkey + msg), "big") % N
    result = point_add(point_mul(G, s), point_mul(point, N - e))
    if result is None or not has_even_y(result) or _x(result) != r:
        return False
    return True
