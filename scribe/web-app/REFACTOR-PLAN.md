# Scribe 前端重构方案（最优版）

> 目标:把 72 条后端能力**全部、恰当地**暴露;把信息架构与交互对标全网最佳实践;在**重构(复用现有代码)而非重写**的前提下,产出一版专业写作工作台。
> 设计系统真源:`design-system/scribe/MASTER.md`(已纠正工具误判)。

---

## 一、先正面回答你的三个问题

**Q1「工程2 / 工程2b 全局参考了吗?」**
跑了,但要诚实:`--design-system` 工具把本产品**误分类成 Newsletter Platform**,还配了**希伯来字体** —— 它的推理库偏向落地页,不适配「应用工作台」。我已:
- 落盘 `MASTER.md`(工程2b),并**人工纠正**三处错判:品类→长篇写作工作台、字体→「Inter/Noto Sans SC(UI)+ Source Serif 4/Noto Serif SC(正文)」双轨、页面模式→三栏 Binder·Editor·Inspector。
- 保留工具中**确实对路**的部分:Minimalism & Swiss 风格、深浅双模、克制 hover(150–300ms)、WCAG AAA、无 emoji 图标、可见 focus、4.5:1 对比。

**Q2「整个系统所有功能你暴露了吗?」**
**没有。** 72 条路由里,当前前端暴露 ~50,**11 类能力完全没有 UI**(见第三节 Gap 表)。这是本次重构最大的硬缺口。

**Q3「所有交互是最佳实践吗?参考全网了吗?」**
现有前端其实已相当扎实(命令面板、流式逐字、diff 裁决、SSE、深链、虚拟列表、防丢稿)。但有**结构性问题**:中栏把「决策卡 + 北极星 + 想象输入 + 章节列表 + 编辑器」**全部纵向堆叠**,违背 `visual-hierarchy` / `content-priority` / `primary-action`(一屏一主操作)。第六节逐条对照修正。

---

## 二、现状盘点

**组件(7 个文件 / 2698 行):**
| 文件 | 职责 |
|---|---|
| `App.tsx` | 三栏壳 + ⌘K 命令面板 + ⌘I 想象 + 专注/主题/SSE/深链 |
| `Library.tsx` | 左栏:作品库 |
| `Center.tsx` | 中栏:OptionSet 决策 + 北极星条 + 想象输入 + 大纲树 + 编辑器入口 |
| `Editor.tsx` | 章编辑:流式生成 / diff 裁决 / 段落视图 / 版本树 / 分支 / 评改 / 北极星裁决 |
| `Right.tsx` | 右栏:札记 + 设定/伏笔/一致性/素材/脉络 Tab + 主编对话 |
| `common.tsx` / `diff.ts` / `SegmentNode.ts` | 复用件:Btn/State/Toast/useData、字符级 diff、AI/人工段落节点 |

**值得保留(不要重写):** `common.tsx` 全套、`diff.ts`、`SegmentNode`、流式 `streamAction`、SSE 订阅、深链 hash 路由、虚拟列表、防丢稿、命令面板骨架。重构是**搬家 + 补面板 + 换皮**,不是推倒。

---

## 三、功能暴露 Gap 表（核心交付）

### ✅ 已暴露(~50 路由,略)
works / author-intent / volumes / chapters(增删改/移动/状态) / feedback / prose / branches / segments / check / actions+stream / critique / intent-check / materials / memory / timeline / cost / settings / impact / characters / foreshadows / consistency-flags / preference / imaginations / insights / proactive-review / option-sets / chat / events(SSE)

### ❌ 完全没有 UI 的后端能力（11 类 → 本次必补）
| # | 路由 | 是什么 | 放哪(建议) |
|---|---|---|---|
| 1 | `GET /works/{id}/quality` | 全书质量分(rubric 汇总) | 右栏「脉络/质量」Tab 顶部计分卡 |
| 2 | `GET /works/{id}/relations` | 实体关系图(谁与谁) | 右栏「设定圣经」→ 关系视图 |
| 3 | `GET /works/{id}/characters/{name}/states` | 角色状态轨迹(随章变化) | 设定圣经 → 角色卡内「状态时间线」 |
| 4 | `POST …/chapters/{seq}/deep-check` | 深度一致性体检 | 编辑器一致性区 +「深度体检」按钮 |
| 5 | `POST …/chapters/{seq}/ingest` | 章节摄入(建索引/抽实体) | 定稿后自动触发 + 手动「重建索引」 |
| 6 | `GET …/task` + `POST …/task/advance` | 章编排状态机(写作流水线) | 编辑器顶部「写作流程」步进条 |
| 7 | `GET /threads` + `POST /threads/{tid}/resolve` | 主编讨论线程(对话持久化) | 右栏「主编对话」→ 历史线程列表 |
| 8 | `GET/POST /agent-memory` | 跨会话记忆(5 命名空间) | 右栏新 Tab「记忆与技能」 |
| 9 | `GET/POST /agent-skills` + `{sid}/{action}` | 自我优化技能(**须人审批**) | 同上,审批门 UI |
| 10 | `imaginations/{iid}/status/{status}` | 想象状态推进(采纳/归档) | 想象列表项操作 |
| 11 | `GET /metrics` | 运维指标 | 不进用户界面(仅 dev) |

> 一句话:**8 张曾经的「死表」(agent_memory/agent_skills/threads/relations/char_states/quality…)后端已激活,但前端从没给过入口。** 本次把它们全部接出来。

---

## 四、全网最佳实践基准(提炼,非照搬)

| 参考产品 | 借鉴点 | 落到 Scribe |
|---|---|---|
| **Scrivener** | Binder(大纲)/ Editor / Inspector 三栏分工 | 把章节树**从中栏移到左栏**,中栏只剩编辑器 |
| **Ulysses / iA Writer** | 专注阅读、衬线正文、零干扰 | 正文用 Source Serif 4 / Noto Serif SC;专注模式隐藏两侧 |
| **Sudowrite / NovelCrafter** | Story Bible / Codex + AI 工具栏 + 卡片式建议 | 设定圣经 + 关系/状态;主编卡片已具雏形,统一为「决策卡」体系 |
| **Linear** | 键盘优先、⌘K 暴露**所有动作** | 命令面板从「只跳转」升级为「全动作」(写这章/评改/体检/查北极星/出方案…) |
| **Google Docs** | 版本历史 + 建议态 diff | 已有版本树/diff,补「质量分趋势」与摄入态 |
| **Notion** | 上下文 Inspector、渐进披露 | 右栏 Tab 收纳所有元数据,`progressive-disclosure` 不一次性塞满 |

---

## 五、最优信息架构(重构蓝图)

```
┌────────────┬─────────────────────────────┬──────────────────────┐
│ NAVIGATOR  │          EDITOR             │      INSPECTOR        │
│ (左 / 折叠) │       (中 / 专注圣地)        │   (右 / 上下文 Tab)    │
├────────────┼─────────────────────────────┼──────────────────────┤
│ ▸ 作品切换  │ ★ 北极星常驻条(sticky)       │ ⚑ 主编札记(置顶)      │
│   器        │ ──────────────────────────  │ ─ Tab ──────────────  │
│ ▾ 大纲树    │ ◆ 写作流程步进条(task,新)   │ · 设定圣经(+关系/状态)│
│   卷/章     │ ◆ OptionSet 决策(有则浮现)  │ · 伏笔                │
│   状态点    │ ──────────────────────────  │ · 一致性(+深度体检)   │
│   ⚠ 角标    │ 流式预览 / diff 裁决区       │ · 素材                │
│   拖拽排序  │ 段落阅读(AI蓝/人工绿+引用)   │ · 脉络 / 质量(新)    │
│            │ 版本树 · 分支 · 评改 · 裁决  │ · 对话 / 讨论线程(新) │
│            │ 操作:写这章 / 提意见重写     │ · 记忆与技能(新·审批)│
└────────────┴─────────────────────────────┴──────────────────────┘
全局:⌘K 全动作面板 · ⌘I 想象 · ⌘⇧F 专注 · ? 快捷键 · ☀/☾ 主题 · SSE 自动刷新
```

**关键改动 = 三件事:**
1. **章节树搬家**:`Center` 的 `Chapters` → 移入左栏 `Navigator`,中栏腾空给编辑器。(解决「中栏堆叠」根因)
2. **中栏瘦身**:只保留 北极星条 → 流程步进 → 决策卡(按需浮现)→ 编辑器。想象输入退回 ⌘I 模态(已存在),不再常驻占位。
3. **右栏补全**:新增 3 个 Tab(质量、讨论线程、记忆与技能)+ 在现有 Tab 内嵌入关系图/角色状态/深度体检。

---

## 六、交互最佳实践对照(当前违背 → 修正)

| ux 规则 | 当前问题 | 修正 |
|---|---|---|
| `primary-action`(一屏一主操作) | 中栏 5 块纵向堆叠,无主次 | 章树移走;主操作恒为「写/裁决当前章」 |
| `visual-hierarchy` `content-priority` | 决策卡/想象/北极星抢视线 | 决策卡仅在有待决时浮现;想象进模态 |
| `nav-state-active` `breadcrumb-web` | 当前所在章在标题,层级弱 | 左栏树高亮 + 中栏面包屑「卷›章」 |
| `readable-font-size` `line-length-control` | 正文用系统无衬线,无字号/行宽控制 | 衬线正文,行宽 60–75 字,行高 1.7 |
| `keyboard-shortcuts` | ⌘K 只跳转,快捷键无处可查 | ⌘K 全动作 + `?` 弹快捷键表 |
| `progressive-disclosure` | 右栏信息一次铺开 | Tab + 折叠卡,按需展开 |
| `color-not-only` | 状态点/严重度只用颜色 | 加图标/文字(已部分有,统一) |
| `empty-data-state` `loading-chart` | 新面板需空/载入态 | 复用 `State`,质量分加 skeleton |
| `responsive`(375/768/1024) | 三栏在窄屏靠 show-left/right,但中栏堆叠仍挤 | 中栏瘦身后窄屏天然改善;<1024 抽屉式 |

---

## 七、设计系统纠正(已落 MASTER.md)

- **品类**:Long-form Writing Workspace(非 Newsletter)。
- **字体**:UI = Inter + Noto Sans SC;正文 = Source Serif 4 + Noto Serif SC;数字 tabular-nums。
- **色板**:沿用工具给的 violet 主色 + cyan 强调(适配深色),但**补一套浅色映射**(当前 `--theme` 已切换,需校验浅色对比 4.5:1)。
- **令牌**:统一 `--space-* / --shadow-* / --radius`,把 `Editor`/`Right` 里散落的 inline style 收敛到 `index.css` 类。

---

## 八、分期执行计划(refactor,不推倒)

**P0 · 信息架构归位(改观感最大,风险低)**
- 章节树从 `Center` 移到左栏;中栏瘦身;面包屑;`Library` 升级为「作品切换器 + 大纲树」容器。
- 字体/令牌换皮:接入双轨字体,正文衬线,收敛 inline style。
- 浅色模式对比度校验。

**P1 · 补全缺失能力(暴露所有功能)**
- 右栏新 Tab:`质量`(quality)、`讨论线程`(threads + resolve)、`记忆与技能`(agent-memory + agent-skills 审批门)。
- 设定圣经内嵌:关系图(relations)、角色状态轨迹(states)。
- 编辑器:写作流程步进条(task/advance)、深度体检(deep-check)、定稿后 ingest。
- 想象状态推进(status)。

**P2 · 命令面板升级 + 键盘体系**
- ⌘K 收录所有动作(写这章/评改/体检/查北极星/出方案/全文体检/切书/切章…)。
- `?` 快捷键帮助层。

**P3 · 打磨**
- 空/载入 skeleton、reduced-motion、focus ring 全覆盖;质量分趋势小图;3 档断点回归。
- `npm run build` + 视觉自审(对照 MASTER.md Pre-Delivery Checklist)。

每期结束跑 `npm run build`,P3 末做完整 Pre-Delivery 勾选。

## 九、取舍与风险
- **不重写**:复用 common/diff/SegmentNode/流式/SSE,降回归风险。
- **agent-skills 是写动作 + 须人审批**:UI 必须把「审批门」做显式(proposed→approve 才生效),不能一键激活。
- **relations/quality 数据形态未在前端验证过**:P1 接入前先用真实接口探一次返回结构,避免按猜测写。
- **字体加载**:正文衬线用 `font-display: swap` + 预连接,避免 FOIT 拖慢首屏。
