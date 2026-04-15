"""
ocr.py — Platform-adaptive OCR dispatcher.

macOS   → Apple Vision (pyobjc-framework-Vision) — inbyggt, gratis, sv-SE + en-US
Win/Lin → EasyOCR (easyocr, svenska+engelska) — gratis, hanterar åäö

Interface:
  is_image(path)               → bool
  ocr_image(path, progress_cb) → str
"""
from __future__ import annotations
import platform
from pathlib import Path

SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp", ".heic", ".heif"}


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_IMAGES


def ocr_image(image_path: str, progress_cb=None) -> dict:
    """
    Run OCR on an image file and return {"text": str, "boxes": [...]}.
    Uses Apple Vision on macOS, EasyOCR on Windows/Linux.
    progress_cb(stage: str, fraction: float) — optional progress callback.
    """
    system = platform.system()
    if system == "Darwin":
        from core.ocr_vision import ocr_image_vision
        return ocr_image_vision(image_path, progress_cb=progress_cb)
    else:
        from core.ocr_easyocr import ocr_image_easyocr
        return ocr_image_easyocr(image_path, progress_cb=progress_cb)
