"""
crypto.py — Project-level encryption for Transcribbler.

File format (per-file):
  Bytes 0-3:   b"TENC"  (magic)
  Bytes 4-15:  nonce (12 bytes)
  Bytes 16+:   ciphertext + 16-byte GCM auth tag

Key derivation: Argon2id  (same parameters as scribbler.py)
  memory_cost = 262144  (256 MB)
  time_cost   = 3
  parallelism = 4
  hash_len    = 32      (256-bit key)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

MAGIC = b"TENC"
NONCE_LEN = 12
TAG_LEN = 16
HEADER_LEN = len(MAGIC) + NONCE_LEN  # 16

ARGON2_M_COST = 262144
ARGON2_T_COST = 3
ARGON2_PARALLELISM = 4
KEY_LEN = 32

VERIFY_PLAINTEXT = b"TRANSCRIBBLER_VERIFY"


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from *password* + *salt* using Argon2id."""
    from argon2.low_level import hash_secret_raw, Type

    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_T_COST,
        memory_cost=ARGON2_M_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,
    )


# ---------------------------------------------------------------------------
# Low-level AES-256-GCM
# ---------------------------------------------------------------------------

def encrypt_blob(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt *plaintext* with AES-256-GCM. Returns nonce(12) + ciphertext + tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct


def decrypt_blob(blob: bytes, key: bytes) -> bytes:
    """Decrypt a blob produced by encrypt_blob. Raises ValueError on failure."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if len(blob) < NONCE_LEN + TAG_LEN:
        raise ValueError("Encrypted blob is too short.")
    nonce = blob[:NONCE_LEN]
    ct = blob[NONCE_LEN:]
    try:
        return AESGCM(key).decrypt(nonce, ct, None)
    except Exception:
        raise ValueError("Decryption failed — wrong key or corrupt data.")


# ---------------------------------------------------------------------------
# Verification token (password check without decrypting the full payload)
# ---------------------------------------------------------------------------

def make_verify_token(key: bytes) -> bytes:
    """Encrypt VERIFY_PLAINTEXT. Returns nonce + ciphertext + tag."""
    return encrypt_blob(VERIFY_PLAINTEXT, key)


def check_verify_token(token: bytes, key: bytes) -> bool:
    """Return True if *token* decrypts to VERIFY_PLAINTEXT with *key*."""
    try:
        return decrypt_blob(token, key) == VERIFY_PLAINTEXT
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# File-level helpers (TENC format)
# ---------------------------------------------------------------------------

def encrypt_file(path: Path, data: bytes, key: bytes):
    """Write *data* encrypted to *path* in TENC format."""
    blob = encrypt_blob(data, key)
    path.write_bytes(MAGIC + blob)


def decrypt_file(path: Path, key: bytes) -> bytes:
    """Read and decrypt a TENC file. Raises ValueError on failure."""
    raw = path.read_bytes()
    if len(raw) < HEADER_LEN + TAG_LEN:
        raise ValueError(f"File too short to be encrypted: {path}")
    if raw[:len(MAGIC)] != MAGIC:
        raise ValueError(f"Not a TENC file: {path}")
    return decrypt_blob(raw[len(MAGIC):], key)


def is_encrypted_file(path: Path) -> bool:
    """Check whether *path* starts with the TENC magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except (OSError, IOError):
        return False


# ---------------------------------------------------------------------------
# Convenience: text and JSON files
# ---------------------------------------------------------------------------

def encrypt_text_file(path: Path, text: str, key: bytes):
    encrypt_file(path, text.encode("utf-8"), key)


def decrypt_text_file(path: Path, key: bytes) -> str:
    return decrypt_file(path, key).decode("utf-8")


def encrypt_json_file(path: Path, data, key: bytes):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    encrypt_file(path, raw, key)


def decrypt_json_file(path: Path, key: bytes):
    raw = decrypt_file(path, key)
    return json.loads(raw)
