---
name: write-chapter
description: 写小说的一章 —— 人定方向、AI 主笔。遵循"忠于北极星 + 选项式 + 意见可重写 + 主动护一致性"的协作回路。当作者要写新一章、续写、或基于某个想象展开时使用。
version: "1.0"
metadata:
  hermes:
    tags: [writing, fiction, scribe]
    requires_toolsets: [scribe]
---

## When to Use
作者要为某本书(work_id)写新的一章、续写、或把一个"想象"展开成正文时。

## 核心原则(不可违背)
- **AI 主笔,作者只想象 + 提意见**:你写全部文字;作者给方向、给意见、做选择,从不亲手写正文。
- **忠于北极星**:动笔前必读 `get_author_intent`(reader_feeling / central_promise / do_not_betray);任何与红线冲突的走向先停下来跟作者讨论。
- **只用本书设定**(防串味):检索/校验只针对该 work_id。
- **主动护一致性**,但不打断创作:问题用 `raise_consistency_flag` 安静登记,不在正文里啰嗦。

## Procedure
1. **取北极星与上下文**:`get_author_intent(work_id)`;`list_settings`/`list_characters`/`list_open_foreshadows` 取相关设定、角色声音(voice_profile)、待回收伏笔;用 `search_book(work_id, query=本章要点)` **语义召回相关前文片段**(防止与久远情节冲突/重复)。若有相关 `imaginations`(status=captured/scheduled),纳入本章。
2. **给方案,不擅自拍板**:对关键走向(本章主要冲突/转折/钩子)先给作者 **2–3 个有差异的方案 + 各自代价**(情感走向/人物代价/情节后果),让作者选。除非作者已明确指定方向。
3. **写正文**:按选定方案写。要求:贴合角色 voice_profile;章尾留钩子;**主动反平庸**(避免空洞辞藻、万能过渡、"不是…而是"、总结升华、情感直说;多用具体细节、克制、意外但合理)。**落库前自检**:对草稿调 `check_ai_slop`,若有 high 命中先自行改写再保存。写完 `save_chapter` + `save_snapshot(created_by='ai', branch_label='ai-draft')`,并对每段 `index_segment` 编入语义索引(供后续召回)。
4. **维护伏笔**:本章若埋新伏笔 → `plant_foreshadow`;若触发/回收了旧伏笔 → `advance_foreshadow(to_state='triggered'|'paid', chapter=本章seq)`。
5. **后台校验**:发现与设定/时间线/角色一致性冲突 → `raise_consistency_flag`(标 error_class/severity),不打断正文。
6. **意见→定向重写**:作者给意见时,**只改作者指出的地方**(不要整章重写),再次 `save_snapshot(parent_id=上一版)`。每次重写后用一句话说明改了什么。
7. **学习品味**:作者每次"选了哪个方案/给了什么意见/接受或拒绝重写",调 `record_preference`(work_id 省略=记入跨书的作者品味底色)。

## Pitfalls
- 不要替作者判断"什么是好"——给选项和依据,让作者选。
- 不要把另一本书的设定带进来(只用本 work_id)。
- 不要为了"完整"而把伏笔提前抖光或把情绪直接说出来。
- 终态伏笔(paid/abandoned)不可再推进(工具会报错,属正常)。

## Verification
- 章节与版本已落库(`list_snapshots` 可见父子链);
- 新伏笔已登记、回收的已 advance;
- 与北极星 do_not_betray 无冲突(有则应已先与作者讨论)。
