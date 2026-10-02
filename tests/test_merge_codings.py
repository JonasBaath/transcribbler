"""Exchanging codings between coders (core/merge.py + routes)."""
import io
import json

import pytest

from core.annotation import load_annotations
from core.merge import export_coder_bundle, import_coder_bundle

TEXT = "Intervjuare: Hur började det?\nAnna: Det var 2019."


def _proj(tmp_path, tid, codes, text=TEXT):
    (tmp_path / "annotations").mkdir(exist_ok=True)
    (tmp_path / "transcripts").mkdir(exist_ok=True)
    (tmp_path / "transcripts" / f"{tid}.txt").write_text(text, encoding="utf-8")
    return {"name": "P", "codes": codes,
            "transcripts": [{"id": tid, "name": "Intervju A", "text_file": f"{tid}.txt"}]}


def _write(tmp_path, tid, coder, anns):
    (tmp_path / "annotations" / f"{tid}.{coder}.json").write_text(
        json.dumps({"transcript_id": tid, "coder": coder, "annotations": anns}), encoding="utf-8")


CODES = [{"id": "c0", "name": "Bakgrund", "parent": None, "color": "#111"},
         {"id": "c1", "name": "Start", "parent": "c0", "color": "#222"}]
ANN = {"id": "a1", "code_id": "c1", "kind": "text", "start": 0, "end": 11, "text": "Intervjuare"}


def test_bundle_matches_by_text_and_creates_codes(tmp_path):
    src, dst = tmp_path / "student", tmp_path / "teacher"
    src.mkdir(); dst.mkdir()
    sp = _proj(src, "aaaa0001", CODES)
    _write(src, "aaaa0001", "elev1", [ANN])
    bundle = export_coder_bundle(str(src), sp, "elev1")
    assert {c["id"] for c in bundle["codes"]} == {"c0", "c1"}  # ancestors included

    # Teacher imported the same text separately: other id, no codes yet
    dp = _proj(dst, "bbbb0002", [])
    dp, rep = import_coder_bundle(str(dst), dp, bundle)
    assert rep["imported"] == 1 and rep["transcripts_matched"] == 1
    assert rep["codes_created"] == ["Bakgrund", "Start"]
    by_name = {c["name"]: c for c in dp["codes"]}
    assert by_name["Start"]["parent"] == by_name["Bakgrund"]["id"]
    anns = load_annotations(str(dst), "bbbb0002", "elev1")
    assert anns[0]["code_id"] == by_name["Start"]["id"]


def test_bundle_matches_existing_code_by_name(tmp_path):
    src, dst = tmp_path / "s", tmp_path / "t"
    src.mkdir(); dst.mkdir()
    sp = _proj(src, "aaaa0001", CODES)
    _write(src, "aaaa0001", "elev1", [ANN])
    bundle = export_coder_bundle(str(src), sp, "elev1")
    dp = _proj(dst, "aaaa0001", [{"id": "zz", "name": "start", "parent": None, "color": "#000"}])
    dp, rep = import_coder_bundle(str(dst), dp, bundle)
    assert rep["codes_created"] == []
    assert load_annotations(str(dst), "aaaa0001", "elev1")[0]["code_id"] == "zz"


def test_reimport_skips_duplicates(tmp_path):
    p = _proj(tmp_path, "aaaa0001", CODES)
    _write(tmp_path, "aaaa0001", "elev1", [ANN])
    bundle = export_coder_bundle(str(tmp_path), p, "elev1")
    p, rep = import_coder_bundle(str(tmp_path), p, bundle)
    assert rep["imported"] == 0 and rep["skipped"] == 1


def test_unmatched_transcript_is_an_error_not_silent(tmp_path):
    p = _proj(tmp_path, "aaaa0001", CODES)
    legacy = {"transcript_id": "ffff9999", "coder": "elev1", "annotations": [ANN]}
    with pytest.raises(ValueError):
        import_coder_bundle(str(tmp_path), p, legacy)


def test_text_changed_is_reported(tmp_path):
    src, dst = tmp_path / "s", tmp_path / "t"
    src.mkdir(); dst.mkdir()
    sp = _proj(src, "aaaa0001", CODES)
    _write(src, "aaaa0001", "elev1", [ANN])
    bundle = export_coder_bundle(str(src), sp, "elev1")
    dp = _proj(dst, "aaaa0001", CODES, text=TEXT + " Tillägg.")
    dp, rep = import_coder_bundle(str(dst), dp, bundle)
    assert rep["text_changed"] == ["Intervju A"]


def test_invalid_coder_name_rejected(tmp_path):
    p = _proj(tmp_path, "aaaa0001", CODES)
    with pytest.raises(ValueError):
        import_coder_bundle(str(tmp_path), p,
                            {"transcript_id": "aaaa0001", "coder": "../x", "annotations": []})


class TestCodingsRoutes:
    def test_export_then_upload(self, flask_client, tmp_project):
        import main
        folder, _ = tmp_project
        (folder / "annotations").mkdir(exist_ok=True)
        (folder / "transcripts" / "cccc0003.txt").write_text(TEXT, encoding="utf-8")
        main.STATE["project"]["transcripts"].append(
            {"id": "cccc0003", "name": "Intervju C", "text_file": "cccc0003.txt"})
        main.STATE["project"]["codes"].extend(CODES)
        main.proj_mod.save_project(str(folder), main.STATE["project"])  # import reloads from disk
        _write(folder, "cccc0003", "testare", [ANN])

        r = flask_client.get("/api/codings/export")
        assert r.status_code == 200
        assert "attachment" in r.headers["Content-Disposition"]
        bundle = r.get_json()
        assert bundle["coder"] == "testare" and len(bundle["transcripts"]) == 1

        bundle["coder"] = "elev2"
        r = flask_client.post("/api/codings/import", data={
            "file": (io.BytesIO(json.dumps(bundle).encode("utf-8")), "kodningar.json"),
        }, content_type="multipart/form-data")
        assert r.status_code == 200, r.get_json()
        assert r.get_json()["imported"] == 1
        assert load_annotations(str(folder), "cccc0003", "elev2")[0]["id"] == "a1"

    def test_upload_rejects_non_json(self, flask_client):
        r = flask_client.post("/api/codings/import", data={
            "file": (io.BytesIO(b"x"), "fil.txt")}, content_type="multipart/form-data")
        assert r.status_code == 400


def test_parent_cycle_in_file_does_not_recurse_forever(tmp_path):
    p = _proj(tmp_path, "aaaa0001", [])
    bundle = {"format": "transcribbler-codings", "coder": "elev1",
              "codes": [{"id": "x", "name": "X", "parent": "y"},
                        {"id": "y", "name": "Y", "parent": "x"}],
              "transcripts": [{"id": "aaaa0001", "annotations": [dict(ANN, code_id="x")]}]}
    p, rep = import_coder_bundle(str(tmp_path), p, bundle)
    assert rep["imported"] == 1


@pytest.mark.parametrize("bad", [
    {"format": "transcribbler-codings", "coder": "elev1", "transcripts": None},
    {"format": "transcribbler-codings", "coder": "elev1", "transcripts": [{"annotations": ["x"]}]},
    {"transcript_id": "aaaa0001", "coder": "elev1", "annotations": "nope"},
    ["not", "a", "dict"],
])
def test_malformed_files_give_clear_error(tmp_path, bad):
    p = _proj(tmp_path, "aaaa0001", CODES)
    with pytest.raises(ValueError):
        import_coder_bundle(str(tmp_path), p, bad)


@pytest.mark.parametrize("coder", ["Anna: grupp 2", "anna.s", "a*b"])
def test_unsafe_coder_names_rejected(tmp_path, coder):
    p = _proj(tmp_path, "aaaa0001", CODES)
    with pytest.raises(ValueError):
        import_coder_bundle(str(tmp_path), p,
                            {"transcript_id": "aaaa0001", "coder": coder, "annotations": []})


def test_project_saved_before_annotations(tmp_path):
    src, dst = tmp_path / "s", tmp_path / "t"
    src.mkdir(); dst.mkdir()
    sp = _proj(src, "aaaa0001", CODES)
    _write(src, "aaaa0001", "elev1", [ANN])
    bundle = export_coder_bundle(str(src), sp, "elev1")
    dp = _proj(dst, "aaaa0001", [])
    order = []
    import core.merge as m
    orig = m.save_annotations
    m.save_annotations = lambda *a, **k: (order.append("ann"), orig(*a, **k))
    try:
        import_coder_bundle(str(dst), dp, bundle, save_project=lambda p: order.append("project"))
    finally:
        m.save_annotations = orig
    assert order == ["project", "ann"]
