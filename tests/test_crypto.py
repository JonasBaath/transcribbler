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


def test_crlf_transcript_offsets_match_in_encrypted_project(tmp_path):
    # The browser drops \r when rendering, so annotation offsets count \n only;
    # the server must see the same text, encrypted or not
    from core.project import add_transcript, get_transcript_text, create_project
    from core.export import export_markdown_transcripts
    src = tmp_path / "win.txt"
    src.write_bytes("Rad ett.\r\nRad två med ord.\r\nRad tre.".encode("utf-8"))
    for password in (None, "testlosenord1"):
        folder = tmp_path / ("enc" if password else "plain")
        folder.mkdir()
        proj, key = create_project(str(folder), "P", "anna", password=password)
        proj["codes"] = [{"id": "c", "name": "Ord", "parent": None}]
        proj = add_transcript(str(folder), proj, str(src), "Win", key=key)
        t = proj["transcripts"][0]
        text = get_transcript_text(str(folder), t, key=key)
        assert "\r" not in text
        s = text.index("med ord")
        save_annotations(str(folder), t["id"], "anna",
                         [{"id": "a1", "code_id": "c", "start": s, "end": s + 7, "text": "med ord"}], key=key)
        assert "*med ord*" in export_markdown_transcripts(str(folder), proj, key=key)


def test_existing_encrypted_crlf_text_is_read_normalised(tmp_path):
    # Projects imported before the fix store \r\n inside the encrypted file
    from core.crypto import encrypt_text_file
    p = tmp_path / "t.txt"
    encrypt_text_file(p, "Rad ett.\r\nRad två.\rRad tre.", KEY)
    assert read_project_text(p, KEY) == "Rad ett.\nRad två.\nRad tre."
