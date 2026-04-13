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
