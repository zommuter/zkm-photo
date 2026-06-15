"""zkm-photo — import JPEG/PNG/TIFF/HEIC photos into the knowledge store.

Walks PHOTO_SOURCE_DIR for image files, parses EXIF, writes
frontmatter markdown under photos/YYYY/MM/, stores raw bytes in CAS,
and registers an inbox symlink. Second run on the same source is a no-op.
"""

from __future__ import annotations

import os
import re
import struct
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import exifread
import frontmatter

from zkm.atomic import write_atomic
from zkm.cas import write_object
from zkm.hashing import sha256_file
from zkm.inbox import build_canonical_index, symlink_with_sidecar

PLUGIN_NAME = "photo"
PLUGIN_VERSION = "0.4.0"

SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic"}


def convert(store_path: Path, config: dict, *, progress=None) -> list[Path]:
    """Import JPEGs from PHOTO_SOURCE_DIR into store_path/photos/.

    Returns a list of paths to newly created .md files.
    progress: optional callback(current, total, message).
    """
    src = Path(config["source_dir"]).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"source_dir does not exist: {src}")

    photos_dir = store_path / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir = store_path / "inbox" / "photos"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (store_path / "originals" / "photos").mkdir(parents=True, exist_ok=True)

    existing_shas = _scan_existing_shas(photos_dir)
    canonical_index = build_canonical_index(store_path, "inbox/photos")

    candidates = [
        f for f in sorted(src.rglob("*"))
        if f.is_file() and f.suffix.lower() in SUFFIXES
    ]
    total = len(candidates)
    created: list[Path] = []

    for i, src_file in enumerate(candidates, 1):
        sha = sha256_file(src_file)
        if sha in existing_shas:
            if progress:
                progress(i, total, src_file.name)
            continue

        photo_bytes = src_file.read_bytes()
        exif = _parse_exif(src_file)
        date_str = exif.get("date") or _mtime_iso(src_file)
        date_prefix = date_str[:10]  # YYYY-MM-DD
        year, month = date_prefix[:4], date_prefix[5:7]

        cas_obj = write_object(store_path, "originals/photos", photo_bytes)
        original_rel = str(cas_obj.relative_to(store_path))

        inbox_shard_dir = inbox_dir / year / month
        symlink_with_sidecar(
            cas_object=cas_obj,
            link_dir=inbox_shard_dir,
            link_name=src_file.name.lower(),
            producer={"plugin": PLUGIN_NAME, "message": str(src_file), "sha256": sha},
            canonical_index=canonical_index,
        )

        md_dir = photos_dir / year / month
        md_dir.mkdir(parents=True, exist_ok=True)
        slug = _slugify(src_file.stem)
        out = _unique_path(md_dir, date_prefix, slug)

        meta: dict = {
            "source": PLUGIN_NAME,
            "processor": PLUGIN_NAME,
            "processor_version": PLUGIN_VERSION,
            "date": date_str,
            "tags": [],
            "sha256": sha,
            "original": original_rel,
        }
        if exif.get("camera"):
            meta["camera"] = exif["camera"]
        if exif.get("location"):
            meta["location"] = exif["location"]
        if exif.get("width"):
            meta["width"] = exif["width"]
        if exif.get("height"):
            meta["height"] = exif["height"]

        rel_original = os.path.relpath(cas_obj, out.parent)
        body_lines = [f"![{src_file.stem}]({rel_original})"]
        summary = _exif_summary(exif)
        if summary:
            body_lines.append("")
            body_lines.append(summary)
        body = "\n".join(body_lines) + "\n"

        write_atomic(out, frontmatter.dumps(frontmatter.Post(body, **meta)))
        created.append(out)
        existing_shas.add(sha)

        if progress:
            progress(i, total, src_file.name)

    return created


# ── EXIF helpers ──────────────────────────────────────────────────────────────

def _parse_exif(path: Path) -> dict:
    """Return a dict with keys: date, camera, location, width, height (all optional)."""
    result: dict = {}
    try:
        with path.open("rb") as fh:
            tags = exifread.process_file(fh, details=False)
    except Exception:
        tags = {}

    # Date: "YYYY:MM:DD HH:MM:SS" → ISO 8601 with timezone.
    # Offset tags are matched to the DateTime tag that was used.
    _date_offset_pairs = (
        ("EXIF DateTimeOriginal", "EXIF OffsetTimeOriginal"),
        ("EXIF DateTimeDigitized", "EXIF OffsetTimeDigitized"),
        ("Image DateTime", "EXIF OffsetTime"),
    )
    for dt_key, off_key in _date_offset_pairs:
        if dt_key in tags:
            offset_str = str(tags[off_key]).strip() if off_key in tags else None
            result["date"] = _exif_date_to_iso(str(tags[dt_key]), offset_str)
            break

    # Camera model
    if "Image Model" in tags:
        result["camera"] = str(tags["Image Model"]).strip()

    # GPS → decimal degrees
    loc = _parse_gps(tags)
    if loc:
        result["location"] = loc

    # Dimensions — EXIF tags first, then format-specific fallbacks
    for wkey in ("EXIF ExifImageWidth", "Image ImageWidth"):
        if wkey in tags:
            result["width"] = int(str(tags[wkey]))
            break
    for hkey in ("EXIF ExifImageLength", "Image ImageLength"):
        if hkey in tags:
            result["height"] = int(str(tags[hkey]))
            break

    # PNG: read IHDR chunk for dimensions when EXIF didn't supply them
    if path.suffix.lower() == ".png" and ("width" not in result or "height" not in result):
        dims = _png_ihdr_dimensions(path)
        if dims:
            result["width"], result["height"] = dims

    return result


def _png_ihdr_dimensions(path: Path) -> tuple[int, int] | None:
    """Read width and height from a PNG IHDR chunk (stdlib struct, no Pillow).

    PNG spec: 8-byte signature, then IHDR chunk: 4-byte length, 4-byte type
    (b'IHDR'), 4-byte big-endian width, 4-byte big-endian height.
    """
    try:
        with path.open("rb") as fh:
            header = fh.read(24)
        if len(header) < 24:
            return None
        # Bytes 0-7: PNG signature; 8-11: chunk length; 12-15: b'IHDR'
        if header[12:16] != b"IHDR":
            return None
        width = struct.unpack(">I", header[16:20])[0]
        height = struct.unpack(">I", header[20:24])[0]
        return width, height
    except Exception:
        return None


def _exif_date_to_iso(s: str, offset: str | None = None) -> str:
    """Convert "YYYY:MM:DD HH:MM:SS" to a tz-aware ISO 8601 string.

    If *offset* is provided (e.g. "+02:00"), it is appended directly.
    Otherwise the wall-clock time is interpreted as the system local timezone
    (same policy as _mtime_iso) so that the emitted date is always tz-aware.
    The offset is resolved from the photo's OWN date so that DST is correct
    per-photo (a Jan photo gets +01:00, a Jul photo +02:00 for Europe/Zurich).
    """
    s = s.strip()
    if not (len(s) >= 19 and s[4] == ":" and s[7] == ":"):
        return s  # unrecognised format — return as-is
    iso_base = f"{s[0:4]}-{s[5:7]}-{s[8:10]}T{s[11:19]}"
    if offset:
        return f"{iso_base}{offset}"
    # No EXIF offset tag — interpret wall-clock as local time, attach local offset.
    # Resolve the offset from the photo's own date (DST-correct) using the system
    # IANA zone rather than the current wall-clock offset.
    try:
        naive = datetime(
            int(s[0:4]), int(s[5:7]), int(s[8:10]),
            int(s[11:13]), int(s[14:16]), int(s[17:19]),
        )
        local_zone = _local_zoneinfo()
        aware = naive.replace(tzinfo=local_zone)
        return aware.isoformat(timespec="seconds")
    except (ValueError, OverflowError):
        return iso_base  # malformed — return without tz as last resort


def _local_zoneinfo() -> ZoneInfo | datetime.tzinfo:
    """Return a ZoneInfo for the system local IANA zone, enabling DST-correct offsets.

    Resolution order:
    1. TZ environment variable (IANA name, e.g. "Europe/Zurich")
    2. /etc/localtime symlink (Linux / macOS)
    3. Fallback: fixed offset from datetime.now() (pre-b045 behaviour)
    """
    # 1. TZ env var
    tz_env = os.environ.get("TZ")
    if tz_env:
        try:
            return ZoneInfo(tz_env)
        except (ZoneInfoNotFoundError, KeyError):
            pass
    # 2. /etc/localtime symlink
    try:
        link = os.readlink("/etc/localtime")
        key = link.split("zoneinfo/")[-1]
        return ZoneInfo(key)
    except (OSError, ZoneInfoNotFoundError, KeyError):
        pass
    # 3. Fallback to fixed local offset (original behaviour; no DST correction)
    return datetime.now(tz=UTC).astimezone().tzinfo


def _parse_gps(tags: dict) -> str | None:
    """Return "lat,lon" decimal string or None."""
    try:
        lat_ref = str(tags.get("GPS GPSLatitudeRef", "N"))
        lon_ref = str(tags.get("GPS GPSLongitudeRef", "E"))
        lat = _dms_to_decimal(tags["GPS GPSLatitude"].values, lat_ref)
        lon = _dms_to_decimal(tags["GPS GPSLongitude"].values, lon_ref)
        return f"{lat:.6f},{lon:.6f}"
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _dms_to_decimal(dms, ref: str) -> float:
    """Convert EXIF DMS ratios to a signed decimal degree float."""
    def to_float(r) -> float:
        return r.num / r.den if hasattr(r, "num") else float(r)

    deg = to_float(dms[0])
    min_ = to_float(dms[1])
    sec = to_float(dms[2])
    val = deg + min_ / 60.0 + sec / 3600.0
    if ref in ("S", "W"):
        val = -val
    return val


def _exif_summary(exif: dict) -> str:
    """One-line text summary of available EXIF fields for the md body."""
    parts = []
    if exif.get("camera"):
        parts.append(f"Camera: {exif['camera']}")
    if exif.get("location"):
        parts.append(f"GPS: {exif['location']}")
    if exif.get("width") and exif.get("height"):
        parts.append(f"{exif['width']}×{exif['height']}")
    return "  ".join(parts)


# ── Store helpers ─────────────────────────────────────────────────────────────

def _scan_existing_shas(directory: Path) -> set[str]:
    shas: set[str] = set()
    for md in directory.rglob("*.md"):
        try:
            post = frontmatter.load(md)
            sha = post.metadata.get("sha256")
            if isinstance(sha, str):
                shas.add(sha)
        except Exception:
            continue
    return shas


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).astimezone().isoformat(
        timespec="seconds"
    )


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "photo"


def _unique_path(directory: Path, date_prefix: str, slug: str) -> Path:
    candidate = directory / f"{date_prefix}_{slug}.md"
    i = 1
    while candidate.exists():
        candidate = directory / f"{date_prefix}_{slug}_{i}.md"
        i += 1
    return candidate
