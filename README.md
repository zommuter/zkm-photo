# zkm-photo

zkm plugin that imports JPEG photos into the knowledge store. EXIF metadata (date, GPS, camera model, dimensions) is parsed into frontmatter; the original bytes go into the content-addressed store; a symlink lands in `inbox/photos/` for other plugins.

**Repo**: `~/src/zkm-photo/`  
**Store dirs**: `photos/`, `originals/photos/`, `inbox/photos/`  
**Install**: `zkm plugin add ~/src/zkm-photo`

## What it does

For each `.jpg`/`.jpeg` file found under `PHOTO_SOURCE_DIR`:

1. Computes SHA-256; skips if already ingested (idempotent on re-run).
2. Stores raw bytes in CAS at `originals/photos/_objects/<aa>/<rest>`.
3. Creates/updates a canonical symlink at `inbox/photos/<filename>` with an `.origin.json` sidecar. Multi-producer aware: a JPEG already deposited by `zkm-eml` gets a second entry in `producers[]`, not a second symlink.
4. Writes `photos/YYYY/MM/<date>_<slug>.md` with frontmatter:

```yaml
source: photo
processor: photo
processor_version: 0.1.0
date: 2024-08-15T12:30:00
tags: []                         # placeholder — future amenders may extend
sha256: e5207343…
original: originals/photos/_objects/e5/207343…
camera: Canon EOS R5             # EXIF Image Model (optional)
location: 47.376888,8.541694     # GPS decimal degrees (optional, no reverse-geocode)
width: 4500                      # EXIF pixel dimensions (optional)
height: 3000
```

Body is a markdown image link pointing at the CAS object, plus a one-line EXIF summary.

## Scope (v0.1)

- Formats: `.jpg` / `.jpeg` only
- EXIF library: `exifread` (pure-Python, no subprocess)
- No thumbnail generation, no face detection, no OCR, no GPS reverse-geocoding (Phase 3)
- `tags: []` left empty as amendment placeholder; `camera` scalar carries raw model string

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `PHOTO_SOURCE_DIR` | yes | — | Directory scanned recursively for JPEGs (read-only) |

Set in `$ZKM_STORE/.env` or as an environment variable.

## Development

```bash
cd ~/src/zkm-photo
uv sync --extra dev
uv run pytest -q

# Wire into zkm and test:
cd ~/src/zkm
uv run zkm plugin add ~/src/zkm-photo
PHOTO_SOURCE_DIR=~/Pictures ZKM_STORE=~/knowledge uv run zkm convert photo
```

Note: `exifread` must also be installed in the zkm runtime environment. Add it to the shared venv if running through `zkm convert`.

## Tests

All test fixtures are **synthetic** — no real photos. Run `tests/build_fixtures.py` once (needs `Pillow` + `piexif`) to regenerate committed fixture files.

- `test_convert_creates_md_with_frontmatter` — full frontmatter + body check
- `test_convert_idempotent` — second run returns `[]`, CAS/sidecar unchanged
- `test_convert_dedup_by_sha256` — two copies of same file → one md + one CAS object
- `test_convert_no_exif_date_falls_back_to_mtime` — mtime used when DateTimeOriginal absent
- `test_convert_skips_non_jpeg` — `.png` and `.txt` ignored
- `test_convert_no_op_on_empty_source` — empty source dir returns `[]`
- `test_convert_gps_decimal_degrees` — GPS → `"lat,lon"` string, ±0.001° accuracy
- `test_convert_no_gps_field_when_absent` — no `location` key when EXIF GPS absent
- `test_convert_path_collision_suffix` — same date+slug → `_1` suffix on second file
- `test_convert_canonical_inbox_symlink` — symlink points at CAS, sidecar has `photo` producer
- `test_convert_multi_producer_sidecar` — JPEG pre-seeded by `zkm-eml` gains second producer entry
