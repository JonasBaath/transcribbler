"""
nsenc.py — Encrypt/decrypt .nsenc bundle files for Notescribbler ↔ Transcribbler.

Binary header (unchanged for all versions):
  Bytes 0–3:   b"NSE1"  (magic)
  Byte  4:     0x01     (binary format version, fixed)
  Bytes 5–20:  salt (16 bytes, Argon2id)
  Bytes 21+:   AES-256-GCM encrypted blob
                 nonce (12 bytes) | ciphertext | auth tag (16 bytes)

Key derivation: Argon2id(memory=65536 KiB, time=3, parallelism=4, hash_len=32)

JSON payload versions (inside the encrypted blob):
  v1: {"version": 1, "notes": [{"filename": "slug.md", "content": "..."}, ...]}
  v2: {"version": 2,
       "notes": [{"filename": "slug.md", "content": "..."}, ...],
       "photos": [{"filename": "photo.jpg", "data": "<base64>"}, ...]}
"""
from __future__ import annotations

import base64

MAGIC = b"NSE1"
BINARY_VERSION = 0x01
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
HEADER_LEN = 4 + 1 + SALT_LEN   # magic(4) + version(1) + salt(16) = 21

ARGON2_M = 65536
ARGON2_T = 3
ARGON2_P = 4
KEY_LEN = 32


def _derive_key(password: str, salt: bytes) -> bytes:
    try:
        from argon2.low_level import hash_secret_raw, Type
    except ImportError:
        raise ImportError("argon2-cffi är inte installerat. Kör: pip install argon2-cffi")
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=bytes(salt),
        time_cost=ARGON2_T,
        memory_cost=ARGON2_M,
        parallelism=ARGON2_P,
        hash_len=KEY_LEN,
        type=Type.ID,
    )


def decrypt_nsenc(path: str, password: str) -> tuple[list[dict], list[dict]]:
    """
    Decrypt a .nsenc file.

    Returns (notes, photos) where:
      notes  = [{"filename": str, "content": str}, ...]
      photos = [{"filename": str, "data": bytes}, ...]  (empty for v1 files)

    Raises ValueError for wrong password, corrupt file, or invalid format.
    Raises ImportError if required packages are missing.
    """
    import json

    with open(path, "rb") as f:
        data = f.read()

    if len(data) < HEADER_LEN + NONCE_LEN + TAG_LEN:
        raise ValueError("Filen är för kort — troligen inte en giltig .nsenc-fil.")

    if data[:4] != MAGIC:
        raise ValueError("Ogiltig .nsenc-fil (felaktig signatur).")

    if data[4] != BINARY_VERSION:
        raise ValueError(f"Okänd binär version: {data[4]}.")

    salt = data[5 : 5 + SALT_LEN]
    blob = data[HEADER_LEN:]
    nonce = blob[:NONCE_LEN]
    ciphertext_with_tag = blob[NONCE_LEN:]

    key = _derive_key(password, salt)

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError("cryptography är inte installerat. Kör: pip install cryptography")

    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext_with_tag, None)
    except Exception:
        raise ValueError("Fel lösenord eller skadad fil.")

    payload = json.loads(plaintext.decode("utf-8"))
    notes = payload.get("notes", [])

    # v2: photos as base64-encoded strings → decode to bytes
    photos_raw = payload.get("photos", [])
    photos = []
    for p in photos_raw:
        try:
            photos.append({
                "filename": p["filename"],
                "data": base64.b64decode(p["data"]),
            })
        except Exception:
            pass  # skip malformed entries

    return notes, photos


def encrypt_nsenc(notes: list[dict], password: str, photos: list[dict] | None = None) -> bytes:
    """
    Encrypt notes (and optionally photos) into a .nsenc bundle.

    notes  = [{"filename": str, "content": str}, ...]
    photos = [{"filename": str, "data": bytes}, ...]  (optional; produces v2 payload)

    Returns raw bytes ready to write to a .nsenc file.
    """
    import json
    import os

    payload_dict: dict = {"notes": notes}
    if photos:
        payload_dict["photos"] = [
            {"filename": p["filename"], "data": base64.b64encode(p["data"]).decode("ascii")}
            for p in photos
        ]
        payload_dict["version"] = 2
    else:
        payload_dict["version"] = 1

    plaintext = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(password, salt)

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ImportError("cryptography är inte installerat. Kör: pip install cryptography")

    ciphertext_with_tag = AESGCM(key).encrypt(nonce, plaintext, None)

    return MAGIC + bytes([BINARY_VERSION]) + salt + nonce + ciphertext_with_tag


if __name__ == "__main__":
    import getpass
    import sys

    if len(sys.argv) < 2:
        print("Användning:")
        print("  python3 -m core.nsenc <fil.nsenc>          — dekryptera")
        print("  python3 -m core.nsenc --encrypt <ut.nsenc> — kryptera testfil")
        sys.exit(1)

    if sys.argv[1] == "--encrypt":
        out_path = sys.argv[2] if len(sys.argv) > 2 else "test_out.nsenc"
        pw = getpass.getpass("Lösenord för testfilen: ")
        test_notes = [{"filename": "test.md", "content": "# Test\n\nHej världen! Åäö fungerar."}]
        raw = encrypt_nsenc(test_notes, pw)
        with open(out_path, "wb") as fh:
            fh.write(raw)
        print(f"Testfil skriven: {out_path}  ({len(raw)} bytes)")
        # Immediately verify by decrypting
        notes2, _ = decrypt_nsenc(out_path, pw)
        print(f"Verifiering OK — {len(notes2)} anteckning(ar) dekrypterades.")
    else:
        path = sys.argv[1]
        pw = getpass.getpass("Lösenord: ")
        try:
            notes, photos = decrypt_nsenc(path, pw)
            print(f"OK — {len(notes)} anteckning(ar), {len(photos)} foto(n) dekrypterades:")
            for n in notes:
                print(f"  {n['filename']}  ({len(n.get('content', ''))} tecken)")
            for p in photos:
                print(f"  [foto] {p['filename']}  ({len(p['data'])} bytes)")
        except ValueError as e:
            print(f"Fel: {e}")
            sys.exit(1)
