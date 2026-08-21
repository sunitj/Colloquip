"""Bech32 encoding (BIP-173) for NIP-19 ``npub`` / ``nsec`` identifiers.

Buzz identifies agents and humans by secp256k1 pubkey. Operators paste keys
around in bech32 form (``npub1...``, ``nsec1...``), so the adapter accepts and
emits both that and raw hex.
"""

from typing import List, Optional, Tuple

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


class Bech32Error(ValueError):
    """Raised when a bech32 string is malformed."""


def _polymod(values: List[int]) -> int:
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _hrp_expand(hrp: str) -> List[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _verify_checksum(hrp: str, data: List[int]) -> bool:
    return _polymod(_hrp_expand(hrp) + data) == 1


def _create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = _hrp_expand(hrp) + data
    polymod = _polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _convertbits(data: bytes, frombits: int, tobits: int, pad: bool = True) -> Optional[List[int]]:
    acc = 0
    bits = 0
    ret: List[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32_encode(hrp: str, data: bytes) -> str:
    """Encode raw bytes as a bech32 string with the given human-readable part."""
    converted = _convertbits(data, 8, 5)
    if converted is None:
        raise Bech32Error("could not convert payload to 5-bit groups")
    combined = converted + _create_checksum(hrp, converted)
    return hrp + "1" + "".join(CHARSET[d] for d in combined)


def bech32_decode(value: str) -> Tuple[str, bytes]:
    """Decode a bech32 string, returning ``(hrp, payload_bytes)``."""
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise Bech32Error("bech32 string contains out-of-range characters")
    if value.lower() != value and value.upper() != value:
        raise Bech32Error("bech32 string has mixed case")
    value = value.lower()
    pos = value.rfind("1")
    if pos < 1 or pos + 7 > len(value):
        raise Bech32Error("bech32 string has no valid separator")
    hrp = value[:pos]
    try:
        data = [CHARSET.index(c) for c in value[pos + 1 :]]
    except ValueError as exc:  # noqa: F841
        raise Bech32Error("bech32 string contains invalid characters") from None
    if not _verify_checksum(hrp, data):
        raise Bech32Error("bech32 checksum mismatch")
    converted = _convertbits(bytes(data[:-6]), 5, 8, pad=False)
    if converted is None:
        raise Bech32Error("could not convert payload to 8-bit groups")
    return hrp, bytes(converted)


def to_npub(pubkey_hex: str) -> str:
    """Encode a 32-byte hex pubkey as a NIP-19 ``npub``."""
    return bech32_encode("npub", bytes.fromhex(pubkey_hex))


def to_nsec(privkey_hex: str) -> str:
    """Encode a 32-byte hex private key as a NIP-19 ``nsec``."""
    return bech32_encode("nsec", bytes.fromhex(privkey_hex))


def from_npub(npub: str) -> str:
    """Decode a NIP-19 ``npub`` to a 32-byte hex pubkey."""
    hrp, data = bech32_decode(npub)
    if hrp != "npub":
        raise Bech32Error(f"expected an npub, got '{hrp}'")
    if len(data) != 32:
        raise Bech32Error(f"npub payload must be 32 bytes, got {len(data)}")
    return data.hex()


def from_nsec(nsec: str) -> str:
    """Decode a NIP-19 ``nsec`` to a 32-byte hex private key."""
    hrp, data = bech32_decode(nsec)
    if hrp != "nsec":
        raise Bech32Error(f"expected an nsec, got '{hrp}'")
    if len(data) != 32:
        raise Bech32Error(f"nsec payload must be 32 bytes, got {len(data)}")
    return data.hex()
