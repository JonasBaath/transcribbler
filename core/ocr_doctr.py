"""
ocr_doctr.py — Mindee docTR OCR backend (Windows / Linux, och macOS utan Vision).

Kräver: python-doctr[torch]  (pip install "python-doctr[torch]")
Modeller laddas ned automatiskt vid första körning (~150 MB, sedan cachat).

docTR hanterar hela dokument i ett steg: layoutanalys + igenkänning inbyggt.
"""
from __future__ import annotations
from pathlib import Path

# Modulnivå-cache
_DOCTR_MODEL = None


def _load_doctr(progress_cb=None):
    """Ladda docTR-modellen och cachelagra den."""
    global _DOCTR_MODEL
    if _DOCTR_MODEL is not None:
        return _DOCTR_MODEL

    try:
        from doctr.models import ocr_predictor
    except ImportError:
        raise ImportError(
            "python-doctr är inte installerat. "
            'Kör: pip install "python-doctr[torch]"'
        )

    if progress_cb:
        progress_cb("loading_model", 0.05)

    # pretrained=True laddar ned modeller automatiskt vid första körning
    _DOCTR_MODEL = ocr_predictor(pretrained=True)

    if progress_cb:
        progress_cb("loading_model", 0.35)

    return _DOCTR_MODEL


def ocr_image_doctr(image_path: str, progress_cb=None) -> dict:
    """
    Extrahera text ur en bild med Mindee docTR.
    Returnerar {"text": str, "boxes": [{"text", "x", "y", "w", "h"}]}.
    Koordinater i boxes är normaliserade (0-1), top-left origin.
    """
    def _cb(stage: str, frac: float):
        if progress_cb:
            progress_cb(stage, frac)

    try:
        from doctr.io import DocumentFile
    except ImportError:
        raise ImportError(
            "python-doctr är inte installerat. "
            'Kör: pip install "python-doctr[torch]"'
        )

    model = _load_doctr(progress_cb=progress_cb)
    _cb("ocr", 0.40)

    ext = Path(image_path).suffix.lower()
    if ext == ".pdf":
        doc = DocumentFile.from_pdf(image_path)
    else:
        doc = DocumentFile.from_images(image_path)

    result = model(doc)
    _cb("ocr", 0.90)

    # Extrahera text i läsordning: sida → block → rad → ord
    lines = []
    boxes = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                words = [word.value for word in line.words]
                if words:
                    lines.append(" ".join(words))
                    # geometry: ((x_min, y_min), (x_max, y_max)), normalized, top-left origin
                    geo = line.geometry
                    x0, y0 = float(geo[0][0]), float(geo[0][1])
                    x1, y1 = float(geo[1][0]), float(geo[1][1])
                    boxes.append({
                        "text": " ".join(words),
                        "x": x0, "y": y0,
                        "w": x1 - x0, "h": y1 - y0,
                    })

    _cb("done", 1.0)
    return {"text": "\n".join(lines), "boxes": boxes}
