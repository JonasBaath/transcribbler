"""
export.py — Export coded data to CSV and Markdown.
"""
from __future__ import annotations

import csv
import io
from .annotation import load_all_coders, is_text_annotation
from .codebook import get_code, build_tree
from .project import get_transcript_text
from .i18n import tr


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def export_csv(folder: str, project: dict, tid=None, *, key: bytes | None = None) -> str:
    """
    Export all annotations to CSV.
    If tid is given, only that transcript; otherwise all.
    Returns CSV as a string.
    """
    transcripts = project["transcripts"]
    if tid:
        transcripts = [t for t in transcripts if t["id"] == tid]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["transcript", "coder", "code", "theme_path",
                     "start", "end", "text", "memo", "created"])

    for t in transcripts:
        all_coders = load_all_coders(folder, t["id"], key=key)
        for coder, anns in all_coders.items():
            for ann in anns:
                if ann.get("kind") == "point":
                    continue  # skip image pins — no text positions
                code = get_code(project, ann["code_id"])
                code_name = code["name"] if code else ann["code_id"]
                # Build breadcrumb path
                path = _code_path(project, ann["code_id"])
                writer.writerow([
                    t["name"], coder, code_name, path,
                    ann.get("start", 0), ann.get("end", 0),
                    ann.get("text", ""),
                    ann.get("memo", ""), ann.get("created", ""),
                ])
    return output.getvalue()


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def export_markdown_by_code(folder: str, project: dict, tid=None, *, key: bytes | None = None) -> str:
    """
    Export quotes grouped by code/theme in Markdown format.
    """
    transcripts = project["transcripts"]
    if tid:
        transcripts = [t for t in transcripts if t["id"] == tid]

    # Gather all annotations keyed by code_id
    by_code: dict[str, list] = {}
    for t in transcripts:
        all_coders = load_all_coders(folder, t["id"], key=key)
        for coder, anns in all_coders.items():
            for ann in anns:
                cid = ann["code_id"]
                if cid not in by_code:
                    by_code[cid] = []
                by_code[cid].append({**ann, "transcript_name": t["name"], "coder": coder})

    if not by_code:
        return tr("_Inga kodningar hittades._") + "\n"

    lines = [f"# {tr('{name} — Kodade citat', name=project['name'])}\n"]

    tree = build_tree(project)
    _render_tree_md(tree, by_code, lines, level=2)

    # Codes that exist in annotations but not in codebook
    known_ids = {c["id"] for c in project["codes"]}
    orphans = [cid for cid in by_code if cid not in known_ids]
    if orphans:
        lines.append(f"## {tr('Okända koder')}\n")
        for cid in orphans:
            lines.append(f"### {cid}\n")
            for ann in by_code[cid]:
                lines.append(_format_quote(ann))

    return "\n".join(lines)


def export_csv_tidy(folder: str, project: dict, tid=None, *, key: bytes | None = None) -> str:
    """
    Export annotations in tidy (long) format for R/Python analysis.
    One row per annotation with all metadata as columns.
    """
    transcripts = project["transcripts"]
    if tid:
        transcripts = [t for t in transcripts if t["id"] == tid]

    by_id = {c["id"]: c for c in project.get("codes", [])}
    proj_name = project.get("name", "")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "project", "transcript", "transcript_category",
        "coder", "code", "parent_code", "code_path", "code_color",
        "start", "end", "text_length", "text", "memo",
        "weight", "anchor", "created",
    ])

    for t in transcripts:
        all_coders = load_all_coders(folder, t["id"], key=key)
        cat = t.get("category", "")
        for coder, anns in all_coders.items():
            for ann in anns:
                if ann.get("kind") == "point":
                    continue  # skip image pins — no text positions
                code = by_id.get(ann["code_id"])
                code_name   = code["name"] if code else ann["code_id"]
                parent_name = by_id.get(code["parent"], {}).get("name", "") if code and code.get("parent") else ""
                path        = _code_path(project, ann["code_id"])
                color       = code.get("color", "") if code else ""
                start = ann.get("start", 0)
                end   = ann.get("end", 0)
                writer.writerow([
                    proj_name,
                    t["name"],
                    cat,
                    coder,
                    code_name,
                    parent_name,
                    path,
                    color,
                    start,
                    end,
                    end - start,
                    ann.get("text", ""),
                    ann.get("memo", ""),
                    ann.get("weight", ""),
                    "TRUE" if ann.get("anchor") else "FALSE",
                    ann.get("created", ""),
                ])
    return output.getvalue()


def export_codebook_csv(project: dict, counts: dict | None = None) -> str:
    """
    Export the codebook as CSV.
    Columns: number, name, parent, description, count
    counts: optional {code_id: int} from stats.compute_stats
    """
    if counts is None:
        counts = {}

    tree = build_tree(project)
    _assign_numbers_py(tree, "")

    rows = []

    def _walk(nodes, parent_name):
        for node in nodes:
            rows.append({
                "number":      node.get("_number", ""),
                "name":        node["name"],
                "parent":      parent_name,
                "description": node.get("description", ""),
                "count":       counts.get(node["id"], 0),
            })
            _walk(node.get("children", []), node["name"])

    _walk(tree, "")

    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=["number", "name", "parent", "description", "count"],
    )
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def _assign_numbers_py(nodes: list, prefix: str):
    for i, node in enumerate(nodes):
        number = f"{prefix}.{i + 1}" if prefix else str(i + 1)
        node["_number"] = number
        _assign_numbers_py(node.get("children", []), number)


def export_markdown_codebook(project: dict, counts: dict | None = None) -> str:
    """Export the codebook as a Markdown document."""
    if counts is None:
        counts = {}
    lines = [f"# {tr('Kodbok — {name}', name=project['name'])}\n"]
    tree = build_tree(project)
    numbered = bool(project.get("numbering"))
    if numbered:
        _assign_numbers_py(tree, "")
    _render_codebook_tree(tree, lines, level=2, numbered=numbered, counts=counts)
    if not tree:
        lines.append(tr("_Kodboken är tom._") + "\n")
    return "\n".join(lines)


def export_markdown_transcripts(folder: str, project: dict, tid: str | None = None, *,
                                key: bytes | None = None) -> str:
    """Coded transcripts with codes marked inline: one transcript, or every coded one."""
    from datetime import date
    from .annotation import load_all_coders
    chosen = [t for t in project.get("transcripts", []) if tid is None or t["id"] == tid]
    sections, all_coders = [], set()
    for t in chosen:
        by_coder = load_all_coders(folder, t["id"], key=key)
        anns = [{**a, "coder": c} for c, lst in by_coder.items() for a in lst if is_text_annotation(a)]
        if not anns:
            continue
        coders = sorted({a["coder"] for a in anns})
        all_coders.update(coders)
        sections.append(_transcript_section(project, t, get_transcript_text(folder, t, key=key),
                                            anns, show_coder=len(coders) > 1))
    head = [f"# {tr('{name} — Kodade transkript', name=project.get('name', ''))}\n",
            f"_{tr('Exporterad {date}', date=date.today().isoformat())}"
            + (f" · {tr('Kodare: {coder}', coder=', '.join(sorted(all_coders)))}" if all_coders else "")
            + "_\n"]
    if not sections:
        head.append(tr("_Inga kodningar hittades._") + "\n")
    return "\n".join(head + sections)


def _italic(line: str) -> str:
    # Italics cannot span line breaks or start/end with a space, so keep spaces outside
    core = line.strip()
    if not core:
        return line
    lead = line[:len(line) - len(line.lstrip())]
    trail = line[len(line.rstrip()):]
    return f"{lead}*{core}*{trail}"


def _transcript_section(project: dict, t: dict, text: str, anns: list, show_coder: bool) -> str:
    def label(a):
        code = get_code(project, a["code_id"])
        name = code["name"] if code else tr("[borttagen: {id}]", id=a["code_id"])
        return f"{name} · {a['coder']}" if show_coder else name

    anns = sorted(anns, key=lambda a: (a["start"], -a["end"]))
    n = len(text)
    cuts = sorted({0, n} | {max(0, min(n, a[k])) for a in anns for k in ("start", "end")})
    body = []
    for s, e in zip(cuts, cuts[1:]):
        piece = text[s:e]
        active = [a for a in anns if a["start"] <= s and a["end"] >= e]
        if not active:
            body.append(piece)
            continue
        labels = list(dict.fromkeys(label(a) for a in active))
        # Markdown only renders "**[" as bold after whitespace, so split mid-word codings
        sep = " " if body and body[-1][-1:] not in ("", " ", "\n") else ""
        body.append(f"{sep}**[{', '.join(labels)}]** " + "\n".join(_italic(ln) for ln in piece.split("\n")))

    out = ["\n---\n", f"## {t.get('name', t['id'])}\n",
           # Hard line breaks keep each turn on its own line (Markdown joins single newlines)
           f"_{tr('1 kodning') if len(anns) == 1 else tr('{n} kodningar', n=len(anns))}_\n", "".join(body).replace("\n", "  \n"),
           f"\n### {tr('Kodsammanfattning')}\n"]
    for a in anns:
        excerpt = a.get("text") or text[a["start"]:a["end"]]
        key_mark = f" ({tr('nyckelpassage')})" if a.get("anchor") else ""
        out.append(f"- **{label(a)}**{key_mark}: {excerpt[:120]}{'…' if len(excerpt) > 120 else ''}")
        if a.get("memo"):
            out.append(f"  - _Memo: {a['memo']}_")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _code_path(project: dict, code_id: str) -> str:
    """Return 'Grandparent > Parent > Code' breadcrumb."""
    by_id = {c["id"]: c for c in project["codes"]}
    chain = []
    cid = code_id
    while cid and cid in by_id:
        chain.insert(0, by_id[cid]["name"])
        cid = by_id[cid].get("parent")
    return " > ".join(chain)


def _format_quote(ann: dict) -> str:
    lines = [f"\n**{ann['transcript_name']}** _({tr('kodare: {coder}', coder=ann['coder'])})_"]
    lines.append(f"> {ann['text']}")
    if ann.get("memo"):
        lines.append(f"> _Memo: {ann['memo']}_")
    return "\n".join(lines) + "\n"


def _render_tree_md(nodes: list, by_code: dict, lines: list, level: int):
    for node in nodes:
        hashes = "#" * level
        quotes = by_code.get(node["id"], [])
        if quotes or node["children"]:
            lines.append(f"{hashes} {node['name']}\n")
            if node.get("description"):
                lines.append(f"_{node['description']}_\n")
            for ann in quotes:
                lines.append(_format_quote(ann))
            _render_tree_md(node["children"], by_code, lines, level + 1)


def _render_codebook_tree(nodes: list, lines: list, level: int,
                          numbered: bool = False, counts: dict | None = None):
    if counts is None:
        counts = {}
    for node in nodes:
        hashes = "#" * level
        num = f"{node['_number']}. " if numbered and node.get("_number") else ""
        cnt = counts.get(node["id"], 0)
        cnt_str = f" ({cnt})" if counts else ""
        lines.append(f"{hashes} {num}{node['name']}{cnt_str}\n")
        if node.get("description"):
            lines.append(f"{node['description']}\n")
        _render_codebook_tree(node["children"], lines, level + 1,
                              numbered=numbered, counts=counts)


# ---------------------------------------------------------------------------
# Code tree DOCX / ODT exports
# ---------------------------------------------------------------------------

def export_codetree_docx(project: dict) -> bytes:
    """Export the code tree as a Word .docx file."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
    except ImportError:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    import io

    tree = build_tree(project)
    numbered = bool(project.get("numbering"))
    if numbered:
        _assign_numbers_py(tree, "")
    doc = Document()
    doc.add_heading(tr("Kodbok — {name}", name=project["name"]), 0)

    def _hex_rgb(hex_color):
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _walk(nodes, depth):
        for node in nodes:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(depth * 18)
            bullet = "■ " if depth == 0 else "▸ "
            num = f"{node['_number']}. " if numbered and node.get("_number") else ""
            run = p.add_run("  " * depth + bullet + num + node["name"])
            run.bold = (depth == 0)
            run.font.size = Pt(max(9, 13 - depth))
            try:
                r, g, b = _hex_rgb(node.get("color", "#888888"))
                run.font.color.rgb = RGBColor(r, g, b)
            except Exception:
                pass
            if node.get("description"):
                dp = doc.add_paragraph("  " * (depth + 1) + node["description"])
                dp.paragraph_format.left_indent = Pt(depth * 18 + 10)
                if dp.runs:
                    dp.runs[0].italic = True
                    dp.runs[0].font.size = Pt(10)
            _walk(node["children"], depth + 1)

    _walk(tree, 0)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_codetree_odt(project: dict) -> bytes:
    """Export the code tree as an OpenDocument Text .odt file."""
    try:
        from odf.opendocument import OpenDocumentText
        from odf.text import P, H
    except ImportError:
        raise RuntimeError("odfpy not installed. Run: pip install odfpy")
    import io

    tree = build_tree(project)
    numbered = bool(project.get("numbering"))
    if numbered:
        _assign_numbers_py(tree, "")
    doc = OpenDocumentText()

    title_el = H(outlinelevel=1)
    title_el.addText(tr("Kodbok — {name}", name=project["name"]))
    doc.text.addElement(title_el)

    def _walk(nodes, depth):
        for node in nodes:
            num = f"{node['_number']}. " if numbered and node.get("_number") else ""
            if depth == 0:
                h = H(outlinelevel=2)
                h.addText(num + node["name"])
                doc.text.addElement(h)
            else:
                p = P()
                p.addText("  " * depth + "• " + num + node["name"])
                doc.text.addElement(p)
            if node.get("description"):
                dp = P()
                dp.addText("  " * (depth + 1) + node["description"])
                doc.text.addElement(dp)
            _walk(node["children"], depth + 1)

    _walk(tree, 0)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
