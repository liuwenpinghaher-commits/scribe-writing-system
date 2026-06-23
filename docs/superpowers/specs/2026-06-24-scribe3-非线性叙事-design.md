# scribe3 非线性叙事 · 设计

> 设计日期:2026-06-24
> 目标:让 render 支持"叙事时间≠故事时间"(插叙/闪回/环形),复用 scribe3 知识帧的限知红利。

## 目标

scribe3 当前 `render`/`build_render_prompt` 的 `chapter` 参数**三合一**:同时是叙事章、事件故事时间(`events_at(chapter)`)、知识帧时间(`project_frame(focalizer, chapter)`)。这把叙事锁死成线性(章=故事时间 1:1)。本设计把三者拆开,给"渲染任意故事时间的事件 + 任意时间的知识帧"的能力——插叙/闪回/环形结构。

**关键架构红利**:`project_frame(focalizer, frame_at)` 已支持任意时间投影,所以插叙某角色的过去→投影他那时的知识帧,**限知正确性是免费的**(不穿帮)。这是 scribe2/hermes-novel 都没有的能力。

## 设计(沉浸默认 + 三处跟 frame_at)

### 拆三个时间维度(默认相等=线性,零回归)

```
render(world, chapter, focalizer, ..., story_at=None, frame_at=None)
  story_at = story_at if story_at is not None else chapter   # 渲染哪段故事时间的事件
  frame_at = frame_at if frame_at is not None else story_at  # 知识帧时间(沉浸默认=story_at)
```
- `chapter` = 叙事章(sjuzhet 位置)。
- `story_at` = 渲染 `events_at(story_at)` 的事件。
- `frame_at` = `project_frame(focalizer, frame_at)` 的知识帧。
- **线性**(默认):三者相等,行为完全不变。
- **沉浸式闪回**:`render(chapter=10, story_at=3)` → frame_at 默认=3 → 渲染第3章事件 + 焦三第3章只知那时。
- **回忆式**:`render(chapter=10, story_at=3, frame_at=10)` → 第3章事件 + 焦三第10章认知。

### `build_render_prompt` 改动

```
build_render_prompt(world, chapter, focalizer, craft_block="", soak_result=None,
                    voice=None, story_at=None, frame_at=None)
  story_at = story_at if story_at is not None else chapter
  frame_at = frame_at if frame_at is not None else story_at
  frame = project_frame(world, focalizer, frame_at)   # 原来用 chapter
  ...
  for ev in _events_at(world, story_at):              # 原来用 chapter
  ...
  # 插叙标注:story_at ≠ chapter 时,在"## 视角"标题行之后、"## 此刻所知"之前插一行
  # (prompt 开头区,模型第一眼看到这是非线性段;插在 lines 列表头部几行内)
  if story_at != chapter:
      # f"## ⚠ 这是插叙/闪回:渲染第{story_at}章发生的事(非当前叙事时间,别当线性推进)"
```

### `render()` 三处跟 frame_at(沉浸式一致性)

沉浸式闪回里角色的状态/声音也该是那时的:
- `soak(world, frame_at, focalizer, complete_fn)` — 浸泡用 frame_at(原来用 chapter)
- `latest_voice_samples(focalizer, frame_at)` — 声音用那时版本(呼应 #4 时间门:第3章焦三还是初版声音)(原来用 chapter)
- `build_render_prompt(..., story_at=story_at, frame_at=frame_at)` 透传

## 组件

| 文件 | 改动 |
|---|---|
| `scribe3/render.py` | `build_render_prompt` 加 `story_at`/`frame_at` 参数 + 拆时间 + 插叙标注;`render` 加 `story_at`/`frame_at` + soak/voice 跟 frame_at + 透传 |
| 测试 | `tests/test_render.py` 追加(线性零回归/沉浸闪回/回忆式/限知红利/插叙标注) |

## 不改的(YAGNI)

- **save 不动**:render 是产物;插叙正文存哪由作者用现有 `s3_save_chapter` 安置(sjuzhet 编排)。#2 只给"渲染任意故事时间"的能力,不管存储。
- **event 模型不动**:`events_at(story_at)` 已按 story_time 查,直接用。
- **不做多 story_time 混合渲染**(一次渲染多个故事时间的环形混排)——先做单 story_at 插叙,混排后续。
- **不做前端非线性 UI / MCP 工具**(本期只给 render 能力;`s3_render_scene` 可后续加 story_at 参数,本期 YAGNI)。

## 测试策略(TDD)

| 测试 | 断言 |
|---|---|
| `test_render.py::test_linear_default_unchanged` | `build_render_prompt(w, 1, foc)` 与 `build_render_prompt(w, 1, foc, story_at=1, frame_at=1)` 输出相同(默认=线性,零回归) |
| `test_render.py::test_flashback_renders_past_events` | `build_render_prompt(w, 10, foc, story_at=1)` 渲染第1章的事件(而非第10章) |
| `test_render.py::test_flashback_immersive_frame` | story_at=1 默认 frame_at=1:某角色在第1章的知识帧(沉浸)。用 luanshi_leak_world 验证 |
| `test_render.py::test_flashback_label` | story_at≠chapter 时 prompt 含"插叙/闪回" 标注;story_at=chapter 时不含 |
| `test_render.py::test_flashback_does_not_break_pov`(load-bearing) | 插叙第1章,老道 prompt 只含他第1章知道的,不含他第1章不知道的私密(project_frame(老道,1) 投影正确) |
| `test_render.py::test_recall_mode_frame` | `build_render_prompt(w, 10, foc, story_at=1, frame_at=10)` 用第10章知识帧(回忆式) |

## 不变量 / 风险

- **限知红利不破**:插叙的限知由 `project_frame(focalizer, frame_at)` 保证——焦三回第3章只投影他第3章的帧。test_flashback_does_not_break_pov 守护。
- **线性零回归**:story_at/frame_at 默认回退到 chapter,既有所有 render 测试不变(默认路径等价旧行为)。
- **声音时间门联动**:frame_at 透传给 `latest_voice_samples`,沉浸闪回自动用那时的声音版本(#4 已建时间门)。
- `build_render_prompt` 签名渐长(craft_block/soak_result/voice/story_at/frame_at 五个可选参数)——都向后兼容,但若再加可考虑收进一个 options 对象(本期不做,YAGNI)。
