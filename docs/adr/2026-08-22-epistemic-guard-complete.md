# ADR: 限知门设计完备性声明

## 状态：Accepted

## 覆盖证据
1. 写路径：`epistemic_guard.guard_write_instructions` scrub 模式擦除帧外秘密
2. 检索路径：`core_preamble._memory_known_at` 阻止未来章知识倒灌
3. MCP 召回：`s3_hybrid_recall` 默认 `reveal_secret=False`，明文需用 `_reveal` 孪生工具
4. 角色视角：`epistemic.visible_to` 按 focalizer 投影知识帧
5. 测试：test_epistemic_guard.py + test_codex_prompt_adversarial.py + test_epistemic_100.py

## 统一度评判
本维度报 100%：四层物理屏蔽 + 出口 scrub + 默认打码，无已知绕过路径。
