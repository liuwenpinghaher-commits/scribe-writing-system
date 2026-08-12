# craft-loop PASS · 20260812-book_qe_live5（序贯复验）

## 结论

**`craft_loop_mvp_pass: true`**

本文件对应 **有序** CL-B0→B6 复验（各块 `timeline.json.evaluated_at` **互不相同**；B1 green 后才进 B2）。

| 块 | verdict | evaluated_at |
|----|---------|--------------|
| CL-B0 | green | 2026-08-12T10:48:32.119882+00:00 |
| CL-B1 | green | 2026-08-12T10:48:38.320712+00:00 |
| CL-B2 red | red (H1) | 2026-08-12T10:48:41.590480+00:00 · synopsis_cn=21 |
| CL-B2 green | green | 2026-08-12T10:48:44.768888+00:00 · synopsis_cn=99 |
| CL-B3 | green | 2026-08-12T10:48:46.498853+00:00 |
| CL-B4 | green | 2026-08-12T10:48:48.881063+00:00 |
| CL-B5 | green | 2026-08-12T10:48:54.684076+00:00 · prose_cn=1823 |
| CL-B6 | green | 2026-08-12T10:48:57.070646+00:00 |

## 合法通道 HTTP 证据（非 claim-only）

| 通道 | 调用 | 产物 |
|------|------|------|
| 工程配额 | PUT /api/intent-goals | `block-CL-B0/machine/http-intent-goals.*` |
| world_write+approve | POST /orchestration/proposal/apply（短纲 red） | `block-CL-B2/machine/http-orch-apply-short-synopsis.*` |
| world_write+approve | POST /orchestration/proposal/apply（长纲 green） | `block-CL-B2/machine/http-orch-apply-long-synopsis.*` |
| prose 手稿 | POST /api/save-chapter | `block-CL-B5/machine/http-save-chapter.*` |
| 索引 | 全部调用 | `http-transcripts-index.json` · `craft-loop-full-run.md` |

## CL-B2 red→green（有 before 态）

1. 故意 orch 写入 synopsis cn_len=**21** → `machine/chapter-red.json` + `eval-red.json`
2. craft-loop H1 FAIL（即使 gate_b 可能仍 ok）
3. orch 写入 synopsis cn_len=**99** → `machine/chapter-green.json` + `eval-green.json`

## 三行 disclaimer

```text
1. craft-loop PASS ≠ 50k-e2e PASS
2. craft-loop PASS ≠ v6.3.4 体验总 PASS
3. gate_*.ok ≠ craft-loop 块 hard 自动绿
```

## author_human

`false` — 认证 HTTP 合法通道；无 Playwright SPA 截图；人 hard 行写在各块 verdict.md。
