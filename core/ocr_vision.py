"""
ocr_vision.py — Apple Vision OCR backend (macOS only).

Requires: pyobjc-framework-Vision
Supports printed text and handwriting in Swedish and English.
"""
from __future__ import annotations
from pathlib import Path


def ocr_image_vision(image_path: str, progress_cb=None) -> dict:
    """
    Extract text from an image with Apple Vision (VNRecognizeTextRequest).
    Returns {"text": str, "boxes": [{"text", "x", "y", "w", "h"}]}, with box
    coordinates normalised to 0–1 and a top-left origin, as in CSS.
    """
    def _cb(stage: str, frac: float):
        if progress_cb:
            progress_cb(stage, frac)

    _cb("loading_model", 0.05)

    try:
        import Vision
        from Foundation import NSURL
    except ImportError:
        raise ImportError(
            "pyobjc-framework-Vision är inte installerat. "
            "Kör: pip install pyobjc-framework-Vision"
        )

    _cb("ocr", 0.10)

    url = NSURL.fileURLWithPath_(str(Path(image_path).resolve()))

    request = Vision.VNRecognizeTextRequest.alloc().init()
    # Accurate mode is required for handwriting
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    # No language correction: Vision would otherwise "correct" historical spellings and Latin
    request.setUsesLanguageCorrection_(False)
    request.setRecognitionLanguages_(["sv-SE", "en-US"])
    # Default is about 0.03; a lower threshold catches smaller text
    request.setMinimumTextHeight_(0.01)

    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, {})
    success, error = handler.performRequests_error_([request], None)

    if not success:
        raise RuntimeError(f"Apple Vision OCR misslyckades: {error}")

    _cb("ocr", 0.90)

    results = request.results() or []
    lines = []
    boxes = []
    for obs in results:
        candidates = obs.topCandidates_(1)
        if candidates and len(candidates) > 0:
            text = candidates[0].string()
            lines.append(text)
            try:
                bb = obs.boundingBox()
                # PyObjC CGRect: try attribute access first, fall back to tuple indexing
                try:
                    v_x = float(bb.origin.x)
                    v_y = float(bb.origin.y)
                    v_w = float(bb.size.width)
                    v_h = float(bb.size.height)
                except AttributeError:
                    # CGRect exposed as nested tuples: ((x, y), (w, h))
                    (v_x, v_y), (v_w, v_h) = bb
                # Vision uses bottom-left origin; convert to top-left (CSS) origin
                boxes.append({
                    "text": text,
                    "x": v_x,
                    "y": 1.0 - v_y - v_h,
                    "w": v_w,
                    "h": v_h,
                })
            except Exception:
                pass  # keep the text even if its box cannot be read

    _cb("done", 1.0)
    return {"text": "\n".join(lines), "boxes": boxes}
