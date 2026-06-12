# zkm-photo architecture

Design decisions with rationale and rejected alternatives. Scope decisions
below are settled — document, don't re-litigate.

## Pipeline

```
source_dir (read-only scan)
  → sha256 dedup against existing photos/**/*.md frontmatter
  → EXIF parse (exifread)
  → raw bytes → CAS (originals/photos/_objects/<aa>/<rest>)
  → canonical symlink + .origin.json sidecar (inbox/photos/)
  → photos/YYYY/MM/<date>_<slug>.md (frontmatter + image link body)
```

## Decisions

### D1 — JPEG-only v0.1 scope (2025, Session 11; settled)
v0.1 ingests `.jpg`/`.jpeg` only. PNG/TIFF/HEIC are sized roadmap items
(roadmap:8643/62ea/4514), not scope creep to fold in casually.
**Rejected:** "support everything Pillow opens" — pulls in a hard Pillow
runtime dep and an unbounded format matrix for no v1 user need.

### D2 — exifread, pure Python (settled)
EXIF via `exifread` (no subprocess, no compiled dep). Since 3.x it also covers
TIFF/PNG-eXIf/HEIC/WebP, which the format roadmap items reuse.
**Rejected:** `exiftool` subprocess (heavy external binary, parsing its text
output); Pillow EXIF (compiled dep, weaker tag coverage for GPS/offset tags).

### D3 — Object storage delegated to zkm core (settled)
CAS writes, sha256, atomic writes, canonical-symlink + multi-producer sidecar
protocol all come from `zkm.cas` / `zkm.hashing` / `zkm.atomic` / `zkm.inbox`.
One implementation of the spec (core `docs/object-storage.md`); the
multi-producer invariant (a JPEG deposited by `zkm-eml` gains a second
`producers[]` entry, never a second symlink or CAS copy) is core-tested and
re-asserted here in `test_convert_multi_producer_sidecar`.
**Rejected:** plugin-local copies of these helpers (the pre-object-storage
pattern; drifted implementations were the motivation for the core library).

### D4 — Flat `inbox/photos/<name>` symlinks (accepted deviation)
Core's object-storage doc shows date-sharded `inbox/<subdir>/YYYY/MM/` links
(zkm-eml does this). zkm-photo links flat under `inbox/photos/` because photo
filenames are user-meaningful and the md tree already date-shards. Dedup is
unaffected (`build_canonical_index` rglobs). Revisit only if `inbox/photos/`
grows past a few thousand entries; flagged in REVIEW_ME.md once for human ack.

### D5 — Dedup by rescanning md frontmatter, no state file (settled)
`_scan_existing_shas` reads `sha256:` from every `photos/**/*.md` at startup.
The markdown tree is the single source of truth (core principle); a separate
seen-shas DB could drift from it and complicates disaster recovery
(core `docs/restore.md` re-derives everything from md + originals).
**Rejected:** sidecar state DB / journal — O(n) rescan is fine at photo-library
scale, and correctness beats speed here.

### D6 — Date precedence chain (settled, one known gap)
`DateTimeOriginal` → `DateTimeDigitized` → `Image DateTime` → file mtime.
Capture time beats digitization time beats file-system accident. mtime fallback
is tz-aware (local zone); EXIF values are currently emitted naive, which fails
core conformance — fix specced as roadmap:33e5 (use `OffsetTimeOriginal` family
when present, else assume local zone, matching the mtime path).

### D7 — GPS as raw decimal `"lat,lon"`, no reverse geocoding (settled)
Signed decimal degrees, 6 dp (S/W hemispheres negative). Reverse geocoding
needs either a network call (forbidden in converters by the plugin spec) or a
bundled offline dataset — Phase 3, gated (roadmap:a711).

### D8 — md path scheme `photos/YYYY/MM/<YYYY-MM-DD>_<slug>.md` (settled)
Human-readable filenames, no hashes (core convention). Slug from the source
stem; date+slug collisions get `_1`, `_2`… suffixes (distinct content with the
same name must not be dropped). sha256 in frontmatter is the identity; the
filename is only navigation.

### D9 — `tags: []` placeholder, no analysis in the converter (settled)
The converter does mechanical extraction only. Thumbnails (roadmap:8740), OCR
(roadmap:62cb), face/scene tagging are Phase 3 amender/enricher territory per
core's amendment contract (frontmatter is multi-producer; md body is
single-producer).

### D10 — Dual discovery packaging (SB5, settled)
Implementation lives in `src/zkm_photo/` (wheel: entry point
`zkm.plugins:photo = zkm_photo`); root `convert.py` is a re-export shim for
filesystem discovery. Manifest duplicated at root and in the package — keep
identical. **Rejected:** symlinking the manifest (wheel builds and Windows
checkouts both dislike it).
