"""Tests for core/project.py — text extraction and frontmatter parsing."""
import pytest
from pathlib import Path
from core.project import _extract_text, _parse_md_frontmatter


# ---------------------------------------------------------------------------
# _parse_md_frontmatter
# ---------------------------------------------------------------------------

def test_frontmatter_title(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntitle: Min anteckning\ncategory: Intervju\n---\n\nText här.", encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert fm["title"] == "Min anteckning"
    assert fm["category"] == "Intervju"


def test_frontmatter_quoted_values(tmp_path):
    f = tmp_path / "note.md"
    f.write_text('---\ntitle: "Med citattecken"\n---\nText.', encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert fm["title"] == "Med citattecken"


def test_frontmatter_single_quoted(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntitle: 'Enkelfnuttar'\n---\nText.", encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert fm["title"] == "Enkelfnuttar"


def test_frontmatter_list_fields_ignored(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntags: [a, b, c]\nphotos:\n  - bild.jpg\n---\nText.", encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert "tags" not in fm
    assert "photos" not in fm


def test_frontmatter_no_frontmatter(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("Bara text, ingen frontmatter.", encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert fm == {}


def test_frontmatter_empty_file(tmp_path):
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    fm = _parse_md_frontmatter(f)
    assert fm == {}


# ---------------------------------------------------------------------------
# _extract_text — YAML frontmatter stripping
# ---------------------------------------------------------------------------

def test_md_frontmatter_stripped(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("---\ntitle: Test\ncategory: Foo\n---\n\nDetta är texten.", encoding="utf-8")
    text = _extract_text(f)
    assert "title" not in text
    assert "category" not in text
    assert "Detta är texten" in text


def test_md_no_frontmatter_untouched(tmp_path):
    f = tmp_path / "plain.md"
    f.write_text("# Rubrik\n\nBrödtext.", encoding="utf-8")
    text = _extract_text(f)
    assert "Rubrik" in text
    assert "Brödtext" in text


def test_md_markdown_syntax_stripped(tmp_path):
    f = tmp_path / "md.md"
    f.write_text("**Fet** och _kursiv_ text.", encoding="utf-8")
    text = _extract_text(f)
    assert "**" not in text
    assert "_" not in text
    assert "Fet" in text
    assert "kursiv" in text


# ---------------------------------------------------------------------------
# _extract_text — encoding fallback
# ---------------------------------------------------------------------------

def test_utf8_file(tmp_path):
    f = tmp_path / "utf8.txt"
    f.write_text("Åäö är svenska tecken.", encoding="utf-8")
    text = _extract_text(f)
    assert "Åäö" in text


def test_latin1_with_replacement(tmp_path):
    """Files with invalid UTF-8 bytes should not crash — errors='replace'."""
    f = tmp_path / "latin.txt"
    f.write_bytes("Hej \xe5\xe4\xf6 d\xe4r.".encode("latin-1"))
    # Should not raise — errors="replace" is expected behaviour
    text = _extract_text(f)
    assert isinstance(text, str)
    assert len(text) > 0
