# Human review queue <!-- budget: 15 min -->

Judgment calls encoded in red tests — confirm or correct the interpretation.
Max ~10 open boxes; the reviewer prunes resolved ones each review turn.

- [ ] ARCHITECTURE.md D4 (no test) — zkm-photo creates FLAT inbox/photos/<name>
  symlinks while core docs/object-storage.md shows date-sharded
  inbox/<subdir>/YYYY/MM/ (zkm-eml's layout). Documented as an accepted
  deviation; one-time ack requested, or file a re-shard item.
