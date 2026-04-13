"""
cooccurrence.py — Code co-occurrence matrix: code × code character-overlap counts.

Two annotations co-occur when their character ranges overlap in the same transcript.
The matrix is symmetric: matrix[a][b] == matrix[b][a].
"""
from __future__ import annotations
from .annotation import load_all_coders


def compute_cooccurrence(folder: str, project: dict) -> dict:
    """
    Returns:
      {
        "codes":  [{"id": cid, "name": name, "color": color}, ...],
        "matrix": {code_id_a: {code_id_b: count}},
      }
    Only codes that actually appear in annotations are included.
    Self-pairs (diagonal) are always 0.
    """
    transcripts = project.get("transcripts", [])
    code_map = {c["id"]: c for c in project.get("codes", [])}

    # matrix[a][b] = number of transcripts/passages where a and b overlap
    matrix: dict = {}
    seen_codes: set = set()

    for t in transcripts:
        tid = t["id"]
        all_coders = load_all_coders(folder, tid)

        # Flatten all annotations across coders for this transcript
        all_anns = []
        for coder_anns in all_coders.values():
            all_anns.extend(coder_anns)

        # Check all pairs for character overlap
        for i, a in enumerate(all_anns):
            seen_codes.add(a["code_id"])
            for b in all_anns[i + 1:]:
                seen_codes.add(b["code_id"])
                if a["code_id"] == b["code_id"]:
                    continue
                # Overlap: max(starts) < min(ends)
                if max(a["start"], b["start"]) < min(a["end"], b["end"]):
                    ca, cb = a["code_id"], b["code_id"]
                    matrix.setdefault(ca, {})
                    matrix.setdefault(cb, {})
                    matrix[ca][cb] = matrix[ca].get(cb, 0) + 1
                    matrix[cb][ca] = matrix[cb].get(ca, 0) + 1

    codes_out = []
    for cid in sorted(seen_codes):
        c = code_map.get(cid)
        codes_out.append({
            "id":    cid,
            "name":  c["name"] if c else f"[borttagen: {cid}]",
            "color": c["color"] if c else "#888",
        })

    return {
        "codes":  codes_out,
        "matrix": matrix,
    }
