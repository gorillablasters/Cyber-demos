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


def forge_secure_crosslink(
    known_plain: bytes,
    known_cipher: bytes,
    desired_plain: bytes,
) -> bytes:
    """
    Forge a ciphertext without the key using a known (plain,cipher) pair:
      keystream = known_plain XOR known_cipher
      forged    = desired_plain XOR keystream
    Requires desired_plain length <= known_plain length.
    """
    ks = xor_bytes(known_plain, known_cipher)
    if len(desired_plain) > len(ks):
        raise ValueError("desired plaintext longer than available keystream")
    return xor_bytes(desired_plain, ks[: len(desired_plain)])
