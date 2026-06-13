# Human review queue <!-- budget: 15 min -->

Judgment calls encoded in red tests — confirm or correct the interpretation.
Max ~10 open boxes; the reviewer prunes resolved ones each review turn.

- [x] tests/test_formats.py::test_heic_ingested_with_mtime_fallback
  (roadmap:4514) — HEIC v1 is interpreted as "ingest with graceful EXIF
  degradation": the committed fixture is a placeholder ftyp box, so the unit
  test only proves the no-crash/mtime path. Real-camera HEIC EXIF extraction is
  deferred to the @manual BDD scenario (features/convert-photo.feature). Confirm
  that placeholder-grade coverage is acceptable for ticking the item.
  — confirmed by user 2026-06-13 (batch triage)

- [x] tests/test_formats.py::test_png_ingested_with_ihdr_dimensions
  (roadmap:8643) — PNG dimensions specced from stdlib IHDR parsing (no Pillow
  runtime dep) and date from mtime, since PNG eXIf chunks are rare. exifread is
  still attempted first, so an eXIf-bearing PNG would win — confirm that
  precedence.
  — confirmed by user 2026-06-13 (batch triage)

- [x] tests/test_convert.py::test_convert_skips_non_image (rescoped at handoff)
  — the old test asserted .png files are SKIPPED; ingesting them is now
  roadmap:8643, so the skip-assertion was narrowed to .gif/.txt. Confirm the
  scope flip from "JPEG-only forever" to "JPEG now, PNG/TIFF/HEIC as items".
  — confirmed by user 2026-06-13 (batch triage)

- [ ] ARCHITECTURE.md D4 (no test) — zkm-photo creates FLAT inbox/photos/<name>
  symlinks while core docs/object-storage.md shows date-sharded
  inbox/<subdir>/YYYY/MM/ (zkm-eml's layout). Documented as an accepted
  deviation; one-time ack requested, or file a re-shard item.
