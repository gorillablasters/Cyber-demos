from __future__ import annotations

from typing import ByteString
import hashlib


def xor_bytes(a: ByteString, b: ByteString) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def build_secure_crosslink(
    key: bytes,
    nonce: int,
    plain: bytes,
) -> bytes:
    """
    Build ciphertext matching the sim's secure crosslink scheme:
      keystream = sha256(key || nonce_le)
      cipher    = plain XOR keystream[:len(plain)]
    """
    nonce_bytes = nonce.to_bytes(2, "little")
    ks = hashlib.sha256(key + nonce_bytes).digest()
    return xor_bytes(plain, ks[: len(plain)])
