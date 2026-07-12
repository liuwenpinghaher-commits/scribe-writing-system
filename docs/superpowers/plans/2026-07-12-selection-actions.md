# 选区动作推广(聊这段/改这段 · 全阶段)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 大纲/草稿获得选区级「聊这段/改这段」,节拍/演绎获得条目级「聊这条/改这条」,全部骑现有 chiefIntent/stageProposal 总线;正文链路零改动。

**Architecture:** RichEditor 加可选 `onSelAction` 气泡动作;各阶段把聊/改话术经 `setChiefIntent` 预填进右栏 DiscussionDock(已监听);改的落地扩展各阶段既有 stageProposal pending 卡——「唯一子串命中→替换选中段,否则降级现状+提示」。spec:`docs/superpowers/specs/2026-07-12-selection-actions-design.md`。

**Tech Stack:** React + TipTap;测试 `cd scribe3/web && npx vitest run`;仓库纪律同前(TDD/中文 commit/Co-Authored-By 尾行/不 push)。

---

### Task 1:RichEditor `onSelAction` 气泡动作

**Files:** Modify `scribe3/web/src/editor/RichEditor.jsx`;Test `scribe3/web/src/editor/__tests__/richEditor-selAction.test.jsx`(新;若 editor 下无 __tests__ 目录惯例,放 `src/__tests__/`,以仓内现状为准)

- [ ] Step 1 失败测试(jsdom 下 TipTap BubbleMenu 可能不易真实弹出——先看仓内已有 RichEditor/ProseEditor 测试怎么测气泡;若无法直测弹出,退而测「传 onSelAction 时气泡容器内渲染两钮 + 点击回调 {text,intent}」,用 editor 命令设选区):

```jsx
// 断言语义(实现按仓内可行的测法调整,断言不变):
// ① 不传 onSelAction:气泡内无「改这段」「聊这段」按钮(与现状逐字一致)
// ② 传 onSelAction 且选区非空:两钮出现;点「聊这段」→ onSelAction({ text: '<选中文本>', intent: 'discuss' })
// ③ 点「改这段」→ intent 'edit';minimal 模式永远无气泡(现状)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:props 加 `onSelAction`;BubbleMenu 排版钮后 `{onSelAction && (<><div className="w-px h-5 bg-line mx-0.5" />…两钮…</>)}`;两钮沿 ProseEditor 同款(Sparkles「改这段」/MessagesSquare「聊这段」,title/aria 同文案);onClick 里 `const { from, to } = editor.state.selection; onSelAction({ text: editor.state.doc.textBetween(from, to, '\n'), intent })`
- [ ] Step 4 跑绿 + `npx vitest run` 全量(既有 RichEditor 使用方零回归)
- [ ] Step 5 Commit `feat: RichEditor 气泡可选注入聊这段/改这段动作`

### Task 2:大纲/草稿「聊这段」+「改这段」+ 替换落地

**Files:** Modify `scribe3/web/src/ChapterStudio.jsx`(OutlineTab 约 :112-198、DraftTab 约 :354-498,行号以 grep 为准);Test `scribe3/web/src/__tests__/chapterStudio-selAction.test.jsx`(新,harness 参考 chapterStudio-auxView.test.jsx 的 renderStudio + ChiefSlotProvider 包裹)

- [ ] Step 1 失败测试(核心断言):

```jsx
// ① 大纲 RichEditor 触发 onSelAction({text:'某段', intent:'discuss'})(直接调组件传入的回调或经气泡)
//    → useChiefSlot 的 chiefIntent 变为 { phase:'outline', seq, text: 含「某段」与「聊聊」} 且派发 s3-right-tab
// ② intent 'edit' → chiefIntent 话术含「改」;此后 setStageProposal({phase:'outline', seq, target:<现状值>, content:'新段落'})
//    → pending 卡主按钮文案「替换选中段」;点它 → 编辑器 value 中「某段」被替换为「新段落」且 patchChapter 被调(mock api)
// ③ buffer 含两处相同「某段」时 → 主按钮为现状文案 + 出现降级提示文本
// ④ 草稿 DraftTab 同型两条(替换后 draftRef.dirty 置真,不强制立即 saveDraft)
// ⑤ 切章 → selAnchor 清空(再来 proposal 不出「替换选中段」)
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:两个 Tab 各加 `selAnchor` state + `onSelAction` 回调(话术模板见 spec §2;`setChiefIntent`+`window.dispatchEvent(new CustomEvent('s3-right-tab', { detail:{ tab:'chief' } }))`——事件形状以 studioDocks.jsx 监听端实际为准);既有 stageProposal pending 卡分支:`selAnchor && buf.indexOf(a)===buf.lastIndexOf(a) && buf.includes(a)` → 「替换选中段」按钮(替换后走各自保存链)否则现状+降级提示;落地/放弃/切章清 anchor
- [ ] Step 4 跑绿 + 全量
- [ ] Step 5 Commit `feat: 大纲/草稿选区聊这段/改这段(chiefIntent+stageProposal 替换落地)`

### Task 3:节拍条目级「聊这条/改这条」

**Files:** Modify `scribe3/web/src/ChapterStudio.jsx`(BeatsTab 约 :207-351);Test 同 Task 2 文件追加

- [ ] Step 1 失败测试:每条节拍动作区出现两钮;聊 → chiefIntent 含该条文本;改 → 记 beatSel;setStageProposal(phase 'beats') → pending 卡出「替换该条」→ 点击后该条 text 被整条替换且 patchChapter 调用;无 beatSel 时维持现状「追加为新条目」
- [ ] Step 2 跑红
- [ ] Step 3 实现:行内动作与既有增删钮同排(hover 显隐随现状惯例);beatSel={_id};落地按 _id 定位替换(条目可能被上下移,_id 稳定);落地/放弃/切章清
- [ ] Step 4 跑绿 + 全量
- [ ] Step 5 Commit `feat: 节拍条目级聊这条/改这条(按 _id 替换落地)`

### Task 4:演绎条目级「聊这条/改这条」

**Files:** Modify `scribe3/web/src/DeduceStage.jsx`;Test `scribe3/web/src/__tests__/`(参考既有 DeduceStage 测试文件,无则新建)

- [ ] Step 1 先核实(报告里写明):DeduceStage 既有 stageProposal 落地行为是"替换当前目标 prose"还是"追加"?(grep matchStageProposal/useStageProposal 在 DeduceStage.jsx 的用法)
- [ ] Step 2 失败测试:当前目标工具条出现两钮;聊 → chiefIntent 含目标名与其 prose 引用;改 → chiefIntent 话术含「改」;落地语义=替换当前目标 prose(若 Step 1 核实已是替换则只测按钮与 chiefIntent,不重复测落地)
- [ ] Step 3 实现(最小:入口按钮 + 话术;落地按核实结论补或不补)
- [ ] Step 4 跑绿 + 全量
- [ ] Step 5 Commit `feat: 演绎条目级聊这条/改这条`

### Task 5:回归 + 真机验收

- [ ] Step 1 前端全量 vitest 绿;后端不涉及(纯前端改动,跑 `scribe3/.venv/bin/python -m pytest scribe3/tests/test_consistency.py -q` 冒烟即可)
- [ ] Step 2 真机(控制器亲自):进《纸命》某章,大纲选一段→聊(右栏输入框预填)→改(发出后中区出「替换选中段」卡→落地);草稿同;节拍/演绎条目级各走一遍;正文选区改这段回归(原链路不受影响);截图
- [ ] Step 3 汇报(改了什么/验证/遗留)

## 自审记录

- spec 覆盖:决策 1-4 ↔ Task 1(通用能力)/2(大纲草稿)/3(节拍)/4(演绎);不做清单未入任务 ✓。
- 类型一致:onSelAction({text,intent}) 贯穿 Task 1-2;selAnchor/beatSel 命名与 spec §2/§3 一致。
- 校准点(防 drift,执行时以实际为准):ChapterStudio 行号、s3-right-tab 事件 detail 形状、stageProposal 的 target 现状值、DeduceStage 落地行为(Task 4 Step 1 显式核实)。
