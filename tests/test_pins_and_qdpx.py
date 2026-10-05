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
    from core.export import export_markdown_transcripts
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 3), PIN]})
    md = export_markdown_transcripts(str(tmp_path), proj, TID)
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


def test_coded_transcripts_overlap_and_coders(tmp_path):
    from core.export import export_markdown_transcripts
    proj = _project(tmp_path, {
        "anna": [_text("0000bb01", "a", 0, 10), _text("0000bb02", "b", 5, 15)],
        "bo":   [_text("0000bb03", "c", 0, 3)],
    })
    md = export_markdown_transcripts(str(tmp_path), proj)
    # Overlap: the shared range carries both codes; with two coders, names are shown
    assert f"**[A · anna, B · anna]** *{TEXT[5:10].strip()}*" in md
    assert "C · bo" in md
    assert "4 kodningar" not in md and "3 kodningar" in md


def test_coded_transcripts_skip_uncoded_and_single_coder_has_no_name(tmp_path):
    from core.export import export_markdown_transcripts
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 3)]})
    proj["transcripts"].append({"id": "ffff0000", "name": "Okodad", "text_file": "ffff0000.txt"})
    (tmp_path / "transcripts" / "ffff0000.txt").write_text("Ingen kodning här", encoding="utf-8")
    md = export_markdown_transcripts(str(tmp_path), proj)
    assert "## Intervju" in md and "Okodad" not in md
    assert "**[A]**" in md and "· anna" not in md


def test_coded_transcripts_italics_do_not_span_lines(tmp_path):
    from core.export import _transcript_section
    t = {"id": "x", "name": "X"}
    ann = {"id": "1", "code_id": "a", "coder": "anna", "start": 0, "end": 9, "text": "rad1\nrad2"}
    md = _transcript_section({"codes": [{"id": "a", "name": "A"}]}, t, "rad1\nrad2 slut", [ann], False)
    assert "**[A]** *rad1*  \n*rad2*" in md


def test_coded_transcripts_keep_spaces_and_split_mid_word(tmp_path):
    from core.export import _transcript_section
    t = {"id": "x", "name": "X"}
    codes = {"codes": [{"id": "a", "name": "A"}]}
    ann = {"id": "1", "code_id": "a", "coder": "anna", "start": 3, "end": 8, "text": " och "}
    md = _transcript_section(codes, t, "Hej och hej", [ann], False)
    assert "Hej**[A]**  *och* hej" not in md and "Hej **[A]**  *och* hej" in md
    mid = {"id": "2", "code_id": "a", "coder": "anna", "start": 1, "end": 3, "text": "ej"}
    md = _transcript_section(codes, t, "Hej då", [mid], False)
    assert "H **[A]** *ej* då" in md


def test_coded_transcripts_singular_count(tmp_path):
    from core.export import export_markdown_transcripts
    from core.i18n import set_lang
    proj = _project(tmp_path, {"anna": [_text("0000bb01", "a", 0, 3)]})
    assert "_1 kodning_" in export_markdown_transcripts(str(tmp_path), proj)
    set_lang("en")
    try:
        md = export_markdown_transcripts(str(tmp_path), proj)
    finally:
        set_lang("sv")
    assert "_1 annotation_" in md and "Coded transcripts" in md and "Code summary" in md
