"""Reading and writing project files with and without the project key."""
import os

from core.crypto import (is_encrypted_file, read_project_json, read_project_text,
                         write_project_json, write_project_text)
from core.annotation import load_annotations, save_annotations

KEY = os.urandom(32)


def test_text_roundtrip_encrypted(tmp_path):
    p = tmp_path / "t.txt"
    write_project_text(p, "Åsa sa: hej\nrad två", KEY)
    assert is_encrypted_file(p)
    assert "Åsa".encode() not in p.read_bytes()
    assert read_project_text(p, KEY) == "Åsa sa: hej\nrad två"


def test_json_roundtrip_plain(tmp_path):
    p = tmp_path / "a.json"
    write_project_json(p, {"x": "ö"}, None)
    assert not is_encrypted_file(p)
    assert read_project_json(p, None) == {"x": "ö"}


def test_plain_file_readable_with_key(tmp_path):
    # Files written before encryption was switched on stay plain
    p = tmp_path / "old.json"
    write_project_json(p, [1, 2], None)
    assert read_project_json(p, KEY) == [1, 2]


def test_annotations_roundtrip_encrypted(tmp_path):
    (tmp_path / "annotations").mkdir()
    anns = [{"id": "a1", "code_id": "c1", "start": 0, "end": 3, "text": "Hej"}]
    save_annotations(str(tmp_path), "t1", "anna", anns, key=KEY)
    assert load_annotations(str(tmp_path), "t1", "anna", key=KEY) == anns
