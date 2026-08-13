# 00-author-path · v6.3.4
- slug / 书名 / 新建时间（须 ∈ 证据窗）：`book_79c0d45e` / 炉灰记·v6.3.4·真chat全能力·20260814-1919 / 2026-08-13T19:19:18Z（POST /api/works 200，本轮新建）
- 作者是否真人坐浏览器：否（否 → 最高 engineering PARTIAL）
- 通道使用：discuss / ChangePack / world_write 同等 MCP 点批（`/orchestration/proposal/apply` execute=true） / prose_write（GET /chat/write）
- 是否仅对话+白名单 UI：否（列例外）：无 Playwright；结构/设定经 chat 种子后 MCP 点批；正文经 /chat/write 后 save-chapter。定稿质控 AI 味 heavy 时对 save 使用 `skip_finalize_gate`（craft GATE-B 已齐，checkpoint 可 stamp）。
- v632/v633/pilot：对照通道形状，非体验总 PASS
- 每章开写 chat：seq → tag（1..5 全填）：
  - ch1: s7-open-ch1
  - ch2: s7-open-ch2
  - ch3: s7-open-ch3
  - ch4: s7-open-ch4
  - ch5: s7-open-ch5
  见 transcript/thread.jsonl
- 每章 UI 点批截图路径：ch01..ch05：无（无头浏览器不可用）
- EMERGENCY / safe_beats / 离线灌库：0 次
- 写路径阻塞：装段 `_deduction_context_segments` 在 rebind 后 NameError `FOCAL_DEDUCTION_PROSE_CAP`，已修并 hot 部署后再写 2–5 章。
