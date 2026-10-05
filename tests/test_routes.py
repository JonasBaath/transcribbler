"""Tests for Flask routes — path traversal and basic route behaviour."""
import uuid


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


# ---------------------------------------------------------------------------
# /api/transcripts/tag PATCH — tag-baserat urval för analysen
# ---------------------------------------------------------------------------

class TestTagTranscripts:
    def test_add_tag_to_one(self, flask_client):
        t = _add_transcript(flask_client, tags=[])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t["id"]], "add": ["pilot"]},
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        updated = next(tr for tr in data["project"]["transcripts"] if tr["id"] == t["id"])
        assert "pilot" in updated["tags"]

    def test_add_multiple_tags_and_deduplicate(self, flask_client):
        t = _add_transcript(flask_client, tags=["pilot"])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t["id"]], "add": ["pilot", "lärare", "fas2"]},
            content_type="application/json",
        )
        assert r.status_code == 200
        updated = next(tr for tr in r.get_json()["project"]["transcripts"] if tr["id"] == t["id"])
        assert sorted(updated["tags"]) == ["fas2", "lärare", "pilot"]

    def test_remove_tag(self, flask_client):
        t = _add_transcript(flask_client, tags=["pilot", "lärare"])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t["id"]], "remove": ["pilot"]},
            content_type="application/json",
        )
        assert r.status_code == 200
        updated = next(tr for tr in r.get_json()["project"]["transcripts"] if tr["id"] == t["id"])
        assert updated["tags"] == ["lärare"]

    def test_set_replaces_all(self, flask_client):
        t = _add_transcript(flask_client, tags=["gammal1", "gammal2"])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t["id"]], "set": ["ny"]},
            content_type="application/json",
        )
        assert r.status_code == 200
        updated = next(tr for tr in r.get_json()["project"]["transcripts"] if tr["id"] == t["id"])
        assert updated["tags"] == ["ny"]

    def test_strips_whitespace(self, flask_client):
        t = _add_transcript(flask_client, tags=[])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t["id"]], "add": ["  med-mellanslag  ", "   "]},
            content_type="application/json",
        )
        assert r.status_code == 200
        updated = next(tr for tr in r.get_json()["project"]["transcripts"] if tr["id"] == t["id"])
        assert updated["tags"] == ["med-mellanslag"]

    def test_only_affects_listed_tids(self, flask_client):
        t1 = _add_transcript(flask_client, tags=[])
        t2 = _add_transcript(flask_client, tags=[])
        r = flask_client.patch(
            "/api/transcripts/tag",
            json={"tids": [t1["id"]], "add": ["pilot"]},
            content_type="application/json",
        )
        assert r.status_code == 200
        transcripts = r.get_json()["project"]["transcripts"]
        first = next(tr for tr in transcripts if tr["id"] == t1["id"])
        second = next(tr for tr in transcripts if tr["id"] == t2["id"])
        assert "pilot" in first["tags"]
        assert "pilot" not in second["tags"]


# ---------------------------------------------------------------------------
# Whisper feature flag — audio transcription hidden in the teaching build
# ---------------------------------------------------------------------------

class TestWhisperFlag:
    def _audio_upload(self, client):
        import io
        data = {"file": (io.BytesIO(b"\xff\xfb" + b"\x00" * 100), "intervju.mp3")}
        return client.post("/api/transcripts/upload", data=data,
                           content_type="multipart/form-data")

    def test_features_default_off(self, flask_client, monkeypatch):
        import main
        monkeypatch.delenv("TRANSCRIBBLER_ENABLE_WHISPER", raising=False)
        monkeypatch.setattr(main, "_load_config", lambda: {})
        r = flask_client.get("/api/features")
        assert r.status_code == 200
        assert r.get_json() == {"whisper": False}

    def test_features_enabled_by_config(self, flask_client, monkeypatch):
        import main
        monkeypatch.delenv("TRANSCRIBBLER_ENABLE_WHISPER", raising=False)
        monkeypatch.setattr(main, "_load_config", lambda: {"enable_whisper": True})
        assert flask_client.get("/api/features").get_json()["whisper"] is True

    def test_features_enabled_by_env(self, flask_client, monkeypatch):
        import main
        monkeypatch.setattr(main, "_load_config", lambda: {})
        monkeypatch.setenv("TRANSCRIBBLER_ENABLE_WHISPER", "1")
        assert flask_client.get("/api/features").get_json()["whisper"] is True

    def test_audio_upload_refused_when_disabled(self, flask_client, monkeypatch):
        import main
        monkeypatch.delenv("TRANSCRIBBLER_ENABLE_WHISPER", raising=False)
        monkeypatch.setattr(main, "_load_config", lambda: {})
        n_jobs = len(main.JOBS)
        r = self._audio_upload(flask_client)
        assert r.status_code == 400
        assert "inte tillgänglig" in r.get_json()["error"]
        assert len(main.JOBS) == n_jobs  # no background job started

    def test_text_upload_still_works(self, flask_client, monkeypatch):
        import io, main
        monkeypatch.delenv("TRANSCRIBBLER_ENABLE_WHISPER", raising=False)
        monkeypatch.setattr(main, "_load_config", lambda: {})
        data = {"file": (io.BytesIO("Hej hej.".encode("utf-8")), "intervju.txt")}
        r = flask_client.post("/api/transcripts/upload", data=data,
                              content_type="multipart/form-data")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# Analysis export follows the tag filter
# ---------------------------------------------------------------------------

class TestAnalysisExportTagFilter:
    def _excerpt(self, tid, name, code_id="c1"):
        return {
            "id": str(uuid.uuid4()), "code_id": code_id, "code_name": "Kod",
            "code_color": "#888", "code_number": "", "code_path": "Kod",
            "transcript_id": tid, "transcript_name": name, "transcript_label": "A",
            "coder": "testare", "kind": "text", "start": 0, "end": 4,
            "text": f"citat ur {name}", "memo": "", "weight": 50,
            "anchor": False, "created": "",
        }

    def _setup(self, flask_client, monkeypatch):
        import core.analysis
        a = _add_transcript(flask_client, name="Intervju-pilot", tags=["pilot"])
        b = _add_transcript(flask_client, name="Intervju-lärare", tags=["lärare"])
        c = _add_transcript(flask_client, name="Intervju-båda", tags=["pilot", "lärare"])
        excerpts = [self._excerpt(t["id"], t["name"]) for t in (a, b, c)]
        monkeypatch.setattr(core.analysis, "gather_excerpts",
                            lambda *a, **k: {"excerpts": excerpts, "code_counts": {}})

    def _export(self, flask_client, **body):
        r = flask_client.post("/api/analysis/export",
                              json={"format": "md", **body},
                              content_type="application/json")
        assert r.status_code == 200
        return r.get_data(as_text=True)

    def test_no_tags_exports_everything(self, flask_client, monkeypatch):
        self._setup(flask_client, monkeypatch)
        out = self._export(flask_client)
        assert "Intervju-pilot" in out and "Intervju-lärare" in out

    def test_any_mode(self, flask_client, monkeypatch):
        self._setup(flask_client, monkeypatch)
        out = self._export(flask_client, tags=["pilot"], tag_mode="any")
        assert "Intervju-pilot" in out and "Intervju-båda" in out
        assert "Intervju-lärare" not in out

    def test_all_mode(self, flask_client, monkeypatch):
        self._setup(flask_client, monkeypatch)
        out = self._export(flask_client, tags=["pilot", "lärare"], tag_mode="all")
        assert "Intervju-båda" in out
        assert "Intervju-pilot" not in out and "Intervju-lärare" not in out


# ---------------------------------------------------------------------------
# Encrypted projects: routes must pass the session key on
# ---------------------------------------------------------------------------

class TestRoutesPassKey:
    KEY = b"k" * 32

    def test_stats_passes_key(self, flask_client, monkeypatch):
        import main, core.stats
        seen = {}
        monkeypatch.setattr(main, "_key", lambda: self.KEY)
        def fake(folder, project, tid=None, *, key=None):
            seen["key"] = key
            return {"rows": []}
        monkeypatch.setattr(core.stats, "compute_stats", fake)
        assert flask_client.get("/api/stats").status_code == 200
        assert seen["key"] == self.KEY

    def test_irr_passes_key(self, flask_client, monkeypatch):
        import main, core.irr
        seen = {}
        monkeypatch.setattr(main, "_key", lambda: self.KEY)
        def fake(folder, project, tid, a, b, *, key=None):
            seen["key"] = key
            return {}
        monkeypatch.setattr(core.irr, "cohens_kappa", fake)
        r = flask_client.get("/api/transcripts/x/irr?coder_a=a&coder_b=b")
        assert r.status_code == 200
        assert seen["key"] == self.KEY

    def test_anchors_pass_key(self, flask_client, monkeypatch):
        import main, core.annotation
        seen = []
        _add_transcript(flask_client)
        monkeypatch.setattr(main, "_key", lambda: self.KEY)
        monkeypatch.setattr(core.annotation, "load_all_coders",
                            lambda folder, tid, key=None: seen.append(key) or {})
        assert flask_client.get("/api/codes/anchors").status_code == 200
        assert seen and all(k == self.KEY for k in seen)

    def test_commit_transcript_does_not_crash(self, flask_client, monkeypatch, tmp_path):
        # Regression: enc_key was undefined, so every audio commit returned 500
        import main
        monkeypatch.setattr(main, "_key", lambda: None)
        monkeypatch.setattr(main.proj_mod, "reload_project",
                            lambda folder, key=None: main.STATE["project"])
        monkeypatch.setattr(main.proj_mod, "add_audio_transcript",
                            lambda folder, proj, *a, key=None, **k: proj)
        main.JOBS["job-test"] = {"status": "done", "result": {
            "name": "Ljud", "settings": {}, "segments": [], "text": "hej",
            "audio_path": str(tmp_path / "ljud.wav"),
        }}
        r = flask_client.post("/api/transcripts/commit/job-test", json={},
                              content_type="application/json")
        assert r.status_code == 200, r.get_json()


# ---------------------------------------------------------------------------
# Backend localisation via the transcribbler_lang cookie
# ---------------------------------------------------------------------------

class TestBackendLanguage:
    def test_error_in_english_with_cookie(self, flask_client):
        flask_client.set_cookie("transcribbler_lang", "en")
        try:
            r = flask_client.get("/api/transcripts/x/irr?coder_a=a&coder_b=a")
            assert r.get_json()["error"] == "Choose two different coders."
        finally:
            flask_client.delete_cookie("transcribbler_lang")

    def test_error_in_swedish_by_default(self, flask_client):
        r = flask_client.get("/api/transcripts/x/irr?coder_a=a&coder_b=a")
        assert r.get_json()["error"] == "Välj två olika kodare."

    def test_unknown_language_falls_back_to_swedish(self, flask_client):
        flask_client.set_cookie("transcribbler_lang", "de")
        try:
            r = flask_client.get("/api/transcripts/x/irr?coder_a=a&coder_b=a")
            assert r.get_json()["error"] == "Välj två olika kodare."
        finally:
            flask_client.delete_cookie("transcribbler_lang")

    def test_analysis_export_english_heading_and_filename(self, flask_client, monkeypatch):
        import core.analysis
        monkeypatch.setattr(core.analysis, "gather_excerpts",
                            lambda *a, **k: {"excerpts": [], "code_counts": {}})
        flask_client.set_cookie("transcribbler_lang", "en")
        try:
            r = flask_client.post("/api/analysis/export", json={"format": "md"},
                                  content_type="application/json")
            assert r.status_code == 200
            assert r.get_data(as_text=True).startswith("# Analysis — ")
            cd = r.headers["Content-Disposition"]
            assert 'filename="analysis_' in cd and cd.endswith('.md"')
        finally:
            flask_client.delete_cookie("transcribbler_lang")


# ---------------------------------------------------------------------------
# Project export: scope and partial failures
# ---------------------------------------------------------------------------

class TestExportToFolder:
    def test_md_transcript_without_open_transcript_does_not_abort(self, flask_client, tmp_path):
        r = flask_client.post("/api/export/to-folder", json={
            "folder": str(tmp_path / "ut"), "formats": ["md_codebook", "md_transcript"],
            "tid": None, "current_tid": None,
        }, content_type="application/json")
        data = r.get_json()
        assert r.status_code == 200 and data["ok"]
        assert len(data["written"]) == 1          # the codebook was still written
        assert len(data["errors"]) == 1           # "this transcript" reported, not fatal

    def test_whole_project_scope_passes_no_tid(self, flask_client, tmp_path, monkeypatch):
        import main
        seen = {}
        def fake(folder, project, tid=None, *, key=None):
            seen["tid"] = tid
            return "x"
        monkeypatch.setattr(main.exp_mod, "export_csv", fake)
        flask_client.post("/api/export/to-folder", json={
            "folder": str(tmp_path / "ut2"), "formats": ["csv"],
            "tid": None, "current_tid": "abcd1234",
        }, content_type="application/json")
        assert seen["tid"] is None


    def test_csv_written_with_bom_and_crlf_untouched(self, flask_client, tmp_path):
        r = flask_client.post("/api/export/to-folder", json={
            "folder": str(tmp_path / "ut3"), "formats": ["csv_tidy"],
        }, content_type="application/json")
        data = (tmp_path / "ut3" / r.get_json()["written"][0]).read_bytes()
        assert data.startswith(b"\xef\xbb\xbf")
        assert b"\r\r\n" not in data

    def test_downloads_have_filename_and_type(self, flask_client):
        for url, ext, mime in [("/api/export/markdown/codebook", "md", "text/markdown"),
                               ("/api/export/codebook/csv", "csv", "text/csv"),
                               ("/api/export/code-matrix/csv", "csv", "text/csv"),
                               ("/api/export/cooccurrence/csv", "csv", "text/csv"),
                               ("/api/export/codetree/docx", "docx", "application/vnd.openxml"),
                               ("/api/codings/export", "json", "application/json")]:
            r = flask_client.get(url)
            assert r.status_code == 200, url
            assert r.headers["Content-Disposition"].endswith(f'.{ext}"'), url
            assert r.mimetype.startswith(mime), url
            if ext == "csv":
                assert r.data.startswith(b"\xef\xbb\xbf"), url


class TestCoderNameAndFilenames:
    def test_open_rejects_coder_with_dot(self, flask_client, tmp_project):
        folder, _ = tmp_project
        r = flask_client.post("/api/project/open", json={"folder": str(folder), "coder": "anna.s"},
                              content_type="application/json")
        assert r.status_code == 400

    def test_ascii_slug(self):
        import main
        assert main._ascii_slug("Åsa Öberg") == "Asa_Oberg"
        assert main._ascii_slug("Łukasz") == "ukasz"
        assert main._ascii_slug("") == ""

    def test_codings_export_non_latin1_coder(self, flask_client):
        import main
        old = main.STATE["coder"]
        main.STATE["coder"] = "Łukasz"
        try:
            r = flask_client.get("/api/codings/export")
            assert r.status_code == 200
            r.headers["Content-Disposition"].encode("latin-1")
        finally:
            main.STATE["coder"] = old
