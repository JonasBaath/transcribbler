"""
ocr_easyocr.py — EasyOCR backend for Windows/Linux (and macOS without Vision).

Supports Swedish (å, ä, ö) and English. Models (~80 MB) are downloaded on
first use and cached in ~/.EasyOCR/.

Requires: easyocr>=1.7
"""
from __future__ import annotations

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
    # Ask for CUDA only when it exists; otherwise EasyOCR warns before falling back to CPU
    import torch
    use_gpu = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    _READER = easyocr.Reader(["sv", "en"], gpu=use_gpu, verbose=False)
    if progress_cb:
        progress_cb("loading_model", 0.35)
    return _READER


def ocr_image_easyocr(image_path: str, progress_cb=None) -> dict:
    """Return {"text": str, "boxes": [{text, x, y, w, h}]} with coordinates normalised to 0–1."""
    def _cb(stage, frac):
        if progress_cb:
            progress_cb(stage, frac)

    reader = _load_reader(progress_cb=progress_cb)
    _cb("ocr", 0.40)

    # readtext returns (bbox, text, conf); bbox is four corner points in pixels
    from PIL import Image
    with Image.open(image_path) as im:
        iw, ih = im.size
    results = reader.readtext(image_path, detail=1, paragraph=False)
    _cb("ocr", 0.90)

    lines = []
    boxes = []
    # Reading order: top to bottom, then left to right
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
