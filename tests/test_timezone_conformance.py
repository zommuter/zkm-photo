"""Spec tests for timezone-aware dates + core frontmatter conformance —
roadmap:33e5.

Written RED at handoff. Core's zkm.conformance.validate_frontmatter rejects
naive date strings ("not ISO 8601 with timezone"); zkm-photo currently emits
EXIF dates naive. Policy encoded here (see REVIEW_ME.md):
- EXIF Offset* tags win when present;
- otherwise the EXIF wall-clock time is assumed to be in the SYSTEM LOCAL
  timezone (the same policy the mtime fallback already uses).
"""

from __future__ import annotations

import shutil
from datetime import datetime

import frontmatter
import yaml

from conftest import FIXTURES, cfg
from zkm_photo.convert import convert

CANON = FIXTURES / "canon_2024.jpg"      # DateTimeOriginal, no Offset* tag
OFFSET = FIXTURES / "offset_2024.jpg"    # DateTimeOriginal + OffsetTimeOriginal +02:00

REPO_ROOT = FIXTURES.parent.parent


def _convert_one(store, src, fixture, name):
    shutil.copy(fixture, src / name)
    created = convert(store, cfg(src))
    assert len(created) == 1
    return frontmatter.load(created[0])


def test_offset_time_original_is_emitted(store, src):
    # roadmap:33e5
    post = _convert_one(store, src, OFFSET, "offset.jpg")
    assert post.metadata["date"] == "2024-08-15T12:30:00+02:00"


def test_exif_date_without_offset_gets_local_tz(store, src):
    # roadmap:33e5 — judgment call: assume system local tz (see REVIEW_ME.md)
    post = _convert_one(store, src, CANON, "canon.jpg")
    date_str = str(post.metadata["date"])
    parsed = datetime.fromisoformat(date_str)
    assert parsed.tzinfo is not None, f"date {date_str!r} is naive"
    # Wall-clock part is preserved — only the offset is added
    assert date_str.startswith("2024-08-15T12:30:00")


def test_frontmatter_passes_core_conformance(store, src):
    # roadmap:33e5
    from zkm.conformance import validate_frontmatter

    post = _convert_one(store, src, CANON, "canon.jpg")
    findings = validate_frontmatter(dict(post.metadata), "photo")
    fails = [f for f in findings if f.level == "fail"]
    assert fails == [], "\n".join(str(f) for f in fails)


def test_plugin_yaml_declares_conformance_fixtures():
    # roadmap:33e5 — enables the dynamic tier of `zkm test photo`
    for manifest in (REPO_ROOT / "plugin.yaml", REPO_ROOT / "src" / "zkm_photo" / "plugin.yaml"):
        data = yaml.safe_load(manifest.read_text())
        assert data.get("conformance"), f"{manifest} lacks a conformance block"
        source_dir = data["conformance"]["config"]["source_dir"]
        assert (REPO_ROOT / source_dir).is_dir(), f"{manifest}: {source_dir} not a dir"


# ── DST-correct per-photo offset (roadmap:b045) ───────────────────────────────

def test_offset_less_exif_date_uses_dst_correct_local_offset(monkeypatch):
    # roadmap:b045 — offset resolved from the photo's OWN date, not from now().
    # Pin the system zone to Europe/Zurich so the test is deterministic.
    from zkm_photo.convert import _exif_date_to_iso

    monkeypatch.setenv("TZ", "Europe/Zurich")

    # January capture: CET (+01:00)
    jan_str = _exif_date_to_iso("2024:01:15 12:00:00")
    assert jan_str.endswith("+01:00"), f"Jan date expected +01:00, got {jan_str!r}"

    # July capture: CEST (+02:00)
    jul_str = _exif_date_to_iso("2024:07:15 12:00:00")
    assert jul_str.endswith("+02:00"), f"Jul date expected +02:00, got {jul_str!r}"
