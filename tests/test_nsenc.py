"""Tests for core/nsenc.py — .nsenc encrypt/decrypt."""
import pytest
from core.nsenc import encrypt_nsenc, decrypt_nsenc, MAGIC, BINARY_VERSION, HEADER_LEN


NOTES_V1 = [{"filename": "note.md", "content": "# Hej\n\nÅäö fungerar."}]
PHOTOS = [{"filename": "bild.jpg", "data": b"\xff\xd8\xff" + b"\x00" * 20}]
PASSWORD = "korrekt-lösenord"
WRONG_PW = "fel-lösenord"


# ---------------------------------------------------------------------------
# v1 roundtrip
# ---------------------------------------------------------------------------

def test_v1_roundtrip(tmp_path):
    raw = encrypt_nsenc(NOTES_V1, PASSWORD)
    f = tmp_path / "bundle.nsenc"
    f.write_bytes(raw)
    notes, photos = decrypt_nsenc(str(f), PASSWORD)
    assert len(notes) == 1
    assert notes[0]["filename"] == "note.md"
    assert "Åäö" in notes[0]["content"]
    assert photos == []


def test_v1_header(tmp_path):
    raw = encrypt_nsenc(NOTES_V1, PASSWORD)
    assert raw[:4] == MAGIC
    assert raw[4] == BINARY_VERSION
    assert len(raw) > HEADER_LEN


# ---------------------------------------------------------------------------
# v2 roundtrip (with photos)
# ---------------------------------------------------------------------------

def test_v2_roundtrip(tmp_path):
    raw = encrypt_nsenc(NOTES_V1, PASSWORD, photos=PHOTOS)
    f = tmp_path / "bundle_v2.nsenc"
    f.write_bytes(raw)
    notes, photos = decrypt_nsenc(str(f), PASSWORD)
    assert len(notes) == 1
    assert len(photos) == 1
    assert photos[0]["filename"] == "bild.jpg"
    assert photos[0]["data"][:3] == b"\xff\xd8\xff"


def test_v2_multiple_notes(tmp_path):
    notes_in = [
        {"filename": "a.md", "content": "Alpha"},
        {"filename": "b.md", "content": "Beta"},
    ]
    raw = encrypt_nsenc(notes_in, PASSWORD, photos=PHOTOS)
    f = tmp_path / "multi.nsenc"
    f.write_bytes(raw)
    notes, _ = decrypt_nsenc(str(f), PASSWORD)
    assert len(notes) == 2
    assert {n["filename"] for n in notes} == {"a.md", "b.md"}


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------

def test_wrong_password_raises(tmp_path):
    raw = encrypt_nsenc(NOTES_V1, PASSWORD)
    f = tmp_path / "bundle.nsenc"
    f.write_bytes(raw)
    with pytest.raises(ValueError, match="Fel lösenord"):
        decrypt_nsenc(str(f), WRONG_PW)


# ---------------------------------------------------------------------------
# Corrupt / too-short files
# ---------------------------------------------------------------------------

def test_too_short_file(tmp_path):
    f = tmp_path / "short.nsenc"
    f.write_bytes(b"NSE1\x01" + b"\x00" * 5)
    with pytest.raises(ValueError):
        decrypt_nsenc(str(f), PASSWORD)


def test_bad_magic(tmp_path):
    raw = encrypt_nsenc(NOTES_V1, PASSWORD)
    bad = b"XXXX" + raw[4:]
    f = tmp_path / "bad.nsenc"
    f.write_bytes(bad)
    with pytest.raises(ValueError, match="signatur"):
        decrypt_nsenc(str(f), PASSWORD)


def test_each_encrypt_produces_unique_ciphertext():
    """Salt and nonce are random — two encryptions of same data differ."""
    raw1 = encrypt_nsenc(NOTES_V1, PASSWORD)
    raw2 = encrypt_nsenc(NOTES_V1, PASSWORD)
    assert raw1 != raw2
