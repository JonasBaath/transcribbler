"""
stats.py — Code usage statistics across a project or single transcript.
"""
from __future__ import annotations

from .annotation import load_all_coders
from .codebook import get_code, build_tree


def compute_stats(folder: str, project: dict, tid: str = None, *, key: bytes | None = None) -> dict:
    """
    Return code usage statistics.
    If tid is given: stats for that transcript only, else across all transcripts.
    """
    transcripts = project["transcripts"]
    if tid:
        transcripts = [t for t in transcripts if t["id"] == tid]

    # code_id -> {count, coders, char_count}
    usage = {}

    for t in transcripts:
        all_coders = load_all_coders(folder, t["id"], key=key)
        for coder, anns in all_coders.items():
            for ann in anns:
                cid = ann["code_id"]
                if cid not in usage:
                    usage[cid] = {"count": 0, "coders": set(), "char_count": 0}
                usage[cid]["count"] += 1
                usage[cid]["coders"].add(coder)
                usage[cid]["char_count"] += max(0, ann.get("end", 0) - ann.get("start", 0))

    # Enrich with code metadata
    code_map = {c["id"]: c for c in project.get("codes", [])}
    rows = []
    for cid, data in usage.items():
        code = code_map.get(cid)
        rows.append({
            "code_id":    cid,
            "name":       code["name"] if code else f"[borttagen: {cid}]",
            "color":      code["color"] if code else "#888",
            "parent":     code.get("parent") if code else None,
            "count":      data["count"],
            "char_count": data["char_count"],
            "coders":     sorted(data["coders"]),
        })

    rows.sort(key=lambda r: r["count"], reverse=True)
    total = sum(r["count"] for r in rows)

    return {
        "rows": rows,
        "total_annotations": total,
        "transcript_count": len(transcripts),
        "tree": _stats_tree(build_tree(project), usage),
    }


def _stats_tree(nodes: list, usage: dict) -> list:
    result = []
    for node in nodes:
        u = usage.get(node["id"], {})
        result.append({
            "id":         node["id"],
            "name":       node["name"],
            "color":      node["color"],
            "count":      u.get("count", 0),
            "char_count": u.get("char_count", 0),
            "children":   _stats_tree(node.get("children", []), usage),
        })
    return result
