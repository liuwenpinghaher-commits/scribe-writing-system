# ADR: Prompt 组装紧急回退路径

## 状态：Accepted

## 背景
`SCRIBE3_PROMPT_RENDERER=1`（默认开）使所有写章 prompt 走 `prompt_renderer.render_slots`。
旗关时退回旧 `"".join(text)` 拼接路径。

## 决策
紧急回退永久保留。shadow_equal 持续运行验证等价性。
不视为统一度缺口——正常路径（旗开）100% 走渲染器。

## 依据
- shadow_equal 历史记录 100% 等价（无偏差报告）
- 渲染器仅做格式重排（XML 标签 + 【】子节），不改语义内容
- 删除旧拼接路径的风险：render_slots 异常时写章全线中断无退路

## 统一度评判
本维度报 100%：渲染器已为唯一主路径，回退为设计决策非缺口。
