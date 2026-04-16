"""
codebook.py — Code and theme management.
Codes can be flat (parent=None) or hierarchical (parent=code_id).
"""
import uuid
from datetime import datetime


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def add_code(project: dict, name: str, parent=None,
             color: str = "#4a90d9", description: str = "") -> dict:
    """Add a code and return updated project."""
    code = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "parent": parent,
        "color": color,
        "description": description,
        "created": _now(),
    }
    project["codes"].append(code)
    return project


def update_code(project: dict, code_id: str, **kwargs) -> dict:
    for code in project["codes"]:
        if code["id"] == code_id:
            for k, v in kwargs.items():
                if k in ("name", "parent", "color", "description"):
                    code[k] = v
            break
    return project


def delete_code(project: dict, code_id: str) -> dict:
    """
    Delete a code and re-parent its children to the deleted code's parent.
    Also removes the code from any annotations (caller must handle that).
    """
    target = next((c for c in project["codes"] if c["id"] == code_id), None)
    if not target:
        return project
    parent_of_deleted = target["parent"]
    # Re-parent children
    for c in project["codes"]:
        if c["parent"] == code_id:
            c["parent"] = parent_of_deleted
    project["codes"] = [c for c in project["codes"] if c["id"] != code_id]
    return project


def get_code(project: dict, code_id: str):
    return next((c for c in project["codes"] if c["id"] == code_id), None)


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------

def build_tree(project: dict) -> list:
    """
    Return a nested list representing the code hierarchy.
    Each node: {id, name, color, description, children: [...]}
    Root nodes (parent=None) are top-level.
    """
    codes = project.get("codes", [])
    by_id = {c["id"]: {**c, "children": []} for c in codes}
    roots = []
    for code in codes:
        node = by_id[code["id"]]
        if code["parent"] and code["parent"] in by_id:
            by_id[code["parent"]]["children"].append(node)
        else:
            roots.append(node)
    return roots


def merge_codes(project: dict, folder: str, source_id: str, target_id: str) -> dict:
    """
    Merge source code into target: move all annotations from source to target,
    re-parent source's children to target, then delete source.
    Returns updated project. Handles overlapping annotations by removing duplicates.
    """
    from core.annotation import load_all_coders, load_annotations, save_annotations

    source = get_code(project, source_id)
    target = get_code(project, target_id)
    if not source or not target:
        raise ValueError("Source or target code not found")

    for t in project.get("transcripts", []):
        tid = t["id"]
        by_coder = load_all_coders(folder, tid)
        for coder, anns in by_coder.items():
            changed = False
            target_anns = [a for a in anns if a.get("code_id") == target_id]
            for ann in anns:
                if ann.get("code_id") != source_id:
                    continue
                is_dup = any(
                    ta.get("start") == ann.get("start") and
                    ta.get("end") == ann.get("end") and
                    ta.get("kind") == ann.get("kind")
                    for ta in target_anns
                )
                if is_dup:
                    ann["_delete"] = True
                else:
                    ann["code_id"] = target_id
                changed = True
            if changed:
                save_annotations(folder, tid, coder,
                                 [a for a in anns if not a.get("_delete")])

    # Re-parent source's children to target
    for c in project["codes"]:
        if c["parent"] == source_id:
            c["parent"] = target_id

    project["codes"] = [c for c in project["codes"] if c["id"] != source_id]
    return project


def flat_list(project: dict) -> list:
    """Return all codes as a flat list with an 'ancestors' field for breadcrumb."""
    codes = project.get("codes", [])
    by_id = {c["id"]: c for c in codes}

    def ancestors(code):
        chain = []
        pid = code.get("parent")
        while pid and pid in by_id:
            chain.insert(0, by_id[pid]["name"])
            pid = by_id[pid].get("parent")
        return chain

    return [{**c, "ancestors": ancestors(c)} for c in codes]
