# Scribe3 语义纪律定向修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 安全修复真人验收识别出的章节语义纪律问题，并以全书官方后审证明结果。

**Architecture:** 端点生成完整候选稿，并以长度、确定性 QC、限知泄露与二次纪律判四个门禁控制落库。未通过时不改正文。

**Tech Stack:** FastAPI、SurrealDB、DeepSeek 官方 Chat Completions、pytest。

## Global Constraints

- 密钥只能以掩码设置使用，绝不回显或提交。
- 普通创作与 Hermes agentic 链路不变。
- 未通过门禁的候选不得写入正文。

### Task 1: 门禁纯函数

**Files:** `scribe3/critique.py`、`scribe3/tests/test_critique.py`

- [ ] 写入 `semantic_repair_gate(original, candidate, original_qc, candidate_qc, original_leaks, candidate_leaks, discipline)` 的失败测试。
- [ ] 验证候选少于原稿 85%、QC 增加、泄露增加、纪律降级或仍违规时返回 `ok=False`。
- [ ] 以最小实现通过测试。

### Task 2: fail-closed 修复端点

**Files:** `scribe3/app.py`、`scribe3/tests/test_app.py`

- [ ] 写入 `/semantic-repair` 的失败测试：noop 不写入、门禁失败不写入、成功创建 `semantic_repair` 版本。
- [ ] 端点使用官方直连 `hermes_complete(..., official_api=True)` 生成完整候选，保留场景顺序、命名事实、视角与 85% 长度。
- [ ] 全门禁通过才 `save_chapter` 与 `add_chapter_version(stage="semantic_repair")`。

### Task 3: 真人十章闭环

- [ ] 修复第 1、3、5、6、7、8、10 章并逐章复验。
- [ ] 重跑十章官方后审，要求全部未降级、质量为 0、泄露为 0、纪律违规为空。
- [ ] 运行 `scribe3/.venv/bin/python -m pytest scribe3/tests -q`、`npm run build`、`node pw_pilot_smoke.mjs 9`。
- [ ] 提交并推送实现、测试和本设计文档。
