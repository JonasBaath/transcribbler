"""Span-based computations must ignore image pins; QDPX must hold plain text."""
import io
import json
import zipfile

import pytest

TID = "a1b2c3d4"
TEXT = "Hej och välkommen till intervjun."
PIN = {"id": "0000aa01", "code_id": "b", "kind": "point", "x": 0.1, "y": 0.2}


def _project(tmp_path, anns_by_coder, encrypt_key=None):
    (tmp_path / "annotations").mkdir()
    (tmp_path / "transcripts").mkdir()
    txt = tmp_path / "transcripts" / f"{TID}.txt"
    if encrypt_key:
        from core.crypto import encrypt_text_file
        encrypt_text_file(txt, TEXT, encrypt_key)
    else:
        txt.write_text(TEXT, encoding="utf-8")
    for coder, anns in anns_by_coder.items():
        (tmp_path / "annotations" / f"{TID}.{coder}.json").write_text(
            json.dumps({"annotations": anns}), encoding="utf-8")
    return {
        "name": "P",
        "transcripts": [{"id": TID, "name": "Intervju", "text_file": f"{TID}.txt"}],
        "codes": [{"id": c, "name": c.upper(), "color": "#888", "parent": None}
                  for c in ("a", "b", "c")],
    }


def _text(id_, code, s, e):
    return {"id": id_, "code_id": code, "kind": "text", "start": s, "end": e,
            "text": TEXT[s:e]}


def test_cooccurrence_ignores_pins_and_other_coders(tmp_path):
    from core.cooccurrence import compute_cooccurrence
    proj = _project(tmp_path, {
        "anna": [_text("0000bb01", "a", 0, 10), _text("0000bb02", "c", 5, 15), PIN],
        "bo":   [_text("0000bb03", "b", 0, 10)],  # overlaps anna's "a", but another coder
    })
    m = compute_cooccurrence(str(tmp_path), proj)["matrix"]
    assert m == {"a": {"c": 1}, "c": {"a": 1}}


def test_markdown_transcript_export_with_pin(tmp_path):
    from core.export import export_markdown_transcript
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 3), PIN]})
    md = export_markdown_transcript(str(tmp_path), proj, TID, "anna")
    assert "**[A]** *Hej*" in md


def test_irr_ignores_pins(tmp_path):
    from core.irr import cohens_kappa
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 10), PIN],
                               "bo": [_text("0000bb02", "a", 0, 10)]})
    assert cohens_kappa(str(tmp_path), proj, TID, "anna", "bo")["kappa"] == pytest.approx(1.0)


def test_qdpx_writes_decrypted_sources(tmp_path):
    from core.qdpx import export_qdpx
    key = b"k" * 32
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 3)]}, encrypt_key=key)
    data = export_qdpx(str(tmp_path), proj, key=key)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.read(f"sources/{TID}.txt").decode("utf-8") == TEXT


def test_irr_partial_coding_and_disagreement(tmp_path):
    # Regression: sorting None (uncoded) with code ids raised TypeError
    from core.irr import cohens_kappa
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 10)],
                               "bo":   [_text("0000bb02", "b", 0, 10)]})
    res = cohens_kappa(str(tmp_path), proj, TID, "anna", "bo")
    assert res["kappa"] < 0.5


def test_irr_no_codings_is_an_error(tmp_path):
    from core.irr import cohens_kappa
    proj = _project(tmp_path, {"anna": [], "bo": []})
    with pytest.raises(ValueError):
        cohens_kappa(str(tmp_path), proj, TID, "anna", "bo")
