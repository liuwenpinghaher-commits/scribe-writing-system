# 00-author-path · v6.3.4 新章 6–10

- slug / 书名：`book_79c0d45e` / 炉灰记·v6.3.4·真chat全能力（续写未定稿壳）
- 作者是否真人坐浏览器：**否**（最高 engineering PARTIAL）
- 通道：discuss `GET /chat/stream`（`agentic=false`）→ MCP 同等 `POST /orchestration/proposal/apply` `execute=true`（`s3_patch_chapter_meta` GATE-B）→ prose `GET /chat/write` → `POST /save-chapter`
- 是否仅对话+白名单 UI：否。无 Playwright；点批走 HTTP apply；正文经 `/chat/write` SSE 取 `proposal.prose` 再存。
- 每章开写 chat：
  - ch6: s7-open-ch6
  - ch7: s7-open-ch7
  - ch8: s7-open-ch8
  - ch9: s7-open-ch9
  - ch10: s7-open-ch10
- 续写补字：ch6/ch7/ch8 各一次 `续写` discuss + `/chat/write`，与前文拼接后存。
- UI 点批截图：无
- EMERGENCY / safe_beats / 离线灌库：**0**
- skip_finalize_gate：**是**（五章定稿门 409 后 skip 落库）。能落库 ≠ 过质控。
- 不宣称体验总 PASS / 人盲 ≥9.5；不改 `GATE_SAVE_MODE`。
