# Relay log <!-- merge=union; append-only — never edit or reorder past entries -->

## 2026-06-13 — executor (claude-sonnet-4-6)

Worked id:8643/62ea/4514/33e5 — all four ROUTINE items in one session.
Format ingestion (8643/62ea/4514): added .png/.tif/.tiff/.heic to SUFFIXES;
PNG gets IHDR dimension read via stdlib struct (no Pillow); TIFF uses existing
exifread chain unchanged; HEIC graceful-degrades via the existing except-clause.
Timezone dates (33e5): _exif_date_to_iso() now takes an optional offset arg;
_parse_exif() reads paired OffsetTime* tags; without them, wall-clock is
assumed system local tz so every emitted date passes conformance; both plugin.yaml
copies gain a conformance block for `zkm test photo`. 22/22 tests green, ruff clean.
Friction: uv sync fails in worktrees (../.. resolves outside the project tree);
worked around by running pytest with the main-checkout venv + PYTHONPATH=src.

## 2026-06-12 22:03 — reviewer (claude-fable-5)

Handoff: suite was UNCOLLECTABLE at HEAD (SB5 import + M2 config drift) — repaired pre-C1, plus green guards (S/W GPS, DateTimeDigitized fallback, corrupt EXIF). First CLAUDE.md + ARCHITECTURE.md (D1-D10 incl. flat inbox/photos deviation). ROADMAP 4 ROUTINE (8643 PNG, 62ea TIFF, 4514 HEIC, 33e5 tz-aware dates — naive EXIF dates fail core conformance) + 3 Phase-3-gated HARD (thumbnails, OCR, reverse-geocode). 8 red specs, 14 green; uv.lock now committed; @manual Gherkin; 5 REVIEW_ME (assume-local-tz policy is the big one).

## 2026-06-13 10:14 — executor (sonnet, relay-loop)

All 4 ROUTINE items done: PNG/TIFF/HEIC ingestion + tz-aware EXIF dates; 22/22 tests green

## 2026-06-13 15:09 — reviewer (claude-opus-4-8, fable-standin, relay-loop)

review 20260613-1450: audited b19c8e1 (docs-only owner decision) clean, 22/22 green; reopened 33e5 per-photo DST safeguard as id:b045; refreshed contract pointer v1→v2 + ARCHITECTURE D6 + README/TODO drift

## 2026-06-13 — executor (claude-sonnet-4-6)

Worked id:b045 — DST-correct per-photo local offset for offset-less EXIF dates.
Added `_local_zoneinfo()` helper that resolves the system IANA zone via TZ env var or /etc/localtime symlink, then falls back to the pre-b045 fixed-offset behaviour.
`_exif_date_to_iso` now uses the photo's own naive datetime with the ZoneInfo object (not `datetime.now()`) so a Jan capture gets +01:00 and Jul gets +02:00 under Europe/Zurich.
Added `test_offset_less_exif_date_uses_dst_correct_local_offset` (roadmap:b045) pinning TZ=Europe/Zurich and asserting both offsets. 23/23 tests green, ruff clean.
Friction: uv sync still fails in worktrees (../.. path); same workaround (main-checkout venv + PYTHONPATH=src).
