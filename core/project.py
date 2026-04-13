"""
project.py — Project management for Transcribbler.
A project is a folder containing project.json, a transcripts/ subdir,
and an annotations/ subdir.
"""
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import docx

PROJECT_FILE = "project.json"
TRANSCRIPTS_DIR = "transcripts"
ANNOTATIONS_DIR = "annotations"

# Importera bildstöd från ocr-modulen (undviker duplicering)
from core.ocr import SUPPORTED_IMAGES, is_image  # noqa: E402


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Create / open
# ---------------------------------------------------------------------------

def create_project(folder: str, name: str, coder: str) -> dict:
    """Initialise a new project folder and return the project dict."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / TRANSCRIPTS_DIR).mkdir(exist_ok=True)
    (folder / ANNOTATIONS_DIR).mkdir(exist_ok=True)

    project = {
        "name": name,
        "coder": coder,
        "created": _now(),
        "modified": _now(),
        "codes": [],
        "transcripts": [],
        "speakers": [],   # voice profiles (future feature)
    }
    _save(folder, project)
    return project


def open_project(folder: str) -> dict:
    """Load and return an existing project dict."""
    path = Path(folder) / PROJECT_FILE
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_project(folder: str, project: dict):
    project["modified"] = _now()
    _save(Path(folder), project)


def set_transcript_photos(folder: str, project: dict, tid: str, photos: list) -> dict:
    """Attach a list of photo filenames to a transcript entry and save project.json."""
    for t in project.get("transcripts", []):
        if t["id"] == tid:
            t["photos"] = photos
            break
    _save(Path(folder), project)
    return project


def _save(folder: Path, project: dict):
    path = folder / PROJECT_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------

def add_transcript(folder: str, project: dict, src_path: str, name: str = "") -> dict:
    """
    Copy a .txt or .docx file into the project's transcripts/ dir,
    extract text, register it in the project, return updated project.
    """
    src = Path(src_path)
    ext = src.suffix.lower()
    tid = str(uuid.uuid4())[:8]
    dest_name = f"{tid}{ext}"
    dest = Path(folder) / TRANSCRIPTS_DIR / dest_name

    shutil.copy2(src, dest)

    # For .md files: extract frontmatter metadata (title, category) before text extraction
    fm = _parse_md_frontmatter(src) if ext == ".md" else {}

    text = _extract_text(src)
    # Save plain-text version alongside original
    txt_path = Path(folder) / TRANSCRIPTS_DIR / f"{tid}.txt"
    txt_path.write_text(text, encoding="utf-8")

    entry = {
        "id": tid,
        "name": name or fm.get("title") or src.stem,
        "original": dest_name,
        "text_file": f"{tid}.txt",
        "tags": [],
        "added": _now(),
    }
    if fm.get("category"):
        entry["category"] = fm["category"]
    project["transcripts"].append(entry)
    save_project(folder, project)
    return project


def add_audio_transcript(folder: str, project: dict, tid: str, name: str,
                         audio_src_path: str, text: str,
                         segments: list, meta: dict) -> dict:
    """
    Finalise an audio-sourced transcript after diarization + transcription.

    audio_src_path — path to the original audio temp file (will be copied)
    text           — speaker-labelled plain text
    segments       — [{speaker, start, end, text}]
    meta           — {whisper_model, language, diarization, diarization_settings,
                      speakers (name-mapping dict)}
    """
    import json as _json
    folder_path = Path(folder)
    audio_src = Path(audio_src_path)
    ext = audio_src.suffix.lower()

    # Copy audio file into project
    audio_dest_name = f"{tid}{ext}"
    audio_dest = folder_path / TRANSCRIPTS_DIR / audio_dest_name
    shutil.copy2(audio_src, audio_dest)

    # Write extracted plain text
    txt_path = folder_path / TRANSCRIPTS_DIR / f"{tid}.txt"
    txt_path.write_text(text, encoding="utf-8")

    # Write segments (separate file — can be large)
    seg_path = folder_path / TRANSCRIPTS_DIR / f"{tid}_segments.json"
    seg_path.write_text(
        _json.dumps(segments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    entry = {
        "id": tid,
        "name": name,
        "source": "audio",
        "original": audio_dest_name,
        "text_file": f"{tid}.txt",
        "audio_file": audio_dest_name,
        "whisper_model": meta.get("whisper_model", "medium"),
        "language": meta.get("language", "sv"),
        "diarization": meta.get("diarization", False),
        "diarization_settings": meta.get("diarization_settings", {}),
        "speakers": meta.get("speakers", {}),
        "tags": [],
        "added": _now(),
    }
    project["transcripts"].append(entry)
    save_project(folder, project)
    return project


def add_image_transcript(folder: str, project: dict, tid: str, name: str,
                         image_src_path: str, text: str) -> dict:
    """
    Finalise an image-sourced transcript after OCR.

    image_src_path — path to the (temp) image file (will be copied into project)
    text           — OCR-extracted plain text
    """
    folder_path = Path(folder)
    image_src = Path(image_src_path)
    ext = image_src.suffix.lower()

    # Copy source image into project
    source_dest_name = f"{tid}_source{ext}"
    source_dest = folder_path / TRANSCRIPTS_DIR / source_dest_name
    shutil.copy2(image_src, source_dest)

    # Write extracted plain text
    txt_path = folder_path / TRANSCRIPTS_DIR / f"{tid}.txt"
    txt_path.write_text(text, encoding="utf-8")

    entry = {
        "id": tid,
        "name": name,
        "source": "image",
        "source_file": source_dest_name,
        "text_file": f"{tid}.txt",
        "tags": [],
        "added": _now(),
    }
    project["transcripts"].append(entry)
    save_project(folder, project)
    return project


def get_transcript_text(folder: str, transcript: dict) -> str:
    path = Path(folder) / TRANSCRIPTS_DIR / transcript["text_file"]
    return path.read_text(encoding="utf-8")


def remove_transcript(folder: str, project: dict, tid: str) -> dict:
    t = next((t for t in project["transcripts"] if t["id"] == tid), None)
    if not t:
        return project
    for fname in [t.get("original"), t.get("text_file"), t.get("source_file")]:
        if fname:
            p = Path(folder) / TRANSCRIPTS_DIR / fname
            if p.exists():
                p.unlink()
    # Remove attached photos (imported from Notescribbler)
    for fname in t.get("photos", []):
        if fname:
            p = Path(folder) / TRANSCRIPTS_DIR / fname
            if p.exists():
                p.unlink()
    # Remove segments file (audio transcripts)
    seg_path = Path(folder) / TRANSCRIPTS_DIR / f"{tid}_segments.json"
    if seg_path.exists():
        seg_path.unlink()
    # Remove OCR boxes file (image transcripts)
    boxes_path = Path(folder) / TRANSCRIPTS_DIR / f"{tid}_ocr_boxes.json"
    if boxes_path.exists():
        boxes_path.unlink()
    project["transcripts"] = [t for t in project["transcripts"] if t["id"] != tid]
    # Remove all annotation files for this transcript
    ann_dir = Path(folder) / ANNOTATIONS_DIR
    for f in ann_dir.glob(f"{tid}.*.json"):
        f.unlink()
    save_project(folder, project)
    return project


def _parse_md_frontmatter(path: Path) -> dict:
    """
    Extract top-level scalar fields from YAML frontmatter in a .md file.
    Returns a dict with string values for keys found (e.g. title, category).
    List fields (tags, photos) and nested objects (location) are ignored.
    Returns {} if no frontmatter present.
    """
    import re
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"\A---\n(.*?)\n---\n?", raw, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([a-zA-Z_]\w*):\s*(.+)", line)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        # Skip list values and nested objects
        if value.startswith("[") or value.startswith("{"):
            continue
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        result[key] = value
    return result


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".odt":
        from odf import text as odftext, teletype
        from odf.opendocument import load as odf_load
        doc = odf_load(str(path))
        paragraphs = doc.spreadsheet if hasattr(doc, "spreadsheet") else []
        paras = doc.text.getElementsByType(odftext.P)
        return "\n".join(teletype.extractText(p) for p in paras)
    elif ext == ".md":
        import re
        raw = path.read_text(encoding="utf-8", errors="replace")
        # Strip YAML frontmatter block
        raw = re.sub(r"\A---\n.*?\n---\n?", "", raw, count=1, flags=re.DOTALL)
        # Strip Markdown syntax, return plain text
        raw = re.sub(r"^#{1,6}\s+", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", raw)
        raw = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", raw)
        raw = re.sub(r"`{1,3}[^`]*`{1,3}", "", raw)
        raw = re.sub(r"!\[.*?\]\(.*?\)", "", raw)
        raw = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", raw)
        return raw
    else:
        return path.read_text(encoding="utf-8", errors="replace")
