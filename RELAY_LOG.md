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

## 2026-06-13 15:33 — executor (sonnet, relay-loop)

feat(convert): DST-correct per-photo local offset for offset-less EXIF dates (id:b045) — 23/23 green

## 2026-06-13 23:31 — reviewer (claude-opus-4-8, fable-standin, relay-loop)

review zkm-photo: 1 commit audited clean (REVIEW_ME-only triage), 23 tests green, pruned 3 confirmed boxes, all 5 ROUTINE closed, routine_open=0

## 2026-06-15 11:04 — reviewer (claude-opus-4-8, fable-standin, relay-loop)

review 20260615-1104: audited e9ce00e (REVIEW_ME/ROADMAP triage only — no test/src changes; test-integrity audit trivially clean: 0 deleted, 0 weakened). 23 tests green + ruff clean. Reverse-handoff (§5b): user-added ROADMAP id:a112 (re-shard flat inbox/photos → date-sharded inbox/photos/YYYY/MM/, filed from REVIEW_ME D4) was an unqualified [ROUTINE] — mini-handoff done REUSING id:a112: added acceptance/done-check/context + a red spec test (test_convert_inbox_is_date_sharded, # roadmap:a112, confirmed RED against the flat impl). Spec-drift: refreshed CLAUDE.md relay-contract pointer v2→v3 (fables-executor → /relay executor); marked ARCHITECTURE.md D4 "re-shard scheduled (id:a112)". TODO summary 0→1 ROUTINE open. routine_open=1.

## 2026-06-15 11:33 — reviewer (claude-opus-4-8, fable-standin, relay-loop)

review zkm-photo 20260615-1104: 1 triage commit audited clean (no test/src changes), 23 green; mini-handoff qualified id:a112 (inbox re-shard) with red spec; contract pointer v2->v3; routine_open=1

## 2026-06-15 — executor (claude-sonnet-4-6)

Worked id:a112 — re-shard zkm-photo inbox from flat `inbox/photos/<name>` to date-sharded `inbox/photos/YYYY/MM/<name>`. Change: pass `inbox_dir / year / month` as `link_dir` to `symlink_with_sidecar` (core helper already supports arbitrary `link_dir` + calls `mkdir(parents=True)`; `build_canonical_index` already uses `rglob`). Updated 3 tests to use `rglob` instead of `iterdir` (test_convert_canonical_inbox_symlink, test_convert_multi_producer_sidecar, test_formats.py::test_png_ingested_with_ihdr_dimensions) and updated the multi-producer sidecar test to seed eml into the sharded dir. Updated README, feature file, ticked ROADMAP checkbox. 24/24 tests green, ruff clean.
Friction: uv sync still fails in worktrees (../.. path resolves outside project tree); same workaround (main-checkout venv + PYTHONPATH pointing at worktree src).

## 2026-06-15 18:51 — executor (sonnet, relay-loop)

feat(convert): re-shard inbox/photos from flat to date-sharded YYYY/MM layout (id:a112) — 24/24 green

## 2026-06-22 21:26 — maintenance (manual, uv.lock cascade)

uv.lock cascade refresh to zkm 0.16.0 — mechanical version-pin only (id:bae5), audit-exempt class (no code/spec change).

## 2026-06-23 15:39 — reconcile (human)

reconcile integrate: relay(review): refresh contract pointer v3->v4, sync stale TODO summary (a112 done)
