import { WriteLayout } from './WriteLayout'
import { CodexDetail } from './CodexDetail'
import { AtlasView } from './views/AtlasView'
import { InsightView } from './views/InsightView'
import { TimelineView } from './views/TimelineView'

const CODEX_LEAF = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif'])
const CONTAINER = new Set(['manuscript_root', 'codex_root', 'volume', 'codex_category'])

// 容器节点(卷/分类)的 MVP 渲染:子项列表(卡片墙留进阶)。点子项 → 选中该叶。
function ContainerView({ node, onSelect }) {
  const kids = node.children || []
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-6">
        <h2 className="text-[18px] font-semibold text-ink mb-1">{node.label}</h2>
        <div className="text-[12px] text-faint mb-4">{kids.length} 项</div>
        {kids.length === 0 ? (
          <div className="text-[13px] text-faint/60 py-8 text-center">暂无子项。</div>
        ) : (
          <div className="space-y-1.5">
            {kids.map((c) => (
              <button key={c.id} onClick={() => onSelect(c)}
                className="w-full text-left rounded-xl border border-line bg-surface px-4 py-3 hover:border-brand/30 transition-colors cursor-pointer">
                <span className="text-[14px] text-ink">{c.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

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

  // —— 容器 → 子项列表(MVP)——
  if (CONTAINER.has(node.type)) {
    return <ContainerView node={node} onSelect={onSelectNode} />
  }

  return <div className="p-8 text-faint">未知节点类型:{node.type}</div>
}
