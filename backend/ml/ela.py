"""
Error Level Analysis (ELA) for image tamper hints (CASIA / ResNet pipeline).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def compute_ela(image_path: str, quality: int = 90, size: tuple = (224, 224)):
    from PIL import Image, ImageChops, ImageEnhance
    import tempfile
    import os

    original = Image.open(image_path).convert("RGB")
    tmp = tempfile.mktemp(suffix=".jpg")
    original.save(tmp, "JPEG", quality=quality)
    compressed = Image.open(tmp).convert("RGB")
    ela = ImageChops.difference(original, compressed)
    extrema = ela.getextrema()
    max_diff = max([ex[1] for ex in extrema]) or 1
    scale = 255.0 / max_diff
    from PIL import ImageEnhance

    ela = ImageEnhance.Brightness(ela).enhance(scale)
    os.remove(tmp)
    return ela.resize(size)


def save_ela_preview(
    image_path: str | Path,
    output_path: str | Path,
    quality: int = 90,
) -> Path:
    """Write ELA visualization to disk (uses ``compute_ela``)."""
    ela = compute_ela(str(image_path), quality=quality)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ela.save(str(out), format="PNG")
    return out.resolve()
