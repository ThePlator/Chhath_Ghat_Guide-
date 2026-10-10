"""Prepare photos before they reach the model (LLD §3.2).

Fixes rotation, strips all metadata (phone photos carry GPS in EXIF),
shrinks the long side and re-encodes as JPEG.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_INPUT_PIXELS = 40_000_000  # decompression-bomb guard (~40 MP)


class ImageError(ValueError):
    pass


def prepare_image(raw: bytes, max_px: int = 1024, quality: int = 85) -> bytes:
    if not raw:
        raise ImageError("empty image")
    try:
        im = Image.open(BytesIO(raw))
        w, h = im.size
        if w * h > MAX_INPUT_PIXELS:
            raise ImageError(f"image too large ({w}x{h})")
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ImageError(f"could not open image: {e}") from e

    im.thumbnail((max_px, max_px), Image.LANCZOS)  # keeps aspect, never upsizes

    out = BytesIO()
    # No exif= / icc_profile= arguments, so no metadata is written.
    im.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()
