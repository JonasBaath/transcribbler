"""
analysis.py — Gather coded excerpts across all transcripts for the analysis view.
"""
from pathlib import Path
from .annotation import load_all_coders
from .codebook import build_tree
from .export import _code_path, _assign_numbers_py
from .project import get_transcript_text


def _tree_walk_order(tree):
    """Yield (code_id, order_index) pairs in tree-walk order."""
    idx = [0]

    def walk(nodes):
        for node in nodes:
            yield node["id"], idx[0]
            idx[0] += 1
            walk(node.get("children", []))

    yield from walk(tree)


def gather_excerpts(folder: str, project: dict):
    """
    Gather all coded excerpts across all transcripts.
    Returns {excerpts: [...], code_counts: {code_id: count}}.
    Sorted: codebook order → transcript label → start position.
    """
    codes = project.get("codes", [])
    code_map = {c["id"]: c for c in codes}

    tree = build_tree(project)
    numbered = bool(project.get("numbering"))
    if numbered:
        _assign_numbers_py(tree, "")

    # Build code order from tree walk
    code_order = {}
    number_map = {}

    def collect_tree(nodes):
        for node in nodes:
            code_order[node["id"]] = len(code_order)
            number_map[node["id"]] = node.get("_number", "")
            collect_tree(node.get("children", []))

    collect_tree(tree)

    transcripts = project.get("transcripts", [])
    trans_label_map = {}
    for i, t in enumerate(transcripts):
        label = ""
        n = i
        while True:
            label = chr(ord("A") + n % 26) + label
            n = n // 26 - 1
            if n < 0:
                break
        trans_label_map[t["id"]] = label

    excerpts = []
    code_counts = {}

    for t_idx, t in enumerate(transcripts):
        tid = t["id"]
        by_coder = load_all_coders(folder, tid)
        text = get_transcript_text(folder, t)

        for coder, anns in by_coder.items():
            for ann in anns:
                code_id = ann.get("code_id")
                if not code_id or code_id not in code_map:
                    continue
                code = code_map[code_id]
                code_counts[code_id] = code_counts.get(code_id, 0) + 1

                ann_text = ann.get("text", "")
                if not ann_text and ann.get("kind") == "text":
                    s, e = ann.get("start", 0), ann.get("end", 0)
                    ann_text = text[s:e] if text else ""

                excerpts.append({
                    "id": ann["id"],
                    "code_id": code_id,
                    "code_name": code["name"],
                    "code_color": code.get("color", "#888"),
                    "code_number": number_map.get(code_id, ""),
                    "code_path": _code_path(project, code_id),
                    "transcript_id": tid,
                    "transcript_name": t.get("name", tid),
                    "transcript_label": trans_label_map.get(tid, ""),
                    "coder": coder,
                    "kind": ann.get("kind", "text"),
                    "start": ann.get("start", 0),
                    "end": ann.get("end", 0),
                    "text": ann_text,
                    "memo": ann.get("memo", ""),
                    "weight": ann.get("weight", 50),
                    "anchor": ann.get("anchor", False),
                    "created": ann.get("created", ""),
                })

    # Sort: codebook order → transcript label → start position
    excerpts.sort(key=lambda e: (
        code_order.get(e["code_id"], 999),
        e["transcript_label"],
        e["start"],
    ))

    return {"excerpts": excerpts, "code_counts": code_counts}
