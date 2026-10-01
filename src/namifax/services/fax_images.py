"""The page images and the thumbnail of a stored fax: ``page<N>.png`` and ``thumb.png`` next to ``fax.tif``.

A fax that came in before its previews were made (or lost them) gets them from the TIFF when somebody looks at it.
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image

from namifax.common import settings

PREVIMG, PREVIMGSFX, THUMBNAIL, TIFFNAME = "page", ".png", "thumb.png", "fax.tif"


def page_path(folder: str, index: int) -> str:
    return os.path.join(folder, f"{PREVIMG}{index}{PREVIMGSFX}")


def _scaled(image: Image.Image, width: int) -> Image.Image:
    image = image.convert("L")
    if image.width > width:
        image = image.resize((width, max(1, round(image.height * width / image.width))))
    return image


def render_previews(folder: str) -> int:
    """Write ``page<N>.png`` for every page of fax.tif and ``thumb.png`` for the first one; returns the number of pages."""
    tiff = os.path.join(folder, TIFFNAME)
    if not os.path.isfile(tiff):
        return 0
    count = 0
    with Image.open(tiff) as img:
        for i in range(getattr(img, "n_frames", 1)):
            img.seek(i)
            page = _scaled(img, settings.number("PREV_SP", 750))
            page.save(page_path(folder, i), format="PNG")
            if i == 0:
                _scaled(img, settings.number("PREV_TN", 80)).save(os.path.join(folder, THUMBNAIL), format="PNG")
            count += 1
    return count


def ensure_page(folder: str, index: int) -> Optional[str]:
    """The path of page ``index`` (counted from 0), made from the TIFF when it does not exist; None if there is no such page."""
    if index < 0:
        return None
    path = page_path(folder, index)
    if not os.path.isfile(path):
        try:
            render_previews(folder)
        except Exception:
            return None
    return path if os.path.isfile(path) else None


def ensure_thumbnail(folder: str) -> Optional[str]:
    path = os.path.join(folder, THUMBNAIL)
    if not os.path.isfile(path):
        try:
            render_previews(folder)
        except Exception:
            return None
    return path if os.path.isfile(path) else None
