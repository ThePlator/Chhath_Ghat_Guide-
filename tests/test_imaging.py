from io import BytesIO

import pytest
from PIL import Image

from ghat_guide.imaging import ImageError, prepare_image

GPS_IFD = 0x8825
ORIENTATION = 0x0112


def _jpeg(size, *, orientation=None, gps=False) -> bytes:
    im = Image.new("RGB", size, "white")
    exif = Image.Exif()
    if orientation:
        exif[ORIENTATION] = orientation
    if gps:
        exif[GPS_IFD] = {1: "N", 2: (25.0, 36.0, 33.0), 3: "E", 4: (85.0, 8.0, 15.0)}
    buf = BytesIO()
    im.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def _open(b: bytes) -> Image.Image:
    return Image.open(BytesIO(b))


def test_resizes_long_side():
    out = _open(prepare_image(_jpeg((4000, 3000)), max_px=1024))
    assert max(out.size) == 1024
    assert out.size == (1024, 768)


def test_small_image_not_upscaled():
    out = _open(prepare_image(_jpeg((640, 480)), max_px=1024))
    assert out.size == (640, 480)


def test_exif_and_gps_stripped():
    src = _jpeg((800, 600), gps=True)
    assert GPS_IFD in _open(src).getexif()
    out = _open(prepare_image(src))
    assert len(out.getexif()) == 0
    assert "exif" not in out.info


def test_rotation_applied():
    # Orientation 6 = rotate 90° clockwise to display: 800x600 stored → 600x800 shown.
    out = _open(prepare_image(_jpeg((800, 600), orientation=6)))
    assert out.size == (600, 800)


def test_png_with_alpha_becomes_jpeg():
    buf = BytesIO()
    Image.new("RGBA", (300, 200), (255, 0, 0, 128)).save(buf, format="PNG")
    out = _open(prepare_image(buf.getvalue()))
    assert out.format == "JPEG" and out.mode == "RGB"


@pytest.mark.parametrize("raw", [b"", b"not an image", b"\xff\xd8\xff\x00broken"])
def test_bad_input_raises(raw):
    with pytest.raises(ImageError):
        prepare_image(raw)
