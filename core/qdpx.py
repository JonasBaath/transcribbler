"""
qdpx.py — REFI-QDA Project Exchange (.qdpx) export.

Produces a ZIP archive containing project.qde (XML per the REFI-QDA 1.0 standard)
and plain-text source files. Audio files are referenced but not embedded (too large).

Standard reference: https://www.qdasoftware.org/products-project-exchange/
Namespace: urn:QDA-XML:project:1.0
"""
from __future__ import annotations
import io
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .annotation import load_all_coders

_NS = "urn:QDA-XML:project:1.0"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"
_SCHEMA = "urn:QDA-XML:project:1.0 http://schema.qdasoftware.org/versions/Project/v1.0/Project.xsd"

# Register namespace so ElementTree serialises without ns0: prefix
ET.register_namespace("", _NS)
ET.register_namespace("xsi", _XSI)


def _guid(short_id: str, _cache: dict = {}) -> str:
    """Map a Transcribbler short ID (8 hex chars) to a stable UUID4 string."""
    if short_id not in _cache:
        # Deterministic: pad short_id to 32 hex chars and format as UUID
        padded = short_id.ljust(32, "0")
        _cache[short_id] = str(uuid.UUID(padded))
    return _cache[short_id]


def _fresh_guid() -> str:
    return str(uuid.uuid4())


def _sub(parent, tag, **attrib):
    return ET.SubElement(parent, f"{{{_NS}}}{tag}", **attrib)


def export_qdpx(folder: str, project: dict,
                key: bytes | None = None) -> bytes:
    """
    Build and return a .qdpx (ZIP) file as bytes.

    Structure:
      project.qde          — XML per REFI-QDA 1.0
      sources/{tid}.txt    — plain-text transcript files
    """
    folder_path = Path(folder)
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    project_name = project.get("name", "Transcribbler Project")

    # -----------------------------------------------------------------------
    # Build XML tree
    # -----------------------------------------------------------------------
    root = ET.Element(
        f"{{{_NS}}}Project",
        attrib={
            f"{{{_XSI}}}schemaLocation": _SCHEMA,
            "name":               project_name,
            "origin":             "Transcribbler",
            "creatingUserGUID":   _fresh_guid(),
            "creationDateTime":   now_iso,
            "basePath":           ".",
        },
    )

    # Users — one entry per coder found in annotation files
    coders: set = set()
    # Collect coders by scanning annotation dir
    ann_dir = folder_path / "annotations"
    if ann_dir.exists():
        for f in ann_dir.glob("*.*.json"):
            if f.name.endswith(".fmt.json"):
                continue
            parts = f.stem.split(".", 1)
            if len(parts) == 2:
                coders.add(parts[1])
    if not coders:
        coders.add("unknown")

    users_el = _sub(root, "Users")
    coder_guids = {}
    for coder in sorted(coders):
        g = _fresh_guid()
        coder_guids[coder] = g
        _sub(users_el, "User", guid=g, name=coder)

    # CodeBook
    cb_el = _sub(root, "CodeBook")
    codes_el = _sub(cb_el, "Codes")
    code_map = {c["id"]: c for c in project.get("codes", [])}

    def _add_code_el(parent_el, node):
        c_el = _sub(
            parent_el, "Code",
            guid=_guid(node["id"]),
            name=node["name"],
            isCodable="true",
            color=node.get("color", "#888888"),
        )
        if node.get("description"):
            desc_el = _sub(c_el, "Description")
            desc_el.text = node["description"]
        for child in node.get("children", []):
            _add_code_el(c_el, child)

    # Build tree from flat codes list
    from .codebook import build_tree
    tree = build_tree(project)
    for node in tree:
        _add_code_el(codes_el, node)

    # Sources
    sources_el = _sub(root, "Sources")
    transcripts = project.get("transcripts", [])

    for t in transcripts:
        tid = t["id"]
        txt_path = folder_path / "transcripts" / f"{tid}.txt"
        if not txt_path.exists():
            continue

        if key:
            from core.crypto import is_encrypted_file, decrypt_text_file
            if is_encrypted_file(txt_path):
                plain_text = decrypt_text_file(txt_path, key)
            else:
                plain_text = txt_path.read_text(encoding="utf-8")
        else:
            plain_text = txt_path.read_text(encoding="utf-8")
        internal_path = f"sources/{tid}.txt"

        src_el = _sub(
            sources_el, "TextSource",
            guid=_guid(tid),
            name=t.get("name", tid),
            plainTextPath=internal_path,
            creationDateTime=now_iso,
        )

        # Codings — one per annotation per coder
        all_coders_data = load_all_coders(folder, tid, key=key)
        for coder, anns in all_coders_data.items():
            coder_guid = coder_guids.get(coder, _fresh_guid())
            for ann in anns:
                if ann.get("kind") == "point":
                    continue  # skip image pins — no text positions for QDPX
                code = code_map.get(ann["code_id"])
                if not code:
                    continue  # skip annotations for deleted codes
                coding_el = _sub(
                    src_el, "Coding",
                    guid=_guid(ann["id"]),
                    creatingUser=coder_guid,
                    creationDateTime=ann.get("created", now_iso),
                )
                _sub(coding_el, "CodeRef", targetGUID=_guid(ann["code_id"]))
                _sub(
                    coding_el, "SelectionExtension",
                    startPosition=str(ann["start"]),
                    endPosition=str(ann["end"]),
                )
                if ann.get("memo"):
                    note_el = _sub(coding_el, "ModifyingUser", modifyingUser=coder_guid)
                    # Memo stored as a NoteRef comment in description
                    # (REFI-QDA has no native memo on Coding; use Description)
                    desc_el = _sub(coding_el, "Description")
                    desc_el.text = ann["memo"]

    # -----------------------------------------------------------------------
    # Serialise XML
    # -----------------------------------------------------------------------
    ET.indent(root, space="  ")  # Python 3.9+
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=True)
    if not xml_bytes.startswith("<?xml"):
        xml_bytes = '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n' + xml_bytes

    # -----------------------------------------------------------------------
    # Build ZIP
    # -----------------------------------------------------------------------
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.qde", xml_bytes.encode("utf-8"))
        for t in transcripts:
            tid = t["id"]
            txt_path = folder_path / "transcripts" / f"{tid}.txt"
            if txt_path.exists():
                zf.write(txt_path, f"sources/{tid}.txt")

    return buf.getvalue()
