"""Tests for core/scribbler.py — .scribbler decrypt."""
import os
import pytest
from core.scribbler import decrypt_scribbler, MAGIC, SALT_OFFSET, SALT_LEN, NONCE_OFFSET, NONCE_LEN, DATA_OFFSET


PASSWORD = "korrekt-lösenord"
WRONG_PW = "fel-lösenord"
PLAINTEXT = "# Anteckning\n\nÅäö fungerar i krypterad fil."


def _make_scribbler(tmp_path, password: str, content: str) -> str:
    """Create a valid .scribbler file and return its path."""
    from argon2.low_level import hash_secret_raw, Type
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=262144,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )
    ciphertext = AESGCM(key).encrypt(nonce, content.encode("utf-8"), None)
    raw = MAGIC + salt + nonce + ciphertext
    path = str(tmp_path / "test.scribbler")
    with open(path, "wb") as f:
        f.write(raw)
    return path


# ---------------------------------------------------------------------------
# Header validation
# ---------------------------------------------------------------------------

def test_magic_header(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == MAGIC
    assert len(data) > DATA_OFFSET + 16


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------

def test_decrypt_roundtrip(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    result = decrypt_scribbler(path, PASSWORD)
    assert result.decode("utf-8") == PLAINTEXT


def test_decrypt_unicode(tmp_path):
    content = "Hej Åsa! Ö funkar. 日本語も。"
    path = _make_scribbler(tmp_path, PASSWORD, content)
    result = decrypt_scribbler(path, PASSWORD)
    assert result.decode("utf-8") == content


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------

def test_wrong_password_raises(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    with pytest.raises(ValueError, match="Fel lösenord"):
        decrypt_scribbler(path, WRONG_PW)


def test_empty_password_raises(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    with pytest.raises(ValueError):
        decrypt_scribbler(path, "")


# ---------------------------------------------------------------------------
# Corrupt / too-short files
# ---------------------------------------------------------------------------

def test_too_short_file(tmp_path):
    f = tmp_path / "short.scribbler"
    f.write_bytes(b"SCRIB001" + b"\x00" * 10)
    with pytest.raises(ValueError, match="för kort"):
        decrypt_scribbler(str(f), PASSWORD)


def test_bad_magic(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    with open(path, "rb") as f:
        data = f.read()
    bad = b"BADMAGIC" + data[8:]
    bad_path = str(tmp_path / "bad.scribbler")
    with open(bad_path, "wb") as f:
        f.write(bad)
    with pytest.raises(ValueError, match="signatur"):
        decrypt_scribbler(bad_path, PASSWORD)


def test_flipped_bit_raises(tmp_path):
    path = _make_scribbler(tmp_path, PASSWORD, PLAINTEXT)
    with open(path, "rb") as f:
        data = bytearray(f.read())
    data[-1] ^= 0xFF  # flip last byte (GCM auth tag)
    bad_path = str(tmp_path / "flipped.scribbler")
    with open(bad_path, "wb") as f:
        f.write(data)
    with pytest.raises(ValueError):
        decrypt_scribbler(bad_path, PASSWORD)
