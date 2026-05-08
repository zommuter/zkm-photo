"""Generate synthetic JPEG test fixtures with crafted EXIF data.

Run once (needs Pillow):
    uv run --extra dev python tests/build_fixtures.py

Commits the binary .jpg files so tests don't need Pillow at runtime.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image
import piexif

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)


def _make_jpeg(
    *,
    size: tuple[int, int] = (8, 6),
    color: tuple[int, int, int] = (128, 128, 128),
    exif_dict: dict | None = None,
) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    if exif_dict is not None:
        exif_bytes = piexif.dump(exif_dict)
        img.save(buf, format="JPEG", exif=exif_bytes)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _gps_ifd(lat_deg: float, lon_deg: float) -> dict:
    def to_dms(val: float):
        val = abs(val)
        d = int(val)
        m = int((val - d) * 60)
        s = round(((val - d) * 60 - m) * 60 * 1000)
        return ((d, 1), (m, 1), (s, 1000))

    return {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: to_dms(lat_deg),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: to_dms(lon_deg),
    }


# Fixture 1: Full EXIF — DateTimeOriginal, GPS (Zürich), Model, Width, Height
exif1 = {
    "0th": {
        piexif.ImageIFD.Make: b"Canon",
        piexif.ImageIFD.Model: b"Canon EOS R5",
        piexif.ImageIFD.ImageWidth: 100,
        piexif.ImageIFD.ImageLength: 75,
    },
    "Exif": {
        piexif.ExifIFD.DateTimeOriginal: b"2024:08:15 12:30:00",
        piexif.ExifIFD.PixelXDimension: 100,
        piexif.ExifIFD.PixelYDimension: 75,
    },
    "GPS": _gps_ifd(47.376888, 8.541694),
    "1st": {},
}
(FIXTURES / "canon_2024.jpg").write_bytes(_make_jpeg(exif_dict=exif1))
print("Written: canon_2024.jpg")

# Fixture 2: DateTimeOriginal + Model but no GPS
exif2 = {
    "0th": {
        piexif.ImageIFD.Make: b"Sony",
        piexif.ImageIFD.Model: b"ILCE-7M4",
        piexif.ImageIFD.ImageWidth: 64,
        piexif.ImageIFD.ImageLength: 48,
    },
    "Exif": {
        piexif.ExifIFD.DateTimeOriginal: b"2023:03:10 09:15:00",
        piexif.ExifIFD.PixelXDimension: 64,
        piexif.ExifIFD.PixelYDimension: 48,
    },
    "GPS": {},
    "1st": {},
}
(FIXTURES / "nogps_2023.jpg").write_bytes(_make_jpeg(size=(64, 48), exif_dict=exif2))
print("Written: nogps_2023.jpg")

# Fixture 3: No DateTimeOriginal — date falls back to mtime
exif3 = {
    "0th": {
        piexif.ImageIFD.Make: b"Apple",
        piexif.ImageIFD.Model: b"iPhone 14 Pro",
    },
    "Exif": {},
    "GPS": {},
    "1st": {},
}
(FIXTURES / "nodate.jpg").write_bytes(_make_jpeg(size=(32, 24), exif_dict=exif3))
print("Written: nodate.jpg")

print("Done.")
