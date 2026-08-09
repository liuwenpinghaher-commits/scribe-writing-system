# Demo arc smoke v2 (skeptic gaps closed)

## Work / seq
- work: `book_arc_smoke_demo`
- seq: `8`
- character: `role:弧测主角`

## Before → After (HTTP chapter-pulse severity)

| Phase | severity | degraded | notes |
|-------|----------|----------|-------|
| BEFORE | **decision** | None | `demo-chapter-pulse-before.json` |
| AFTER (×2 stable) | **decision** | None | `demo-chapter-pulse.json` / `-after.json` |

- AFTER must be **decision** with overdue + `s3_add_char_state` tool names.
- Brief AFTER has tools: **True**

## MCP write path (commit_if_approved auto-accept)
- `s3_set_char_anchors` → written
- `s3_add_char_state` change_type=belief lie_belief=**88** → written
- `s3_add_arc_beat` smoke_delete_me → written then `s3_delete_arc_beat` → gone
- HTTP GET `/char-states` shows lie_belief **88** in list

## Anchors
- URL-encoded GET `/char-anchors` → `demo-char-anchors.json` with **alignment** object

## Empty book
- book_arc_empty_smoke: info, no 未见跳变

## Raw log
See `demo-arc-write.log`.
