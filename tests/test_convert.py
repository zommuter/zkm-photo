"""Tests for zkm-photo convert.py."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import frontmatter
import pytest

from convert import PLUGIN_NAME, PLUGIN_VERSION, convert

FIXTURES = Path(__file__).parent / "fixtures"
CANON = FIXTURES / "canon_2024.jpg"
NOGPS = FIXTURES / "nogps_2023.jpg"
NODATE = FIXTURES / "nodate.jpg"


@pytest.fixture
def store(tmp_path: Path) -> Path:
    """Minimal zkm store skeleton."""
    s = tmp_path / "store"
    (s / "photos").mkdir(parents=True)
    (s / "inbox").mkdir()
    (s / "originals" / "photos").mkdir(parents=True)
    import subprocess
    subprocess.run(["git", "init", "-q", str(s)], check=True)
    return s


@pytest.fixture
def src(tmp_path: Path) -> Path:
    """Clean PHOTO_SOURCE_DIR."""
    d = tmp_path / "photos_src"
    d.mkdir()
    return d


def cfg(src: Path) -> dict:
    return {"PHOTO_SOURCE_DIR": str(src)}


# ── 1. Happy path ─────────────────────────────────────────────────────────────

def test_convert_creates_md_with_frontmatter(store, src):
    shutil.copy(CANON, src / "canon_2024.jpg")
    created = convert(store, cfg(src))
    assert len(created) == 1
    md = created[0]
    assert md.exists()
    # path structure: photos/YYYY/MM/<date>_<slug>.md
    assert md.parts[-4] == "photos"
    assert md.parts[-3] == "2024"
    assert md.parts[-2] == "08"
    post = frontmatter.load(md)
    assert post.metadata["source"] == PLUGIN_NAME
    assert post.metadata["processor_version"] == PLUGIN_VERSION
    assert post.metadata["date"] == "2024-08-15T12:30:00"
    assert post.metadata["tags"] == []
    assert isinstance(post.metadata["sha256"], str) and len(post.metadata["sha256"]) == 64
    assert post.metadata["original"].startswith("originals/photos/_objects/")
    assert post.metadata["camera"] == "Canon EOS R5"
    assert post.metadata["location"] == "47.376888,8.541694"
    assert post.metadata["width"] == 100
    assert post.metadata["height"] == 75
    # body contains markdown image link
    assert "![" in post.content


# ── 2. Idempotency ────────────────────────────────────────────────────────────

def test_convert_idempotent(store, src):
    shutil.copy(CANON, src / "canon_2024.jpg")
    first = convert(store, cfg(src))
    assert len(first) == 1

    # Count CAS objects and sidecar producers before second run
    cas_dir = store / "originals" / "photos" / "_objects"
    cas_count_before = sum(1 for _ in cas_dir.rglob("*") if _.is_file())
    sidecar = next((store / "inbox" / "photos").rglob("*.origin.json"))
    producers_before = json.loads(sidecar.read_text())["producers"]

    second = convert(store, cfg(src))
    assert second == []
    # No new CAS objects
    cas_count_after = sum(1 for _ in cas_dir.rglob("*") if _.is_file())
    assert cas_count_after == cas_count_before
    # Producer list unchanged
    producers_after = json.loads(sidecar.read_text())["producers"]
    assert len(producers_after) == len(producers_before)


# ── 3. SHA-256 dedup across source paths ──────────────────────────────────────

def test_convert_dedup_by_sha256(store, src):
    """Two source files with identical bytes → one md, one CAS object."""
    shutil.copy(CANON, src / "copy_a.jpg")
    shutil.copy(CANON, src / "copy_b.jpg")
    created = convert(store, cfg(src))
    assert len(created) == 1
    cas_files = list((store / "originals" / "photos" / "_objects").rglob("*"))
    assert sum(1 for f in cas_files if f.is_file()) == 1


# ── 4. mtime fallback when DateTimeOriginal is absent ─────────────────────────

def test_convert_no_exif_date_falls_back_to_mtime(store, src):
    dest = src / "nodate.jpg"
    shutil.copy(NODATE, dest)
    # Set a known mtime
    os.utime(dest, (1_700_000_000, 1_700_000_000))  # 2023-11-14T...
    created = convert(store, cfg(src))
    assert len(created) == 1
    post = frontmatter.load(created[0])
    # Date string must parse as ISO 8601 and match the mtime year
    date_str = post.metadata["date"]
    assert date_str.startswith("2023-")


# ── 5. Non-JPEG files are skipped ─────────────────────────────────────────────

def test_convert_skips_non_jpeg(store, src):
    shutil.copy(CANON, src / "photo.jpg")
    (src / "thumbnail.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (src / "readme.txt").write_text("ignore me")
    created = convert(store, cfg(src))
    assert len(created) == 1  # only the .jpg


# ── 6. Empty source → no-op ───────────────────────────────────────────────────

def test_convert_no_op_on_empty_source(store, src):
    created = convert(store, cfg(src))
    assert created == []


# ── 7. GPS decimal degrees ────────────────────────────────────────────────────

def test_convert_gps_decimal_degrees(store, src):
    shutil.copy(CANON, src / "canon.jpg")
    created = convert(store, cfg(src))
    post = frontmatter.load(created[0])
    loc = post.metadata["location"]
    # "lat,lon" with 6 decimal places
    assert re.match(r"^\d+\.\d+,\d+\.\d+$", loc)
    lat, lon = map(float, loc.split(","))
    assert abs(lat - 47.376888) < 0.001
    assert abs(lon - 8.541694) < 0.001


def test_convert_no_gps_field_when_absent(store, src):
    shutil.copy(NOGPS, src / "nogps.jpg")
    created = convert(store, cfg(src))
    post = frontmatter.load(created[0])
    assert "location" not in post.metadata


# ── 8. Path collision → _1 suffix ────────────────────────────────────────────

def test_convert_path_collision_suffix(store, src):
    """Two distinct JPEGs with the same date and slug get a _1 suffix on the second."""
    # Use NODATE fixtures (no DateTimeOriginal) so both fall back to mtime.
    # Give them the same mtime → same date prefix.
    # Name them so both slugify to the same string: "img-0042".
    nodate_bytes = NODATE.read_bytes()
    file_a = src / "img_0042.jpg"
    file_b = src / "img 0042.jpg"  # space → same slug "img-0042"
    file_a.write_bytes(nodate_bytes)
    # Different bytes for different sha256 (flip last byte so EXIF header intact)
    file_b.write_bytes(nodate_bytes[:-1] + bytes([nodate_bytes[-1] ^ 0x01]))
    mtime = 1_700_000_000
    os.utime(file_a, (mtime, mtime))
    os.utime(file_b, (mtime, mtime))
    created = convert(store, cfg(src))
    assert len(created) == 2
    names = {p.name for p in created}
    suffixed = [n for n in names if re.search(r"_\d+\.md$", n)]
    assert len(suffixed) == 1


# ── 9. Canonical inbox symlink ────────────────────────────────────────────────

def test_convert_canonical_inbox_symlink(store, src):
    shutil.copy(CANON, src / "canon.jpg")
    convert(store, cfg(src))
    inbox_photos = store / "inbox" / "photos"
    symlinks = [f for f in inbox_photos.iterdir() if f.is_symlink()]
    assert len(symlinks) == 1
    link = symlinks[0]
    target = Path(os.readlink(link))
    resolved = (link.parent / target).resolve()
    assert resolved.exists()
    # sidecar has producer entry
    sidecar_path = inbox_photos / (link.name + ".origin.json")
    assert sidecar_path.exists()
    data = json.loads(sidecar_path.read_text())
    assert any(p["plugin"] == PLUGIN_NAME for p in data["producers"])


# ── 10. Multi-producer sidecar ───────────────────────────────────────────────

def test_convert_multi_producer_sidecar(store, src):
    """A JPEG pre-seeded by zkm-eml gets a second producer entry from zkm-photo."""
    from zkm.cas import write_object
    from zkm.inbox import build_canonical_index, symlink_with_sidecar

    photo_bytes = CANON.read_bytes()
    # Simulate zkm-eml depositing the same bytes into CAS and inbox/photos
    cas_obj = write_object(store, "originals/photos", photo_bytes)
    inbox_dir = store / "inbox" / "photos"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    index: dict = {}
    # eml uses the *email message* sha256, not the attachment sha256 — they differ.
    eml_sha256 = "a" * 64
    symlink_with_sidecar(
        cas_object=cas_obj,
        link_dir=inbox_dir,
        link_name="canon_2024.jpg",
        producer={"plugin": "eml", "message": "mail/messages/2024-08-15_test.md", "sha256": eml_sha256},
        canonical_index=index,
    )
    assert len(list(inbox_dir.rglob("*.origin.json"))) == 1

    # Now run zkm-photo against the same file
    shutil.copy(CANON, src / "canon_2024.jpg")
    created = convert(store, cfg(src))
    assert len(created) == 1  # photo md is new

    # Sidecar now has 2 producers
    sidecar_path = next(inbox_dir.rglob("*.origin.json"))
    data = json.loads(sidecar_path.read_text())
    plugins = {p["plugin"] for p in data["producers"]}
    assert "eml" in plugins
    assert PLUGIN_NAME in plugins

    # Still only one symlink (canonical) and one CAS object
    symlinks = [f for f in inbox_dir.iterdir() if f.is_symlink()]
    assert len(symlinks) == 1
    cas_files = list((store / "originals" / "photos" / "_objects").rglob("*"))
    assert sum(1 for f in cas_files if f.is_file()) == 1
