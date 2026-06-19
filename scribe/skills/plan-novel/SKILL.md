---
name: plan-novel
description: 分层规划一部小说 —— 从北极星/想象出发,生成"作品→卷→章"大纲,选项式、忠于意图。当作者要立项新书、规划新卷、或把想象铺成章节大纲时使用。
version: "1.0"
metadata:
  hermes:
    tags: [writing, fiction, planning, scribe]
    requires_toolsets: [scribe]
---

## When to Use
作者要为某本书(work_id)立大纲、规划新一卷、或把若干想象铺成章节序列时。配合 `write-chapter`(写)与 Hermes 自带 `novel-outline`/`novel-genesis`(可借鉴结构)。

## 核心原则
- **源头是作者的想象与北极星**:先 `get_author_intent`,再 `list_imaginations(status='captured'|'scheduled')`;大纲必须服务 reader_feeling/central_promise,绝不碰 do_not_betray。
- **AI 出选项,作者拍板**:卷的弧线走向、关键转折、卷尾大钩子,给 **2–3 个差异方案 + 代价**,作者选。
- **只用本书设定**(防串味)。
- **百万字视角**:卷自身是小三幕(卷尾大钩子),卷间主线递进;长线伏笔在规划时就登记。

## Procedure
1. **读意图与素材**:`get_author_intent` + `list_imaginations` + `list_settings`/`list_characters`/`list_open_foreshadows`。
2. **卷级规划**:给作者 2–3 个卷弧线方案(目标冲突/主角变化/卷尾钩子/各自代价),选定后落 `save_chapter` 之上的卷信息(用 outline 里的结构锚点;卷表后续接入)。
3. **章级大纲**:把卷拆成章,每章 `save_chapter(work_id, seq, title, outline={...})`,outline 含:本章事件、出场角色、目标 beat、章尾钩子意图、涉及的设定/伏笔。
4. **登记长线伏笔**:规划阶段就 `plant_foreshadow`(标 importance;关键伏笔后续会被主动预警 `overdue_foreshadows`)。
5. **节奏自检**:确认爽点/钩子分布合理(网文节奏)、与北极星一致;有疑问发起讨论而非擅自定。
6. **学习品味**:作者的每次方案选择 → `record_preference`(省略 work_id 记入跨书品味底色)。

## Pitfalls
- 不要一次把全书章纲铺满到僵死;DHO 思想——先粗后细,边写边据实际(`get_chapter` 的 actual)回填修正。
- 长线伏笔只挖不登记 = 日后必漏;务必 `plant_foreshadow`。
- 不要替作者决定主线走向。

## Verification
- 章节大纲已落库(`get_chapter` 可读);
- 长线伏笔已登记(`list_open_foreshadows`);
- 与北极星 do_not_betray 无冲突。
