"""Envelope encryption with libsodium (PyNaCl).

Design:
  - MASTER_KEY: 32-byte secret from env. Never logged, never sent to clients.
    Used to WRAP every per-conversation key.
  - Per-conversation key: 32 bytes, generated at conversation creation,
    stored in `conversations.encrypted_key` as `secretbox(master, conv_key)`.
  - Per-message: `secretbox(conv_key, plaintext)` — output already includes
    a 24-byte random nonce + 16-byte Poly1305 tag, stored as BLOB.

The server unwraps the conversation key in memory, decrypts the message,
and ships plaintext JSON over HTTPS / WSS. The DB itself never stores
plaintext. A stolen DB without the master key yields ciphertext blobs that
cannot be opened.
"""

from __future__ import annotations

import base64
import os

import nacl.secret
import nacl.utils


def generate_master_key() -> bytes:
    """Generate a fresh 32-byte master key. Use once, then store in env."""
    return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)


def generate_conversation_key() -> bytes:
    """Generate a fresh 32-byte conversation key."""
    return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)


def wrap_conversation_key(master_key: bytes, conv_key: bytes) -> bytes:
    """Encrypt a per-conversation key under the master key.

    Output: 24-byte nonce || ciphertext+tag (24 + 32 + 16 = 72 bytes).
    """
    if len(master_key) != nacl.secret.SecretBox.KEY_SIZE:
        raise ValueError("master key must be 32 bytes")
    if len(conv_key) != nacl.secret.SecretBox.KEY_SIZE:
        raise ValueError("conversation key must be 32 bytes")
    box = nacl.secret.SecretBox(master_key)
    return box.encrypt(conv_key)


def unwrap_conversation_key(master_key: bytes, wrapped: bytes) -> bytes:
    """Decrypt a wrapped conversation key. Raises if the master key is wrong
    or the ciphertext was tampered with (libsodium's Poly1305 rejects it)."""
    if len(master_key) != nacl.secret.SecretBox.KEY_SIZE:
        raise ValueError("master key must be 32 bytes")
    box = nacl.secret.SecretBox(master_key)
    return box.decrypt(wrapped)


def encrypt_message(conv_key: bytes, plaintext: bytes) -> bytes:
    """Encrypt a message under a per-conversation key.

    Output: 24-byte nonce || ciphertext+tag. Store as BLOB.
    """
    if len(conv_key) != nacl.secret.SecretBox.KEY_SIZE:
        raise ValueError("conversation key must be 32 bytes")
    box = nacl.secret.SecretBox(conv_key)
    return box.encrypt(plaintext)


def decrypt_message(conv_key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt a message. Raises on tampering."""
    if len(conv_key) != nacl.secret.SecretBox.KEY_SIZE:
        raise ValueError("conversation key must be 32 bytes")
    box = nacl.secret.SecretBox(conv_key)
    return box.decrypt(ciphertext)


# --- helpers for HTTP / wire transport ---

def b64e(b: bytes) -> str:
    """Base64-encode for JSON transport."""
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def b64d(s: str) -> bytes:
    """Base64-decode the format produced by b64e. Tolerates missing padding."""
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def random_token() -> str:
    """Cryptographically random URL-safe token, used for refresh tokens."""
    return b64e(os.urandom(32))
