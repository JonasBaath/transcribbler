"""
formatting.py — Per-user text formatting spans (bold, italic).
Stored in annotations/{tid}.{coder}.fmt.json
Character positions refer to the plain-text .txt file — never change.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

ANNOTATIONS_DIR = "annotations"
VALID_TYPES = {"bold", "italic"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _fmt_path(folder: str, tid: str, coder: str) -> Path:
    return Path(folder) / ANNOTATIONS_DIR / f"{tid}.{coder}.fmt.json"


def load_formatting(folder: str, tid: str, coder: str) -> list:
    path = _fmt_path(folder, tid, coder)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("spans", [])


def save_formatting(folder: str, tid: str, coder: str, spans: list):
    path = _fmt_path(folder, tid, coder)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"transcript_id": tid, "coder": coder, "spans": spans},
                  f, ensure_ascii=False, indent=2)


def add_format_span(folder: str, tid: str, coder: str,
                    start: int, end: int, fmt_type: str) -> dict:
    if fmt_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {fmt_type}")
    spans = load_formatting(folder, tid, coder)
    span = {"id": str(uuid.uuid4())[:8], "start": start,
            "end": end, "type": fmt_type, "created": _now()}
    spans.append(span)
    save_formatting(folder, tid, coder, spans)
    return span


def delete_format_span(folder: str, tid: str, coder: str, span_id: str) -> bool:
    spans = load_formatting(folder, tid, coder)
    new = [s for s in spans if s["id"] != span_id]
    if len(new) == len(spans):
        return False
    save_formatting(folder, tid, coder, new)
    return True
