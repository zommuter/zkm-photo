# zkm-photo

[zkm](https://github.com/zommuter/zkm) plugin that imports photos into the knowledge store. EXIF metadata (date, GPS, camera model, dimensions) is parsed into frontmatter; the original bytes go into the content-addressed store; a symlink lands in `inbox/photos/` for other plugins.

**Store dirs**: `photos/`, `originals/photos/`, `inbox/photos/`

## What it does

For each `.jpg`/`.jpeg`/`.png`/`.tif`/`.tiff`/`.heic` file found under the configured `source_dir`:

1. Computes SHA-256; skips if already ingested (idempotent on re-run).
2. Stores raw bytes in CAS at `originals/photos/_objects/<aa>/<rest>`.
3. Creates/updates a canonical symlink at `inbox/photos/<filename>` with an `.origin.json` sidecar. Multi-producer aware: a JPEG already deposited by `zkm-eml` gets a second entry in `producers[]`, not a second symlink.
4. Writes `photos/YYYY/MM/<date>_<slug>.md` with frontmatter:

```yaml
source: photo
processor: photo
processor_version: <plugin semver>
date: 2024-08-15T12:30:00+02:00  # tz-aware: EXIF OffsetTime* or system local tz
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

- Formats: `.jpg` / `.jpeg` / `.png` (IHDR dimensions) / `.tif` / `.tiff` (TIFF EXIF) / `.heic` (graceful EXIF fallback)
- EXIF library: `exifread` (pure-Python, no subprocess)
- No thumbnail generation, no face detection, no OCR, no GPS reverse-geocoding (Phase 3)
- `tags: []` left empty as amendment placeholder; `camera` scalar carries raw model string

## Install

End users (released wheel, sealed uv env):

```bash
uv tool install zkm --with zkm-photo
```

Development (filesystem discovery — clone inside your zkm `plugins/` directory):

```bash
git clone https://github.com/zommuter/zkm-photo.git plugins/zkm-photo
```

## Configuration

Bare snake_case keys under the `photo:` section of `$ZKM_STORE/zkm-config.yaml`:

| Key | Required | Default | Description |
|---|---|---|---|
| `source_dir` | yes | — | Directory scanned recursively for images (read-only) |

## Development

```bash
cd plugins/zkm-photo
uv sync --extra dev
uv run pytest -q
```

Note: `exifread` must also be installed in the zkm runtime environment.

## Tests

All test fixtures are **synthetic** — no real photos. Run `tests/build_fixtures.py` (needs `Pillow` + `piexif`, included in the dev extra) to regenerate committed fixture files; the generator is deterministic.

`tests/test_convert.py` covers: full frontmatter + body shape, idempotent re-run
(CAS/sidecar unchanged), sha256 dedup across paths, the EXIF date fallback chain
(DateTimeOriginal → DateTimeDigitized → mtime), corrupt-EXIF graceful fallback,
GPS decimal degrees incl. southern/western hemispheres, date+slug collision
suffixing, the canonical inbox symlink, and multi-producer sidecars (a JPEG
pre-seeded by `zkm-eml` gains a second producer entry). Additional currently-RED
spec tests for open roadmap items live in `tests/test_*` files marked with
`# roadmap:<id>` comments — see `ROADMAP.md`.

## License

MIT — see [LICENSE](LICENSE)
