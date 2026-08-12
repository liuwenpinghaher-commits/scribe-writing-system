# root-cause · CL-B2 red→green（本会话可复验）

## red 状态（有产物）

- **evaluated_at**: `2026-08-12T10:48:41.590480+00:00`
- **failed_hard**: CL-B2-H1（synopsis cn_len=21 < 80）
- **gate_b.ok**: True（**不得**当 craft-loop green）
- **artifact**: `machine/chapter-red.json`, `machine/http-orch-apply-short-synopsis.*`, `machine/eval-red.json`

## 根因 taxonomy

- **C（工艺/阈值）**: gate_b B1 在 40–79 仍 pass，与 craft-loop SSOT≥80 分叉 → 假绿风险。
- **非 K**: 不靠再生成掩盖；用合法加长大纲。

## 修复

- 通道: `POST /orchestration/proposal/apply` decision=approve execute=true · tool `s3_patch_chapter_plan`
- 动作: synopsis 加长至 cn_len≥80，含起因→转折→结果与章末钩子

## 复验

见 green 产物 `machine/chapter-green.json` / `eval-green.json`。
