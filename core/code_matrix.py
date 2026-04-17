"""
code_matrix.py — Code matrix: transcripts × codes frequency table.

Returns a matrix where rows = transcripts, columns = codes, cells = annotation count.
Distinct from cooccurrence (code × code overlap); this shows per-transcript coding density.
"""
from __future__ import annotations
from .annotation import load_all_coders


def compute_code_matrix(folder: str, project: dict, *, key: bytes | None = None) -> dict:
    """
    Returns:
      {
        "transcripts": [{"id": tid, "name": name}, ...],
        "codes":       [{"id": cid, "name": name, "color": color}, ...],
        "matrix":      {tid: {code_id: count}},
        "totals":      {code_id: total_count},
      }
    All codes that appear in any annotation are included.
    Codes in the codebook but with zero annotations are omitted.
    """
    transcripts = project.get("transcripts", [])
    code_map = {c["id"]: c for c in project.get("codes", [])}

    # Build matrix: tid → {code_id → count}
    matrix: dict = {}
    seen_codes: set = set()

    for t in transcripts:
        tid = t["id"]
        counts: dict = {}
        all_coders = load_all_coders(folder, tid, key=key)
        for coder_anns in all_coders.values():
            for ann in coder_anns:
                cid = ann["code_id"]
                counts[cid] = counts.get(cid, 0) + 1
                seen_codes.add(cid)
        matrix[tid] = counts

    # Ordered list of codes that appear at least once
    codes_out = []
    for cid in sorted(seen_codes):
        c = code_map.get(cid)
        codes_out.append({
            "id":    cid,
            "name":  c["name"] if c else f"[borttagen: {cid}]",
            "color": c["color"] if c else "#888",
        })

    # Column totals
    totals = {c["id"]: sum(matrix[t["id"]].get(c["id"], 0) for t in transcripts)
              for c in codes_out}

    transcripts_out = [{"id": t["id"], "name": t.get("name", t["id"])}
                       for t in transcripts]

    return {
        "transcripts": transcripts_out,
        "codes":       codes_out,
        "matrix":      matrix,
        "totals":      totals,
    }
