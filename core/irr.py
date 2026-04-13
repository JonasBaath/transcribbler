"""
irr.py — Inter-rater reliability: Cohen's Kappa between two coders.

Approach: character-level agreement.
For each character position in the transcript, we record which code_id
each coder assigned (or None if uncoded). Cohen's Kappa is computed on
these two vectors.
"""
from .annotation import load_annotations
from .project import get_transcript_text


def cohens_kappa(folder: str, project: dict, tid: str,
                 coder_a: str, coder_b: str) -> dict:
    """
    Compute Cohen's Kappa between two coders on a single transcript.
    Returns a dict with kappa, po, pe, agreement details.
    """
    t = next((t for t in project["transcripts"] if t["id"] == tid), None)
    if not t:
        raise ValueError(f"Transcript {tid} not found.")

    text = get_transcript_text(folder, t)
    n = len(text)
    if n == 0:
        raise ValueError("Transcript is empty.")

    anns_a = load_annotations(folder, tid, coder_a)
    anns_b = load_annotations(folder, tid, coder_b)

    # Build character-level label vectors
    vec_a = _build_vector(anns_a, n)
    vec_b = _build_vector(anns_b, n)

    # Collect all categories
    categories = sorted(set(vec_a) | set(vec_b))

    # Observed agreement (Po)
    agree = sum(1 for a, b in zip(vec_a, vec_b) if a == b)
    po = agree / n

    # Expected agreement (Pe) — marginal probabilities
    pe = 0.0
    for cat in categories:
        p_a = vec_a.count(cat) / n
        p_b = vec_b.count(cat) / n
        pe += p_a * p_b

    kappa = (po - pe) / (1 - pe) if pe < 1.0 else 1.0

    # Per-code breakdown
    code_map = {c["id"]: c for c in project.get("codes", [])}
    per_code = []
    coded_cats = [c for c in categories if c is not None]
    for cid in coded_cats:
        a_count = vec_a.count(cid)
        b_count = vec_b.count(cid)
        both    = sum(1 for a, b in zip(vec_a, vec_b) if a == cid and b == cid)
        code = code_map.get(cid)
        per_code.append({
            "code_id":   cid,
            "name":      code["name"] if code else cid,
            "color":     code["color"] if code else "#888",
            "coder_a":   a_count,
            "coder_b":   b_count,
            "agreement": both,
        })
    per_code.sort(key=lambda x: x["coder_a"] + x["coder_b"], reverse=True)

    return {
        "coder_a":      coder_a,
        "coder_b":      coder_b,
        "transcript":   t["name"],
        "n_chars":      n,
        "po":           round(po, 4),
        "pe":           round(pe, 4),
        "kappa":        round(kappa, 4),
        "interpretation": _interpret(kappa),
        "per_code":     per_code,
    }


def _build_vector(anns: list, n: int) -> list:
    """Map each char position to its code_id (last annotation wins on overlap)."""
    vec = [None] * n
    for ann in sorted(anns, key=lambda a: a["start"]):
        s = max(0, ann["start"])
        e = min(n, ann["end"])
        for i in range(s, e):
            vec[i] = ann["code_id"]
    return vec


def _interpret(kappa: float) -> str:
    if kappa < 0:
        return "Sämre än slumpen"
    elif kappa < 0.20:
        return "Minimal överenstämmelse"
    elif kappa < 0.40:
        return "Svag överenstämmelse"
    elif kappa < 0.60:
        return "Måttlig överenstämmelse"
    elif kappa < 0.80:
        return "Stark överenstämmelse"
    else:
        return "Nästan perfekt överenstämmelse"
