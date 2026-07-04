"""Tests for app.core.crypto.

Round-trip, tamper detection, key wrap/unwrap, nonce uniqueness.
"""

from __future__ import annotations

import pytest
import nacl.utils
import nacl.secret

from app.core.crypto import (
    b64d,
    b64e,
    decrypt_message,
    encrypt_message,
    generate_conversation_key,
    generate_master_key,
    unwrap_conversation_key,
    wrap_conversation_key,
)


def test_master_key_is_32_bytes() -> None:
    assert len(generate_master_key()) == 32


def test_conversation_key_is_32_bytes() -> None:
    assert len(generate_conversation_key()) == 32


def test_message_round_trip() -> None:
    key = generate_conversation_key()
    plaintext = b"hello, world"
    ct = encrypt_message(key, plaintext)
    assert ct != plaintext
    assert decrypt_message(key, ct) == plaintext


def test_tamper_detection() -> None:
    key = generate_conversation_key()
    ct = encrypt_message(key, b"hello")
    # Flip a byte in the middle of the ciphertext
    tampered = bytearray(ct)
    tampered[len(tampered) // 2] ^= 0x01
    with pytest.raises(nacl.exceptions.CryptoError):
        decrypt_message(key, bytes(tampered))


def test_wrong_key_rejected() -> None:
    k1 = generate_conversation_key()
    k2 = generate_conversation_key()
    ct = encrypt_message(k1, b"secret")
    with pytest.raises(nacl.exceptions.CryptoError):
        decrypt_message(k2, ct)


def test_wrap_unwrap_round_trip() -> None:
    master = generate_master_key()
    conv = generate_conversation_key()
    wrapped = wrap_conversation_key(master, conv)
    assert wrapped != conv
    assert unwrap_conversation_key(master, wrapped) == conv


def test_wrap_tamper_detection() -> None:
    master = generate_master_key()
    conv = generate_conversation_key()
    wrapped = wrap_conversation_key(master, conv)
    tampered = bytearray(wrapped)
    tampered[0] ^= 0xFF
    with pytest.raises(nacl.exceptions.CryptoError):
        unwrap_conversation_key(master, bytes(tampered))


def test_wrap_wrong_master_rejected() -> None:
    master1 = generate_master_key()
    master2 = generate_master_key()
    conv = generate_conversation_key()
    wrapped = wrap_conversation_key(master1, conv)
    with pytest.raises(nacl.exceptions.CryptoError):
        unwrap_conversation_key(master2, wrapped)


def test_nonce_uniqueness() -> None:
    """Sample 10,000 messages and assert all nonces are unique. NaCl random
    nonces should never collide in any practical sense."""
    key = generate_conversation_key()
    seen: set[bytes] = set()
    for _ in range(10_000):
        ct = encrypt_message(key, b"x")
        nonce = ct[:24]  # first 24 bytes are the nonce
        assert nonce not in seen
        seen.add(nonce)
    assert len(seen) == 10_000


def test_b64_round_trip() -> None:
    raw = b"hello\x00\x01\x02"
    s = b64e(raw)
    assert b64d(s) == raw


def test_b64d_tolerates_missing_padding() -> None:
    raw = b"hello"
    s = b64e(raw)
    # strip padding
    assert b64d(s.rstrip("=")) == raw


def test_wrap_rejects_wrong_key_size() -> None:
    with pytest.raises(ValueError):
        wrap_conversation_key(b"too short", b"\x00" * 32)
    with pytest.raises(ValueError):
        wrap_conversation_key(b"\x00" * 32, b"short")
