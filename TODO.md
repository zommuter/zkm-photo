# zkm-photo TODO

This is the work ledger for zkm-photo (Option B, decided 2026-06-30 — `~/src/zkm/docs/meeting-notes/2026-06-30-1004-per-plugin-todo-topology-revisited.md`). Executor specs: `ROADMAP.md` (relay-managed). <!-- lint-ok: file-purpose preamble -->

## Current

- Relay: 3 open ROADMAP items (all gated [HARD — meeting], Phase 3); 6 ROUTINE done <!-- id:fb85 -->
- [x] **DST-safe EXIF TZ safeguard** — apply DST-safe EXIF TZ safeguard (resolve offset from IANA zone on the photo's own date, not `dt.astimezone()` current offset) + add Jan/Jul Europe/Zurich offset test (mirrors zkm-scan owner decision 2026-06-13). Shipped under ROADMAP id:b045 (NOT 33e5); verified green 2026-06-30 (5/5 timezone tests; Jan→+01:00 / Jul→+02:00). (was inbox routed:5a69 from zkm-scan) <!-- id:aaa3 -->
