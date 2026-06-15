"""Spec tests for non-JPEG format ingestion — roadmap:8643 (PNG),
roadmap:62ea (TIFF), roadmap:4514 (HEIC).

These tests are the executable specification: they were written RED at
handoff and define done for their roadmap items. Date assertions use
startswith so roadmap:33e5 (tz suffix) does not interact.
"""

from __future__ import annotations

import os
import shutil

import frontmatter

from conftest import FIXTURES, cfg
from zkm_photo.convert import convert

PNG = FIXTURES / "photo.png"          # 12×9, no eXIf chunk
TIFF = FIXTURES / "scan_2020.tif"     # 16×12, DateTime + Model tags
HEIC = FIXTURES / "fake.heic"         # placeholder: valid ftyp box, no payload

MTIME_2023 = 1_700_000_000  # 2023-11-14


# ── PNG ── roadmap:8643 ───────────────────────────────────────────────────────

def test_png_ingested_with_ihdr_dimensions(store, src):
    # roadmap:8643
    dest = src / "photo.png"
    shutil.copy(PNG, dest)
    os.utime(dest, (MTIME_2023, MTIME_2023))
    created = convert(store, cfg(src))
    assert len(created) == 1
    md = created[0]
    post = frontmatter.load(md)
    # Dimensions from the PNG IHDR chunk (no EXIF present in this fixture)
    assert post.metadata["width"] == 12
    assert post.metadata["height"] == 9
    # No EXIF date → mtime fallback
    assert post.metadata["date"].startswith("2023-")
    # Full object-storage path: CAS object + canonical inbox symlink
    assert post.metadata["original"].startswith("originals/photos/_objects/")
    cas_files = [f for f in (store / "originals" / "photos" / "_objects").rglob("*") if f.is_file()]
    assert len(cas_files) == 1
    # Symlinks are date-sharded (roadmap:a112) — use rglob.
    symlinks = [f for f in (store / "inbox" / "photos").rglob("*") if f.is_symlink()]
    assert len(symlinks) == 1


def test_png_dedup_on_second_run(store, src):
    # roadmap:8643
    shutil.copy(PNG, src / "photo.png")
    first = convert(store, cfg(src))
    assert len(first) == 1
    second = convert(store, cfg(src))
    assert second == []


# ── TIFF ── roadmap:62ea ──────────────────────────────────────────────────────

def test_tiff_ingested_with_exif_metadata(store, src):
    # roadmap:62ea
    shutil.copy(TIFF, src / "scan_2020.tif")
    created = convert(store, cfg(src))
    assert len(created) == 1
    post = frontmatter.load(created[0])
    # exifread parses TIFF natively: Image DateTime is step 3 of the date chain
    assert post.metadata["date"].startswith("2020-05-01T09:00:00")
    assert post.metadata["camera"] == "HP ScanJet"
    assert post.metadata["width"] == 16
    assert post.metadata["height"] == 12
    # md lands under the EXIF date, not the run date
    assert created[0].parts[-3:-1] == ("2020", "05")


# ── HEIC ── roadmap:4514 ──────────────────────────────────────────────────────

def test_heic_ingested_with_mtime_fallback(store, src):
    # roadmap:4514
    # Placeholder HEIC (ftyp box only): EXIF parse must degrade gracefully
    # to {} and the file must still be ingested with an mtime date.
    dest = src / "img_1234.heic"
    shutil.copy(HEIC, dest)
    os.utime(dest, (MTIME_2023, MTIME_2023))
    created = convert(store, cfg(src))
    assert len(created) == 1
    post = frontmatter.load(created[0])
    assert post.metadata["date"].startswith("2023-")
    assert post.metadata["original"].startswith("originals/photos/_objects/")
    assert "width" not in post.metadata  # nothing parseable from the placeholder
