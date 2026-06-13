# Roadmap <!-- fables-turn roadmap v1 -->

Executor-facing task spec. Each item is sized for ONE Sonnet session. Items are
the single source of truth — TODO.md carries only a summary line. Executors tick
checkboxes; only the reviewer adds, removes, or re-scopes items.

All done-checks assume `uv sync --extra dev` ran and additionally require the
FULL suite green (`uv run pytest`) and `uv run ruff check` clean on touched files.

## Items

- [x] Ingest PNG files (IHDR dimensions, mtime date fallback) [ROUTINE] <!-- id:8643 -->
  - **Acceptance**: `.png` files in `source_dir` are ingested like JPEGs (md +
    CAS object + canonical inbox symlink + sha256 dedup). `width`/`height` come
    from the PNG IHDR chunk (stdlib `struct`, big-endian uint32 at byte offsets
    16/20 — do NOT add a Pillow runtime dep). EXIF is still attempted via the
    existing `_parse_exif` (exifread reads PNG `eXIf` chunks); when absent —
    the normal case — date falls back to mtime. Non-image junk (`.gif`, `.txt`)
    stays skipped.
  - **Tests**: `tests/test_formats.py::test_png_ingested_with_ihdr_dimensions`,
    `::test_png_dedup_on_second_run` (`# roadmap:8643`) (currently RED)
  - **Done-check**: `uv run pytest tests/test_formats.py -k png`
  - **Context**: `src/zkm_photo/convert.py` (`SUFFIXES`, `_parse_exif`); add a
    per-format dimension fallback rather than special-casing inside the main
    loop. ARCHITECTURE.md D1/D2. Update README format list when done.

- [x] Ingest TIFF files (.tif/.tiff, native EXIF tags) [ROUTINE] <!-- id:62ea -->
  - **Acceptance**: `.tif`/`.tiff` files are ingested. exifread parses TIFF
    natively, so date (`Image DateTime` is step 3 of the existing fallback
    chain), camera (`Image Model`), and dimensions
    (`Image ImageWidth`/`ImageLength`) work through the existing `_parse_exif`
    unchanged — the work is the suffix routing plus verifying the chain.
  - **Tests**: `tests/test_formats.py::test_tiff_ingested_with_exif_metadata`
    (`# roadmap:62ea`) (currently RED)
  - **Done-check**: `uv run pytest tests/test_formats.py -k tiff`
  - **Context**: `src/zkm_photo/convert.py` (`SUFFIXES`). Fixture
    `tests/fixtures/scan_2020.tif` (16×12, DateTime 2020:05:01 09:00:00,
    Model "HP ScanJet"). Update README format list when done.

- [x] Ingest HEIC files with graceful EXIF degradation [ROUTINE] <!-- id:4514 -->
  - **Acceptance**: `.heic` files are ingested (md + CAS + symlink + dedup).
    EXIF is attempted via `_parse_exif` (exifread ≥3.5 has a HEIC box parser);
    any parse failure degrades to `{}` → mtime date, never a crash. The
    committed fixture is a placeholder (valid `ftyp heic` box, no image
    payload) — it exercises the graceful path; real-camera HEIC EXIF is
    covered by the `@manual` BDD scenario, not by unit fixtures.
  - **Tests**: `tests/test_formats.py::test_heic_ingested_with_mtime_fallback`
    (`# roadmap:4514`) (currently RED)
  - **Done-check**: `uv run pytest tests/test_formats.py -k heic`
  - **Context**: `src/zkm_photo/convert.py` (`SUFFIXES`); judgment call logged
    in REVIEW_ME.md. Update README format list when done.

- [x] Emit timezone-aware ISO 8601 dates + pass core frontmatter conformance [ROUTINE] <!-- id:33e5 -->
  - **Acceptance**: (1) When EXIF carries `OffsetTimeOriginal` /
    `OffsetTimeDigitized` / `OffsetTime` (matched to whichever DateTime tag was
    used), the emitted `date` carries that offset, e.g.
    `2024-08-15T12:30:00+02:00`. (2) Without an offset tag, the EXIF local
    time is assumed to be in the **system local timezone** (same policy as the
    existing mtime fallback) and emitted tz-aware. (3) Every emitted md passes
    `zkm.conformance.validate_frontmatter(meta, "photo")` with zero fails.
    (4) Both `plugin.yaml` copies (root and `src/zkm_photo/`) declare
    `conformance: {config: {source_dir: tests/fixtures}}` so `zkm test photo`
    runs the dynamic tier. Existing tests use `startswith` on dates and must
    stay green.
  - **Tests**: `tests/test_timezone_conformance.py` — 4 tests marked
    `# roadmap:33e5` (currently RED)
  - **Done-check**: `uv run pytest tests/test_timezone_conformance.py`
  - **Context**: `_exif_date_to_iso` / `_parse_exif` in
    `src/zkm_photo/convert.py`; core schema in zkm `src/zkm/conformance.py`
    (string dates need `T` + tz marker). ARCHITECTURE.md D6. The
    local-tz assumption is a judgment call — see REVIEW_ME.md before changing
    the policy.

- [x] Per-photo DST-correct local offset for offset-less EXIF dates [ROUTINE] <!-- id:b045 -->
  - **Why**: 33e5 shipped the assume-local-tz policy, but `_exif_date_to_iso`
    resolves the offset from `datetime.now().astimezone().tzinfo` — i.e. the
    offset *at processing time*, not at the photo's capture date. A winter photo
    ingested in summer is stamped `+02:00` instead of `+01:00`. Owner decision
    2026-06-13 (was REVIEW_ME 33e5): keep the local-TZ default, but resolve the
    offset from a named IANA zone applied to the photo's OWN date via `zoneinfo`,
    so DST is correct per-photo. Mirrors the identical safeguard on zkm-scan aae8.
  - **Acceptance**: offset-less EXIF dates attach the offset that the configured
    IANA zone had **on that photo's date** (not the current offset). Resolve the
    zone name from the system local zone (e.g. `Europe/Zurich`); apply it to the
    parsed naive datetime with `ZoneInfo`. A Jan capture → `+01:00`, a Jul
    capture → `+02:00` for `Europe/Zurich`. The Offset*-tag path (33e5) is
    unchanged; conformance stays green. Travelling-photo mismatch stays an
    accepted limitation until an Offset* tag or per-store tz is present.
  - **Tests**: add a Jan-vs-Jul DST assertion to
    `tests/test_timezone_conformance.py` (`# roadmap:b045`) — two offset-less
    fixtures (or one fixture with two patched dates) asserting `+01:00` / `+02:00`
    under a pinned `TZ=Europe/Zurich`. (currently RED)
  - **Done-check**: `uv run pytest tests/test_timezone_conformance.py`
  - **Context**: `_exif_date_to_iso` in `src/zkm_photo/convert.py` (line ~213,
    the `datetime.now(tz=UTC).astimezone().tzinfo` branch). ARCHITECTURE.md D6.

## Gated (Phase 3 — do not start before the gate opens)

- [ ] Thumbnail generation for md bodies [HARD — strong model] <!-- id:8740 -->
  - **Why HARD**: gated on zkm Phase 3 (WebUI) — thumbnails only pay off with a
    rendering surface; needs an image-processing dep decision (Pillow runtime
    dep vs external tool) and a CAS-vs-derived-cache storage decision that
    interacts with core's derivable-data policy. Settled v0.1 scope explicitly
    deferred this (ARCHITECTURE.md D9).
  - **Acceptance**: deferred — re-scope when the Phase 3 gate (WebUI work
    started in zkm core) opens.

- [ ] OCR text extraction for photographed documents [HARD — strong model] <!-- id:62cb -->
  - **Why HARD**: gated on zkm Phase 2.5+ amender infrastructure maturity — OCR
    output belongs in frontmatter/extraction-cache via the amendment contract
    (md body is single-producer), not in the converter; engine choice
    (tesseract subprocess vs ML) and quality gating are open design questions.
  - **Acceptance**: deferred — re-scope as an amender plugin item when picked up.

- [ ] GPS reverse geocoding (place names from coordinates) [HARD — strong model] <!-- id:a711 -->
  - **Why HARD**: gated on Phase 3 — converters MUST NOT make network calls
    (plugin spec), so this needs either an offline dataset decision or a
    query-time/amender design; also interacts with the γ typed-slot entity
    schema (`scope:place` entities) rather than plain frontmatter.
  - **Acceptance**: deferred — keep `location` as raw decimal degrees
    (ARCHITECTURE.md D7) until then.
