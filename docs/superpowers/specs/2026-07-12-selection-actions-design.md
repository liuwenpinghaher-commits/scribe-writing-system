# 选区动作推广(聊这段/改这段 · 全阶段)设计文档

日期:2026-07-12
状态:方案定稿,待作者确认后实施
背景:目前只有正文阶段(ProseEditor/WriteLayout)支持选中一段后「聊这段/改这段」。大纲/草稿用的通用 RichEditor 气泡菜单只有排版按钮;节拍/演绎是结构化条目;辅助视图只读。作者要求推广。

## 现状解剖(要点)

- 正文闭环:ProseEditor 气泡 → `discussSel` → `seedQuote`(prop 进 WriteChat)/`lastSel`(字符 offset+锚点防漂移)→ 主编出 2-3 候选(SSE proposal scope=selection)→ `applyProposal` 精确替换回 prose → 落库+护栏体检。全链是 WriteLayout 内部机制。
- 非正文阶段右栏是 **DiscussionDock**(独立对话组件),与 WriteChat 并列;两者间已有现成总线(ChiefSlotContext):
  - **`chiefIntent`** {phase, seq, text}:中区 → 右栏输入框预填(phase/seq 匹配防串台,ChiefDock.jsx:509);
  - **`stageProposal`** {phase, seq, target, content}:右栏生成完 → 中区阶段编辑器 `matchStageProposal` 显示 pending 落地卡(大纲/节拍/草稿/演绎已全部在用,即「让主编生成」链路)。
- 坐标机制差异:正文的精确替换依赖"与保存序列化同口径的字符 offset"(ProseEditor 有 `toText`+`pmPosToProseOffset` 配套);RichEditor 走 markdown 序列化,无等价转换器——**这是不硬造转换器的关键理由**(见下)。

## 设计决策

1. **骑现有总线,不复制正文链路**。聊=`chiefIntent` 预填话术;改=`chiefIntent` + 既有 `stageProposal` 落地通道,只把落地语义从"追加/整体"扩展出"替换选中段"。DiscussionDock 零改动(它已会预填和发布)。
2. **改这段的替换锚点用「唯一子串匹配」而非字符 offset**:选中文本(纯文本)在 md buffer 里 `indexOf` 唯一命中 → 精确替换;命中 0 次(选区跨格式符等)或多次 → 降级为现状落地卡(追加/整体)+ 明示提示「选中段无法精确定位,已按追加处理」。fail-soft,不造 md offset 转换器(YAGNI:大纲/草稿以中文纯段落为主,唯一命中是常态)。
3. **非正文阶段"改这段"出单提案而非 2-3 候选**:与该阶段既有「让主编生成」UX 一致(pending 卡:用此版/放弃);多候选机制仍是正文专属。想要多候选时作者可在话术里自己要,不做机制承诺。
4. **粒度按介质**:大纲/草稿=选区级;节拍/演绎=条目级(「聊这条/改这条」,选区在结构化条目上语义不成立);简报/关联/北极星=不做(只读资料;真要"聊"可自己复制进主编,暂不加按钮——YAGNI,痛点出现再说)。

## 交付内容

### 1. RichEditor 通用能力(editor/RichEditor.jsx)

新增可选 prop `onSelAction({ text, intent })`(intent: 'discuss' | 'edit')。传入且非 minimal 时,气泡菜单在排版钮后加分隔线 + 「改这段」「聊这段」两钮(图标/文案/aria 与 ProseEditor 同款);text 取 `editor.state.doc.textBetween(from, to, '\n')`。不传 prop 时气泡与现状逐字一致(其他 RichEditor 使用方零感知)。不暴露坐标(见决策 2)。

### 2. 大纲/草稿接线(ChapterStudio.jsx OutlineTab/DraftTab)

- **聊这段**:`setChiefIntent({ phase, seq, text: '就本章大纲/草稿这段和你聊聊(先不改):「{text}」\n' })` + 派发 `s3-right-tab` 聚焦主编。
- **改这段**:同上但话术为「把这段改一下,直接给出改后的完整段落:「{text}」」,并在该 Tab 记 `selAnchor = text`(阶段级 state,切章/切阶段清空)。
- **落地**:该阶段既有 stageProposal pending 卡增加分支——`selAnchor` 存在且当前 buffer `indexOf(selAnchor)` 唯一命中时,主按钮变「替换选中段」(splice 替换后走各自既有保存链:大纲 patchChapter、草稿置 dirty);否则维持现状按钮 + 降级提示。落地或放弃后清 `selAnchor`。

### 3. 节拍条目级(BeatsTab)

每条节拍行 hover 动作区加「聊这条」「改这条」小钮(与既有增删/上下移同排)。聊=chiefIntent 话术含该条文本;改=chiefIntent + 记 `beatSel = {_id}`;stageProposal 落地分支:`beatSel` 存在时主按钮「替换该条」(整条 text 替换,沿用失焦 flush 的 patchChapter);否则现状「追加为新条目」。

### 4. 演绎条目级(DeduceStage)

当前演绎目标(truth/角色,DeduceProvider.selected)的编辑区工具条加「聊这条」「改这条」。DiscussionDock 已带 deduce 语境(自动把 selected 写进话术与 focalizer)。改的落地:核实 DeduceStage 既有 stageProposal 落地行为(它已在总线用户清单里)——若已是"替换当前目标 prose"则零新逻辑,只补入口按钮;若是追加则加替换分支。以实现期核实为准,语义目标=替换当前选中演绎目标的 prose。

### 5. 明确不做

- 简报/关联/北极星的任何选区动作(只读资料);
- 非正文阶段的多候选(2-3 个)机制与 md 字符 offset 转换器(决策 2/3);
- 正文既有链路零改动(ProseEditor/WriteLayout/applyProposal 不碰)。

## 测试与验收

- RichEditor:传/不传 onSelAction 的气泡渲染差异;点击回调 intent/text 正确。
- 各阶段:聊→chiefIntent 内容与 phase/seq 正确;改→selAnchor 记录;stageProposal 唯一命中→「替换选中段」替换正确且走保存;多命中/零命中→降级提示;切章清 anchor。
- 真机:大纲/草稿/节拍/演绎各真选一段(条)走完聊与改两条链,截图;正文链路回归不受影响。

## 风险

| 风险 | 缓解 |
|---|---|
| 选中文本与 md buffer 不逐字一致(格式符/软换行) | 唯一子串匹配 + 显式降级路径,绝不静默错替 |
| chiefIntent 预填后作者改了话术,回来的 proposal 语义漂移 | 落地卡本来就是人审(用此版/放弃),漂移由人把关 |
| DeduceStage 落地行为与假设不符 | 实施 Task 内先核实再动,spec 已标注 |
