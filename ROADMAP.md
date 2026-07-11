# Roadmap <!-- fables-turn roadmap v1 -->

Executor-facing task spec. Each item is sized for ONE Sonnet session. Items are
the single source of truth — TODO.md carries only a summary line. Executors tick
checkboxes; only the reviewer adds, removes, or re-scopes items.

All done-checks assume `uv sync --extra dev` ran and additionally require the
FULL suite green (`uv run pytest`) and `uv run ruff check` clean on touched files.

## Items

## Gated (Phase 3 — do not start before the gate opens)

- [ ] [INPUT — meeting] Thumbnail generation for md bodies <!-- id:8740 -->
  - **Why HARD**: gated on zkm Phase 3 (WebUI) — thumbnails only pay off with a
    rendering surface; needs an image-processing dep decision (Pillow runtime
    dep vs external tool) and a CAS-vs-derived-cache storage decision that
    interacts with core's derivable-data policy. Settled v0.1 scope explicitly
    deferred this (ARCHITECTURE.md D9).
  - **Acceptance**: deferred — re-scope when the Phase 3 gate (WebUI work
    started in zkm core) opens.

- [ ] [INPUT — meeting] OCR text extraction for photographed documents <!-- id:62cb -->
  - **Why HARD**: gated on zkm Phase 2.5+ amender infrastructure maturity — OCR
    output belongs in frontmatter/extraction-cache via the amendment contract
    (md body is single-producer), not in the converter; engine choice
    (tesseract subprocess vs ML) and quality gating are open design questions.
  - **Acceptance**: deferred — re-scope as an amender plugin item when picked up.

- [ ] [INPUT — meeting] GPS reverse geocoding (place names from coordinates) <!-- id:a711 -->
  - **Why HARD**: gated on Phase 3 — converters MUST NOT make network calls
    (plugin spec), so this needs either an offline dataset decision or a
    query-time/amender design; also interacts with the γ typed-slot entity
    schema (`scope:place` entities) rather than plain frontmatter.
  - **Acceptance**: deferred — keep `location` as raw decimal degrees
    (ARCHITECTURE.md D7) until then.
