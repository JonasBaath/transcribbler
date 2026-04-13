"""
annotation.py — Per-user annotation storage.
Annotations are stored as:  annotations/{transcript_id}.{coder}.json
Each annotation stores character offsets into the plain-text transcript.
"""
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

def load_annotations(folder: str, tid: str, coder: str) -> list:
    path = _ann_path(folder, tid, coder)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("annotations", [])


def save_annotations(folder: str, tid: str, coder: str, annotations: list):
    path = _ann_path(folder, tid, coder)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"transcript_id": tid, "coder": coder, "annotations": annotations},
            f,
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_annotation(folder: str, tid: str, coder: str,
                   code_id: str, start: int, end: int,
                   text: str, memo: str = "",
                   weight: int = 50, anchor: bool = False) -> dict:
    annotations = load_annotations(folder, tid, coder)
    ann = {
        "id": str(uuid.uuid4())[:8],
        "code_id": code_id,
        "start": start,
        "end": end,
        "text": text,
        "memo": memo,
        "weight": int(weight),
        "anchor": bool(anchor),
        "created": _now(),
    }
    annotations.append(ann)
    save_annotations(folder, tid, coder, annotations)
    return ann


def update_annotation(folder: str, tid: str, coder: str,
                      ann_id: str, **kwargs) -> bool:
    annotations = load_annotations(folder, tid, coder)
    for ann in annotations:
        if ann["id"] == ann_id:
            for k, v in kwargs.items():
                if k in ("code_id", "memo", "weight", "anchor"):
                    if k == "weight":
                        ann[k] = int(v)
                    elif k == "anchor":
                        ann[k] = bool(v)
                    else:
                        ann[k] = v
            save_annotations(folder, tid, coder, annotations)
            return True
    return False


def delete_annotation(folder: str, tid: str, coder: str, ann_id: str) -> bool:
    annotations = load_annotations(folder, tid, coder)
    new = [a for a in annotations if a["id"] != ann_id]
    if len(new) == len(annotations):
        return False
    save_annotations(folder, tid, coder, new)
    return True


# ---------------------------------------------------------------------------
# Multi-coder view
# ---------------------------------------------------------------------------

def load_all_coders(folder: str, tid: str) -> dict:
    """Return {coder: [annotations]} for all coders on a transcript."""
    ann_dir = Path(folder) / ANNOTATIONS_DIR
    result = {}
    for f in ann_dir.glob(f"{tid}.*.json"):
        coder = f.stem[len(tid) + 1:]
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        result[coder] = data.get("annotations", [])
    return result
