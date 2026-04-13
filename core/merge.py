"""
merge.py — Merge annotation files from multiple coders.
When a collaborator sends their annotation JSON file(s), drop them into the
project's annotations/ folder and call merge_coder() to import.
Conflicts (overlapping spans, different codes) are flagged but not auto-resolved.
"""
import json
import shutil
from pathlib import Path

from .annotation import load_annotations, save_annotations, ANNOTATIONS_DIR


def import_coder_file(folder: str, src_path: str) -> dict:
    """
    Import an external annotation JSON file into this project.
    Returns {"coder": str, "transcript_id": str, "imported": int, "skipped": int}
    """
    src = Path(src_path)
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    tid = data.get("transcript_id")
    coder = data.get("coder")
    incoming = data.get("annotations", [])

    if not tid or not coder:
        raise ValueError("Invalid annotation file: missing transcript_id or coder.")

    existing = load_annotations(folder, tid, coder)
    existing_ids = {a["id"] for a in existing}

    added = 0
    skipped = 0
    for ann in incoming:
        if ann["id"] in existing_ids:
            skipped += 1
        else:
            existing.append(ann)
            added += 1

    save_annotations(folder, tid, coder, existing)
    return {"coder": coder, "transcript_id": tid, "imported": added, "skipped": skipped}


def detect_conflicts(folder: str, tid: str) -> list:
    """
    Find overlapping spans between coders that have different codes assigned.
    Returns a list of conflict dicts.
    """
    from .annotation import load_all_coders

    all_coders = load_all_coders(folder, tid)
    if len(all_coders) < 2:
        return []

    # Flatten with coder label
    all_anns = []
    for coder, anns in all_coders.items():
        for a in anns:
            all_anns.append({**a, "coder": coder})

    conflicts = []
    for i, a in enumerate(all_anns):
        for b in all_anns[i + 1:]:
            if a["coder"] == b["coder"]:
                continue
            # Check overlap
            if a["start"] < b["end"] and b["start"] < a["end"]:
                if a["code_id"] != b["code_id"]:
                    conflicts.append({
                        "annotation_a": a,
                        "annotation_b": b,
                        "overlap_start": max(a["start"], b["start"]),
                        "overlap_end": min(a["end"], b["end"]),
                    })
    return conflicts
