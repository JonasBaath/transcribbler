"""
annotation.py — Per-user annotation storage.
Annotations are stored as:  annotations/{transcript_id}.{coder}.json
Each annotation stores character offsets into the plain-text transcript.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

ANNOTATIONS_DIR = "annotations"


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _ann_path(folder: str, tid: str, coder: str) -> Path:
    return Path(folder) / ANNOTATIONS_DIR / f"{tid}.{coder}.json"


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def load_annotations(folder: str, tid: str, coder: str,
                     key: bytes | None = None) -> list:
    path = _ann_path(folder, tid, coder)
    if not path.exists():
        return []
    if key:
        from core.crypto import is_encrypted_file, decrypt_json_file
        if is_encrypted_file(path):
            data = decrypt_json_file(path, key)
            return data.get("annotations", []) if isinstance(data, dict) else data
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("annotations", [])


def save_annotations(folder: str, tid: str, coder: str, annotations: list,
                     key: bytes | None = None):
    path = _ann_path(folder, tid, coder)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"transcript_id": tid, "coder": coder, "annotations": annotations}
    if key:
        from core.crypto import encrypt_json_file
        encrypt_json_file(path, payload, key)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_annotation(folder: str, tid: str, coder: str,
                   code_id: str, memo: str = "",
                   weight: int = 50, anchor: bool = False,
                   kind: str = "text",
                   start: int = None, end: int = None, text: str = None,
                   x: float = None, y: float = None,
                   key: bytes | None = None) -> dict:
    annotations = load_annotations(folder, tid, coder, key=key)
    ann = {
        "id": str(uuid.uuid4())[:8],
        "code_id": code_id,
        "kind": kind,
        "memo": memo,
        "weight": int(weight),
        "anchor": bool(anchor),
        "created": _now(),
    }
    if kind == "point":
        ann["x"] = float(x)
        ann["y"] = float(y)
    else:
        ann["start"] = start
        ann["end"] = end
        ann["text"] = text
    annotations.append(ann)
    save_annotations(folder, tid, coder, annotations, key=key)
    return ann


def update_annotation(folder: str, tid: str, coder: str,
                      ann_id: str, key: bytes | None = None, **kwargs) -> bool:
    annotations = load_annotations(folder, tid, coder, key=key)
    for ann in annotations:
        if ann["id"] == ann_id:
            for k, v in kwargs.items():
                if k in ("code_id", "memo", "weight", "anchor", "x", "y"):
                    if k == "weight":
                        ann[k] = int(v)
                    elif k == "anchor":
                        ann[k] = bool(v)
                    elif k in ("x", "y"):
                        if ann.get("kind") == "point":
                            ann[k] = float(v)
                    else:
                        ann[k] = v
            save_annotations(folder, tid, coder, annotations, key=key)
            return True
    return False


def delete_annotation(folder: str, tid: str, coder: str, ann_id: str,
                      key: bytes | None = None) -> bool:
    annotations = load_annotations(folder, tid, coder, key=key)
    new = [a for a in annotations if a["id"] != ann_id]
    if len(new) == len(annotations):
        return False
    save_annotations(folder, tid, coder, new, key=key)
    return True


# ---------------------------------------------------------------------------
# Multi-coder view
# ---------------------------------------------------------------------------

def load_all_coders(folder: str, tid: str,
                    key: bytes | None = None) -> dict:
    """Return {coder: [annotations]} for all coders on a transcript."""
    ann_dir = Path(folder) / ANNOTATIONS_DIR
    result = {}
    for f in ann_dir.glob(f"{tid}.*.json"):
        coder = f.stem[len(tid) + 1:]
        # Skip sidecar files such as formatting (".fmt") — annotation coders
        # are plain identifiers without dots.
        if "." in coder:
            continue
        if key:
            from core.crypto import is_encrypted_file, decrypt_json_file
            if is_encrypted_file(f):
                data = decrypt_json_file(f, key)
                result[coder] = data.get("annotations", []) if isinstance(data, dict) else data
                continue
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        result[coder] = data.get("annotations", [])
    return result
