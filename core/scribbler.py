"""
scribbler.py — Decrypt .scribbler files from Notescribbler.

File format:
  Bytes 0-7:   b"SCRIB001"  (magic + version)
  Bytes 8-23:  salt (16 bytes)
  Bytes 24-35: nonce (12 bytes)
  Bytes 36+:   ciphertext + 16-byte GCM auth tag (appended by AES-GCM)

Key derivation: Argon2id
  memory_cost = 262144  (256 MB in KB)
  time_cost   = 3
  parallelism = 4
  hash_len    = 32      (256-bit key)
"""
from __future__ import annotations

MAGIC = b"SCRIB001"
SALT_OFFSET = 8
SALT_LEN = 16
NONCE_OFFSET = SALT_OFFSET + SALT_LEN   # 24
NONCE_LEN = 12
DATA_OFFSET = NONCE_OFFSET + NONCE_LEN  # 36
MIN_FILE_LEN = DATA_OFFSET + 16         # ciphertext must include at least the auth tag

ARGON2_M_COST = 262144   # 256 MB
ARGON2_T_COST = 3
ARGON2_PARALLELISM = 4
KEY_LEN = 32


def decrypt_scribbler(path: str, password: str) -> bytes:
    """
    Decrypt a .scribbler file and return plaintext bytes (UTF-8 .md content).
    Raises ValueError for wrong password, corrupt file, or invalid format.
    Raises ImportError if required packages are missing.
    """
    with open(path, "rb") as f:
        data = f.read()

    if len(data) < MIN_FILE_LEN:
        raise ValueError("Filen är för kort — troligen inte en giltig .scribbler-fil.")

    if data[:8] != MAGIC:
        raise ValueError("Ogiltig .scribbler-fil (felaktig signatur).")

    salt = data[SALT_OFFSET : SALT_OFFSET + SALT_LEN]
    nonce = data[NONCE_OFFSET : NONCE_OFFSET + NONCE_LEN]
    ciphertext = data[DATA_OFFSET:]

    try:
        from argon2.low_level import hash_secret_raw, Type
    except ImportError:
        raise ImportError(
            "argon2-cffi är inte installerat. Kör: pip install argon2-cffi"
        )

    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_T_COST,
        memory_cost=ARGON2_M_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_LEN,
        type=Type.ID,
    )

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError(
            "cryptography är inte installerat. Kör: pip install cryptography"
        )

    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Fel lösenord eller skadad fil.")
