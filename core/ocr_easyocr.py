"""
ocr_easyocr.py — EasyOCR-backend för Win/Linux (och macOS utan Vision).

Stöder svenska (åäö) och engelska out-of-the-box. Modeller (~80 MB)
laddas ned automatiskt vid första körning och cachas i ~/.EasyOCR/.

Kräver: easyocr>=1.7  (pip install easyocr)
"""
from __future__ import annotations
from pathlib import Path

_READER = None


def _load_reader(progress_cb=None):
    global _READER
    if _READER is not None:
        return _READER
    try:
        import easyocr
    except ImportError:
        raise ImportError(
            "easyocr är inte installerat. Kör: pip install easyocr"
        )
    if progress_cb:
        progress_cb("loading_model", 0.05)
    # GPU=False ger förutsägbar prestanda på alla plattformar; EasyOCR
    # försöker annars cuda och faller tillbaka till CPU med varning.
    import torch
    use_gpu = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    _READER = easyocr.Reader(["sv", "en"], gpu=use_gpu, verbose=False)
    if progress_cb:
        progress_cb("loading_model", 0.35)
    return _READER


def ocr_image_easyocr(image_path: str, progress_cb=None) -> dict:
    """Returnerar {"text": str, "boxes": [{text, x, y, w, h}]} (0-1 norm)."""
    def _cb(stage, frac):
        if progress_cb:
            progress_cb(stage, frac)

    reader = _load_reader(progress_cb=progress_cb)
    _cb("ocr", 0.40)

    # readtext returnerar lista av (bbox, text, conf). bbox = 4 hörnpunkter i px.
    from PIL import Image
    with Image.open(image_path) as im:
        iw, ih = im.size
    results = reader.readtext(image_path, detail=1, paragraph=False)
    _cb("ocr", 0.90)

    lines = []
    boxes = []
    # Sortera i läsordning (y sedan x)
    def _key(r):
        pts = r[0]
        ys = [p[1] for p in pts]; xs = [p[0] for p in pts]
        return (min(ys), min(xs))
    for pts, text, _conf in sorted(results, key=_key):
        if not text:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = min(xs) / iw, max(xs) / iw
        y0, y1 = min(ys) / ih, max(ys) / ih
        lines.append(text)
        boxes.append({
            "text": text,
            "x": float(x0), "y": float(y0),
            "w": float(x1 - x0), "h": float(y1 - y0),
        })

    _cb("done", 1.0)
    return {"text": "\n".join(lines), "boxes": boxes}
