import { WriteLayout } from './WriteLayout'
import { CodexDetail } from './CodexDetail'
import { AtlasView } from './views/AtlasView'
import { InsightView } from './views/InsightView'
import { TimelineView } from './views/TimelineView'
import { ContainerOutline } from './ContainerOutline'

const CODEX_LEAF = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif'])
const CONTAINER = new Set(['manuscript_root', 'codex_root', 'volume', 'codex_category'])
// 手稿容器(卷/手稿根)→ 章卡片墙/大纲表多模式;其余容器(素材分类)→ 子项列表
const MANUSCRIPT_CONTAINER = new Set(['manuscript_root', 'volume'])

// 把卡片/行点击的章 → 章 TreeNode(与 WriteLayout.onSeqChange 同形),选中后中间栏切写作台
const chapterNode = (seq, title = '') => ({ id: `ch:${seq}`, type: 'chapter', ref: seq, label: `${seq} ${title}`.trim() })

/**
 * 中间栏:按 sel 路由。
 *  - mode==='view'      → 横切视图(图谱/时间线/仪表盘/进度/概览)
 *  - node.type 章/场景  → 完整写作台 WriteLayout(传 seq)
 *  - node.type 素材叶   → CodexDetail 详情卡
 *  - node.type 容器     → 子项列表(MVP)
 */
export function DetailPane({ sel, work, onSelectNode, onTreeChanged, onJumpChapter }) {
  // —— 横切视图 ——
  if (sel?.mode === 'view') {
    const k = sel.viewKey
    if (k === 'atlas') return <AtlasView key={work} />
    if (k === 'insight') return <InsightView key={work} />
    if (k === 'timeline') return <TimelineView key={work} onJumpChapter={onJumpChapter} />
    if (k === 'overview') return <InsightView key={work} />   // MVP:概览暂复用仪表盘
    return <div className="p-8 text-faint">未实现的视图:{k}</div>
  }

  const node = sel?.node
  if (!node) {
    return (
      <div className="h-full grid place-items-center text-[13px] text-faint/60">
        从左侧项目树选一个章开始写,或选一个设定项查看详情。
      </div>
    )
  }

  // —— 章 / 场景 → 写作台(护栏/对话/草稿卡/正文不退化)——
  if (node.type === 'chapter' || node.type === 'scene') {
    const seq = node.type === 'scene' ? node.ref?.seq : node.ref
    return <WriteLayout key={work} work={work} seq={seq}
      onSeqChange={(s) => onSelectNode?.({ id: `ch:${s}`, type: 'chapter', ref: s, label: `${s}` })} />
  }

  // —— 素材叶 → 详情卡 ——
  if (CODEX_LEAF.has(node.type)) {
    return <CodexDetail key={node.id} node={node} onChanged={onTreeChanged} onDeleted={onTreeChanged} />
  }

  // —— 手稿容器(卷/手稿根)→ 卡片墙/大纲表多模式 ——
  if (MANUSCRIPT_CONTAINER.has(node.type)) {
    return <ContainerOutline key={node.id} node={node}
      onOpenChapter={(c) => onSelectNode?.(chapterNode(c.seq, c.title))}
      onSelect={onSelectNode} />
  }

  // —— 其余容器(素材分类)→ 子项列表 ——
  if (CONTAINER.has(node.type)) {
    return <ContainerOutline key={node.id} node={node} onSelect={onSelectNode}
      onOpenChapter={(c) => onSelectNode?.(chapterNode(c.seq, c.title))} />
  }

  return <div className="p-8 text-faint">未知节点类型:{node.type}</div>
}
