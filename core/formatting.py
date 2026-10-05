"""
formatting.py — Per-user text formatting spans (bold, italic).
Stored in annotations/{tid}.{coder}.fmt.json
Character positions refer to the plain-text .txt file — never change.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from core.crypto import read_project_json, write_project_json

ANNOTATIONS_DIR = "annotations"
VALID_TYPES = {"bold", "italic"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _fmt_path(folder: str, tid: str, coder: str) -> Path:
    return Path(folder) / ANNOTATIONS_DIR / f"{tid}.{coder}.fmt.json"


def load_formatting(folder: str, tid: str, coder: str,
                    key: bytes | None = None) -> list:
    path = _fmt_path(folder, tid, coder)
    if not path.exists():
        return []
    data = read_project_json(path, key)
    return data.get("spans", []) if isinstance(data, dict) else data


def save_formatting(folder: str, tid: str, coder: str, spans: list,
                    key: bytes | None = None):
    path = _fmt_path(folder, tid, coder)
    payload = {"transcript_id": tid, "coder": coder, "spans": spans}
    write_project_json(path, payload, key)


def add_format_span(folder: str, tid: str, coder: str,
                    start: int, end: int, fmt_type: str,
                    key: bytes | None = None) -> dict:
    if fmt_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {fmt_type}")
    spans = load_formatting(folder, tid, coder, key=key)
    span = {"id": str(uuid.uuid4())[:8], "start": start,
            "end": end, "type": fmt_type, "created": _now()}
    spans.append(span)
    save_formatting(folder, tid, coder, spans, key=key)
    return span


def delete_format_span(folder: str, tid: str, coder: str, span_id: str,
                       key: bytes | None = None) -> bool:
    spans = load_formatting(folder, tid, coder, key=key)
    new = [s for s in spans if s["id"] != span_id]
    if len(new) == len(spans):
        return False
    save_formatting(folder, tid, coder, new, key=key)
    return True
