# book_79c0d45e 日志盘点

数据源：demo `tonglu.qing.blue` 只读 + `docs/evidence/v634-true-chat-20260814/`。  
**没有**逐步中文 `pipeline_log`（`GET /api/debug/pipeline-logs` → 404）。现网主账仍是瘦 `pipeline_chain` + `pipeline_span`。

| # | 类别 | 来源 | 本轮状态 | 能回答什么 | 不能回答什么 |
|---|------|------|----------|------------|--------------|
| 1 | 书登记 | `GET /api/works` | 有。`book_79c0d45e`，10 章，字数 31614，goal 45000 | 是否本轮新书、规模 | 创建墙钟（列表无 created_at） |
| 2 | 章正文/脚手架 | `GET /api/chapter?seq=1..5` | 五章 prose 非空；beats=3；scene_truth≥80；deductions=3 | 读者看见什么、脚手架齐否 | 哪次 write 的哪一段被存进去 |
| 3 | Pipeline 链 | `GET /api/debug/pipeline-traces?work=` | **42 条**（write 28 / save 14） | 该跑没跑的对照、卡点、llm 耗时、save 红因 | 步内决策流水、输入字段运行值、消费边 |
| 4 | Pipeline span | `GET /…/traces/{id}` + `/pipeline-spans` | 有。写链 ~37–39 span；失败写链停在 `assemble.seg.voice_anchor` | 步骤身份、expected×actual、duration | 为何空（只剩 reason slug）、无 logs[] |
| 5 | Pipeline log | `GET /api/debug/pipeline-logs` | **404** | — | 用户要的「每步全部信息日志」 |
| 6 | Run 卡 | `GET /api/debug/run-cards` | 有（source=chain 兼容读） | 与 contrast_summary 同源红绿 | 同 3，不是分析账 |
| 7 | injection-trace | `GET /api/debug/injection-trace` | 有 last-one | 最近一次装段对照 | 历史；重启即丢语义 |
| 8 | 主编线程 | `GET /api/chat/threads` + 证据 `transcript/thread.jsonl` | 有默认线程；jsonl 有开写/设定种子 | 作者说过什么 | SSE 全文、模型回复 |
| 9 | ChangePack / MCP 点批 | 证据 `transcript/ops-*.json` | 大量 200 apply | 设定/卷章/GATE-B 如何落地 | 审批卡 UI |
| 10 | save / checkpoint | pipeline save 链 + author-path | save 失败 4 次（craft_gate_b / finalize_gate）；后 `skip_finalize_gate` 绿 | 能落库 ≠ 过质控 | 跳过 QC 的机器码未进链 headline |
| 11 | WCG | `00-world-complete-gate.json` | pass=true | 开书门闩 | 正文质量 |
| 12 | post-check | 本分析 `POST /api/post-check` 第 1–5 章 | 200；五章 `may_claim_readable=false`；1–4 AI 味 heavy | 重复/可读灯/scene_cover | 文学分；L1 LLM 审 skipped |
| 13 | post-finalize | 证据 ch1/ch3 | 200 | 定稿反哺候选路径存在 | 人批结果 |
| 14 | capabilities / health | 证据 + 现网 | fabric true / emergency false | 环境锁 | 写作质量 |

## 42 条链摘要

| kind | status | 章分布 | 含义 |
|------|--------|--------|------|
| write ok | 12 | 1×3, 2×1, 3×5, 4×1, 5×2 | 模型跑完；headline 仍是「戏剧合同空 · 工艺误注 · 目的误注」 |
| write failed | 16 | 2–5 各 4 | 热更前 `FOCAL_DEDUCTION_PROSE_CAP` NameError；链停在 voice_anchor，**无 error 正文** |
| save ok | 10 | 各章 | 对照齐全（假绿：只表示门闩行绿） |
| save failed | 4 | 1×3, 2×1 | `craft_gate_b` / `finalize_gate` blocked |

典型写链 id：`071e343971e0460fb863417e65e7ce20`（ch1 成功，llm 47.6s，contrast red=10）。  
典型失败写链：`73946e1a1ea74375a9e30aeb07839a62`（ch5，149ms 崩在 assemble）。  
典型 save 失败：`fd08fe1035ae45a883c3932c4fef094c`（finalize blocked）。

## 观测缺口（必须写进改造，不得假装已有）

1. 无 `pipeline_log`，分析员仍在读对照卡。  
2. 失败链没有 exception class/summary。  
3. `from_span_id` 仍空；headline 成功保存=「对照齐全」。  
4. 装段对照与 span 对同一段（大纲/codex）结论不一致（span 说 injected，contrast 说 empty）。  
5. 存稿跳过 QC 在链上不可见。
