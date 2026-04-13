"""Tests for Flask routes — path traversal and basic route behaviour."""
import json
import uuid
import pytest


# ---------------------------------------------------------------------------
# Helper: add a transcript entry to the in-memory project
# ---------------------------------------------------------------------------

def _add_transcript(flask_client, tid=None, **fields):
    """Insert a transcript dict directly into STATE for route testing."""
    import main
    t = {"id": tid or str(uuid.uuid4()), "name": "Test", **fields}
    main.STATE["project"]["transcripts"].append(t)
    return t


# ---------------------------------------------------------------------------
# No project open
# ---------------------------------------------------------------------------

def test_no_project_returns_400(tmp_path):
    import main
    main.app.config["TESTING"] = True
    # Ensure STATE is empty
    main.STATE["folder"] = None
    main.STATE["project"] = None
    with main.app.test_client() as client:
        r = client.get("/api/transcripts/abc/audio")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# /api/transcripts/<tid>/audio — path traversal
# ---------------------------------------------------------------------------

class TestAudioTraversal:
    def test_valid_audio_file_not_found(self, flask_client, tmp_project):
        """audio_file inside transcripts/ that doesn't exist → 404."""
        tmp_path, _ = tmp_project
        t = _add_transcript(flask_client, audio_file="recording.mp3")
        r = flask_client.get(f"/api/transcripts/{t['id']}/audio")
        assert r.status_code == 404

    def test_valid_audio_served(self, flask_client, tmp_project):
        """audio_file inside transcripts/ that exists → 200."""
        tmp_path, _ = tmp_project
        (tmp_path / "transcripts" / "rec.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 100)
        t = _add_transcript(flask_client, audio_file="rec.mp3")
        r = flask_client.get(f"/api/transcripts/{t['id']}/audio")
        assert r.status_code == 200

    def test_traversal_rejected(self, flask_client, tmp_project):
        """audio_file with ../ traversal → 400."""
        t = _add_transcript(flask_client, audio_file="../../../etc/passwd")
        r = flask_client.get(f"/api/transcripts/{t['id']}/audio")
        assert r.status_code == 400

    def test_traversal_nested(self, flask_client):
        """Nested traversal attempt."""
        t = _add_transcript(flask_client, audio_file="subdir/../../secret.mp3")
        r = flask_client.get(f"/api/transcripts/{t['id']}/audio")
        assert r.status_code == 400

    def test_no_audio_file_field(self, flask_client):
        """Transcript without audio_file → 404."""
        t = _add_transcript(flask_client)
        r = flask_client.get(f"/api/transcripts/{t['id']}/audio")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# /api/transcripts/<tid>/source-image — path traversal
# ---------------------------------------------------------------------------

class TestSourceImageTraversal:
    def test_traversal_rejected(self, flask_client):
        t = _add_transcript(flask_client, source_file="../../../etc/passwd")
        r = flask_client.get(f"/api/transcripts/{t['id']}/source-image")
        assert r.status_code == 400

    def test_valid_missing_file(self, flask_client):
        t = _add_transcript(flask_client, source_file="image.png")
        r = flask_client.get(f"/api/transcripts/{t['id']}/source-image")
        assert r.status_code == 404

    def test_valid_image_served(self, flask_client, tmp_project):
        tmp_path, _ = tmp_project
        img = tmp_path / "transcripts" / "img.png"
        # Minimal 1×1 PNG
        img.write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
            b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        t = _add_transcript(flask_client, source_file="img.png")
        r = flask_client.get(f"/api/transcripts/{t['id']}/source-image")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# /api/transcripts/<tid>/photo/<n> — path traversal
# ---------------------------------------------------------------------------

class TestPhotoTraversal:
    def test_traversal_rejected(self, flask_client):
        t = _add_transcript(flask_client, photos=["../../../etc/passwd"])
        r = flask_client.get(f"/api/transcripts/{t['id']}/photo/0")
        assert r.status_code == 400

    def test_out_of_bounds(self, flask_client):
        t = _add_transcript(flask_client, photos=["photo.jpg"])
        r = flask_client.get(f"/api/transcripts/{t['id']}/photo/5")
        assert r.status_code == 404

    def test_valid_missing_photo(self, flask_client):
        t = _add_transcript(flask_client, photos=["photo.jpg"])
        r = flask_client.get(f"/api/transcripts/{t['id']}/photo/0")
        assert r.status_code == 404

    def test_valid_photo_served(self, flask_client, tmp_project):
        tmp_path, _ = tmp_project
        (tmp_path / "transcripts" / "p.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
        t = _add_transcript(flask_client, photos=["p.jpg"])
        r = flask_client.get(f"/api/transcripts/{t['id']}/photo/0")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# /api/transcripts/<tid>/text PATCH — path traversal
# ---------------------------------------------------------------------------

class TestTextPatchTraversal:
    def test_traversal_rejected(self, flask_client):
        t = _add_transcript(flask_client, text_file="../../../tmp/evil.txt")
        r = flask_client.patch(
            f"/api/transcripts/{t['id']}/text",
            json={"text": "pwned"},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_valid_text_written(self, flask_client, tmp_project):
        tmp_path, _ = tmp_project
        txt = tmp_path / "transcripts" / "t.txt"
        txt.write_text("original", encoding="utf-8")
        t = _add_transcript(flask_client, text_file="t.txt")
        r = flask_client.patch(
            f"/api/transcripts/{t['id']}/text",
            json={"text": "uppdaterad"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert txt.read_text(encoding="utf-8") == "uppdaterad"


# ---------------------------------------------------------------------------
# /api/merge — path traversal (already fixed, regression test)
# ---------------------------------------------------------------------------

class TestMergeTraversal:
    def test_nonexistent_file_rejected(self, flask_client):
        r = flask_client.post(
            "/api/merge",
            json={"path": "/nonexistent/path/file.json"},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_non_json_suffix_rejected(self, flask_client, tmp_project):
        tmp_path, _ = tmp_project
        evil = tmp_path / "evil.txt"
        evil.write_text("{}", encoding="utf-8")
        r = flask_client.post(
            "/api/merge",
            json={"path": str(evil)},
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_empty_path_rejected(self, flask_client):
        r = flask_client.post(
            "/api/merge",
            json={"path": ""},
            content_type="application/json",
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# /api/transcripts/<tid>/segments — tid cannot contain slashes (Flask routing)
# ---------------------------------------------------------------------------

def test_segments_unknown_tid_returns_empty(flask_client):
    """Unknown tid with no segments file → empty list."""
    r = flask_client.get("/api/transcripts/unknowntid/segments")
    assert r.status_code == 200
    assert r.get_json()["segments"] == []


def test_ocr_boxes_unknown_tid_returns_empty(flask_client):
    """Unknown tid with no ocr-boxes file → empty list."""
    r = flask_client.get("/api/transcripts/unknowntid/ocr-boxes")
    assert r.status_code == 200
    assert r.get_json()["boxes"] == []
