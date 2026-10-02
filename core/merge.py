"""
merge.py — Exchange codings between coders.

Classroom flow: every student codes in their own copy of the project and sends
back a codings file made with export_coder_bundle(). import_coder_bundle()
matches transcripts by id, falling back to the text's SHA-256 (so a copy whose
transcripts were imported separately still matches), and codes by id, falling
back to name; codes that are still missing are created. Anything that cannot
be matched is reported rather than written as invisible orphans.

Older single-transcript files ({transcript_id, coder, annotations}) are still
accepted. Conflicts (overlapping spans, different codes) are flagged but not
auto-resolved.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .annotation import load_annotations, save_annotations, is_valid_coder_name
from .codebook import add_code
from .i18n import tr
from .project import get_transcript_text

BUNDLE_FORMAT = "transcribbler-codings"


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def export_coder_bundle(folder: str, project: dict, coder: str, *,
                        key: bytes | None = None) -> dict:
    """All of one coder's annotations plus the codes they use (with ancestors)."""
    by_id = {c["id"]: c for c in project.get("codes", [])}
    used = set()
    transcripts = []
    for t in project.get("transcripts", []):
        anns = load_annotations(folder, t["id"], coder, key=key)
        if not anns:
            continue
        try:
            text_hash = _text_hash(get_transcript_text(folder, t, key=key))
        except Exception:
            text_hash = None
        transcripts.append({"id": t["id"], "name": t.get("name", t["id"]),
                            "text_sha256": text_hash, "annotations": anns})
        used.update(a.get("code_id") for a in anns)
    # Include ancestors so the hierarchy can be rebuilt on import
    needed = set()
    for cid in used:
        while cid and cid in by_id and cid not in needed:
            needed.add(cid)
            cid = by_id[cid].get("parent")
    codes = [{k: c.get(k) for k in ("id", "name", "parent", "color", "description")}
             for c in project.get("codes", []) if c["id"] in needed]
    return {
        "format": BUNDLE_FORMAT, "version": 1,
        "coder": coder, "project_name": project.get("name", ""),
        "exported": datetime.now().isoformat(timespec="seconds"),
        "codes": codes, "transcripts": transcripts,
    }


def read_codings_file(path: str, *, key: bytes | None = None) -> dict:
    """Load a bundle or a legacy annotation file (decrypting it with the
    project key if it comes from this encrypted project)."""
    src = Path(path)
    if key:
        from .crypto import is_encrypted_file, decrypt_json_file
        if is_encrypted_file(src):
            return decrypt_json_file(src, key)
    with open(src, encoding="utf-8") as f:
        return json.load(f)


def _as_bundle(data: dict) -> dict:
    if isinstance(data, dict) and data.get("format") == BUNDLE_FORMAT:
        ok = (isinstance(data.get("codes", []), list)
              and isinstance(data.get("transcripts"), list)
              and all(isinstance(t, dict) and isinstance(t.get("annotations", []), list)
                      and all(isinstance(a, dict) for a in t.get("annotations", []))
                      for t in data["transcripts"])
              and all(isinstance(c, dict) for c in data.get("codes", [])))
        if not ok:
            raise ValueError(tr("Filen är inte en kodningsfil från Transcribbler."))
        return data
    if (isinstance(data, dict) and data.get("transcript_id") and data.get("coder")
            and isinstance(data.get("annotations", []), list)
            and all(isinstance(a, dict) for a in data.get("annotations", []))):
        return {"coder": data["coder"], "codes": [],
                "transcripts": [{"id": data["transcript_id"], "name": data["transcript_id"],
                                 "text_sha256": None,
                                 "annotations": data.get("annotations", [])}]}
    raise ValueError(tr("Filen är inte en kodningsfil från Transcribbler."))


def import_coder_bundle(folder: str, project: dict, data: dict, *,
                        key: bytes | None = None, save_project=None) -> tuple:
    """
    Merge a codings file into the project. Returns (project, report).
    If codes are created, ``save_project(project)`` is called before any
    annotation file is written, so annotations never point to unsaved codes.
    """
    bundle = _as_bundle(data)
    coder = bundle.get("coder")
    if not isinstance(coder, str) or not is_valid_coder_name(coder.strip()):
        raise ValueError(tr("Filen saknar ett giltigt kodarnamn."))
    coder = coder.strip()

    # --- transcripts: id first, then identical text --------------------------
    local = {t["id"]: t for t in project.get("transcripts", [])}
    hashes = {}
    def local_hash(tid):
        if tid not in hashes:
            try:
                hashes[tid] = _text_hash(get_transcript_text(folder, local[tid], key=key))
            except Exception:
                hashes[tid] = None
        return hashes[tid]

    # --- codes: id, then name (case-insensitive), else create ----------------
    by_id = {c["id"]: c for c in project.get("codes", [])}
    by_name = {}
    for c in project.get("codes", []):
        by_name.setdefault(c["name"].strip().lower(), c["id"])
    incoming_codes = {c["id"]: c for c in bundle.get("codes", []) if c.get("id")}
    code_map, created = {}, []

    def map_code(cid):
        if cid in code_map:
            return code_map[cid]
        code_map[cid] = None  # guards against parent cycles in the file
        if cid in by_id:
            code_map[cid] = cid
        elif cid in incoming_codes:
            src = incoming_codes[cid]
            name = (src.get("name") or "").strip()
            hit = by_name.get(name.lower())
            if hit:
                code_map[cid] = hit
            else:
                parent = map_code(src["parent"]) if src.get("parent") else None
                add_code(project, name or cid, parent=parent,
                         color=src.get("color") or "#4a90d9",
                         description=src.get("description") or "")
                new = project["codes"][-1]
                by_id[new["id"]] = new
                by_name[new["name"].lower()] = new["id"]
                code_map[cid] = new["id"]
                created.append(new["name"])
        # else: unknown code and no definition in the file → stays None
        return code_map[cid]

    report = {"coder": coder, "imported": 0, "skipped": 0, "unknown_code": 0,
              "transcripts_matched": 0, "transcripts_unmatched": [],
              "text_changed": [], "codes_created": created, "transcript_ids": []}

    pending = {}  # target tid -> annotations to write once everything is mapped
    for tr_in in bundle.get("transcripts", []):
        tid = tr_in.get("id")
        want = tr_in.get("text_sha256")
        target = None
        if tid in local:
            target = tid
            if want and local_hash(tid) and local_hash(tid) != want:
                report["text_changed"].append(local[tid].get("name", tid))
        elif want:
            target = next((x for x in local if local_hash(x) == want), None)
        if not target:
            report["transcripts_unmatched"].append(tr_in.get("name") or tid)
            continue
        report["transcripts_matched"] += 1
        report["transcript_ids"].append(target)

        existing = pending[target] if target in pending else load_annotations(folder, target, coder, key=key)
        existing_ids = {a.get("id") for a in existing}
        changed = False
        for ann in tr_in.get("annotations", []):
            if ann.get("id") in existing_ids:
                report["skipped"] += 1
                continue
            new_cid = map_code(ann.get("code_id"))
            if not new_cid:
                report["unknown_code"] += 1
                continue
            existing.append({**ann, "code_id": new_cid})
            existing_ids.add(ann.get("id"))
            report["imported"] += 1
            changed = True
        if changed:
            pending[target] = existing

    if not report["transcripts_matched"]:
        raise ValueError(tr("Inget transkript i filen finns i det här projektet. "
                            "Kodningsfiler måste komma från en kopia av samma projekt "
                            "eller från transkript med identisk text."))
    if created and save_project:
        save_project(project)
    for target, anns in pending.items():
        save_annotations(folder, target, coder, anns, key=key)
    return project, report


def import_coder_file(folder: str, src_path: str, *, key: bytes | None = None,
                      project: dict | None = None) -> dict:
    """Backwards-compatible wrapper used by POST /api/merge."""
    data = read_codings_file(src_path, key=key)
    project, report = import_coder_bundle(folder, project or {"transcripts": [], "codes": []},
                                          data, key=key)
    return report


def detect_conflicts(folder: str, tid: str, *, key: bytes | None = None) -> list:
    """
    Find overlapping spans between coders that have different codes assigned.
    Returns a list of conflict dicts.
    """
    from .annotation import load_all_coders, is_text_annotation

    all_coders = load_all_coders(folder, tid, key=key)
    if len(all_coders) < 2:
        return []

    # Flatten with coder label
    all_anns = []
    for coder, anns in all_coders.items():
        for a in anns:
            if is_text_annotation(a):
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
