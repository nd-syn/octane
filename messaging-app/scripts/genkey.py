"""Generate JWT_SECRET and MASTER_KEY for .env.

Usage:
    python scripts/genkey.py

Prints two base64-encoded secrets, one per line, in the format ready to
paste into .env. Run once per environment. NEVER reuse a key across
environments.
"""

from __future__ import annotations

import secrets

import nacl.utils


def _b64(b: bytes) -> str:
    import base64
    return base64.b64encode(b).decode("ascii")


def main() -> None:
    jwt_secret = secrets.token_bytes(48)  # 48 bytes -> 64 base64 chars
    master_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)  # 32 bytes

    print("# Paste these into your .env file (or Render env vars):")
    print()
    print(f"JWT_SECRET={_b64(jwt_secret)}")
    print(f"MASTER_KEY={_b64(master_key)}")
    print()
    print("# IMPORTANT: never reuse these across environments.")
    print("# If you suspect compromise, generate new values and redeploy.")


if __name__ == "__main__":
    main()
