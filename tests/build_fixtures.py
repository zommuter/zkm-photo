"""Generate synthetic JPEG test fixtures with crafted EXIF data.

Run once (needs Pillow):
    uv run --extra dev python tests/build_fixtures.py

Commits the binary .jpg files so tests don't need Pillow at runtime.
"""

from __future__ import annotations

import io
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


def _gps_ifd_signed(lat_deg: float, lon_deg: float) -> dict:
    """GPS IFD honouring hemisphere refs (S/W for negative values)."""
    def to_dms(val: float):
        val = abs(val)
        d = int(val)
        m = int((val - d) * 60)
        s = round(((val - d) * 60 - m) * 60 * 1000)
        return ((d, 1), (m, 1), (s, 1000))

    return {
        piexif.GPSIFD.GPSLatitudeRef: b"S" if lat_deg < 0 else b"N",
        piexif.GPSIFD.GPSLatitude: to_dms(lat_deg),
        piexif.GPSIFD.GPSLongitudeRef: b"W" if lon_deg < 0 else b"E",
        piexif.GPSIFD.GPSLongitude: to_dms(lon_deg),
    }


# Fixture 4: Southern/western hemisphere GPS (Buenos Aires)
exif4 = {
    "0th": {piexif.ImageIFD.Model: b"Pixel 8"},
    "Exif": {piexif.ExifIFD.DateTimeOriginal: b"2022:01:05 10:00:00"},
    "GPS": _gps_ifd_signed(-34.6037, -58.3816),
    "1st": {},
}
(FIXTURES / "gps_sw_2022.jpg").write_bytes(_make_jpeg(size=(10, 8), exif_dict=exif4))
print("Written: gps_sw_2022.jpg")

# Fixture 5: DateTimeDigitized only (no DateTimeOriginal) — fallback-chain step 2
exif5 = {
    "0th": {},
    "Exif": {piexif.ExifIFD.DateTimeDigitized: b"2021:06:01 08:00:00"},
    "GPS": {},
    "1st": {},
}
(FIXTURES / "digitized_2021.jpg").write_bytes(_make_jpeg(size=(10, 8), exif_dict=exif5))
print("Written: digitized_2021.jpg")

# Fixture 6: Corrupt EXIF — garbage APP1 segment spliced after SOI
plain = _make_jpeg(size=(10, 8))
corrupt = plain[:2] + b"\xff\xe1\x00\x10Exif\x00\x00GARBAGE!" + plain[2:]
(FIXTURES / "corrupt_exif.jpg").write_bytes(corrupt)
print("Written: corrupt_exif.jpg")

# Fixture 7: DateTimeOriginal + OffsetTimeOriginal (tz-aware capture, roadmap:33e5)
exif7 = {
    "0th": {piexif.ImageIFD.Model: b"Canon EOS R5"},
    "Exif": {
        piexif.ExifIFD.DateTimeOriginal: b"2024:08:15 12:30:00",
        piexif.ExifIFD.OffsetTimeOriginal: b"+02:00",
    },
    "GPS": {},
    "1st": {},
}
(FIXTURES / "offset_2024.jpg").write_bytes(_make_jpeg(size=(10, 8), exif_dict=exif7))
print("Written: offset_2024.jpg")

# Fixture 8: PNG, 12×9, no eXIf chunk (roadmap:8643)
img_png = Image.new("RGB", (12, 9), color=(1, 2, 3))
buf = io.BytesIO()
img_png.save(buf, format="PNG")
(FIXTURES / "photo.png").write_bytes(buf.getvalue())
print("Written: photo.png")

# Fixture 9: TIFF with DateTime + Model baseline tags (roadmap:62ea)
img_tif = Image.new("RGB", (16, 12), color=(5, 5, 5))
buf = io.BytesIO()
img_tif.save(
    buf, format="TIFF",
    tiffinfo={306: "2020:05:01 09:00:00", 272: "HP ScanJet"},  # 306=DateTime, 272=Model
)
(FIXTURES / "scan_2020.tif").write_bytes(buf.getvalue())
print("Written: scan_2020.tif")

# Fixture 10: HEIC placeholder — valid ftyp box only, no image payload (roadmap:4514).
# exifread recognizes the brand but finds no EXIF; _parse_exif must degrade to {}.
fake_heic = (24).to_bytes(4, "big") + b"ftypheic" + b"\x00" * 12
(FIXTURES / "fake.heic").write_bytes(fake_heic)
print("Written: fake.heic")

print("Done.")
