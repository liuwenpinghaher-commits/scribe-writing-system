import { ChevronRight, ChevronDown, BookText, BookOpen, FileText, Users, Swords, Package, Tags, Shield, Bookmark, Flame, Lock } from 'lucide-react'

// 容器节点类型:点击=展开/折叠(也可选中出卡片墙,MVP 仅展开)
export const CONTAINER_TYPES = new Set(['manuscript_root', 'codex_root', 'volume', 'codex_category'])

// 分类 ref → 图标
const CAT_ICON = {
  character: Users, faction: Swords, item: Package, term: Tags,
  world_rule: Shield, promise: Bookmark, motif: Flame,
}

function Badge({ b }) {
  const tone = b.tone === 'danger' ? 'text-danger' : b.tone === 'warn' ? 'text-warn'
    : b.tone === 'ok' ? 'text-ok' : 'text-faint'
  if (b.kind === 'secret') return <Lock size={11} className="text-faint/60 shrink-0" />
  if (b.kind === 'pov') return null   // 视角不在树里堆角标(避免噪声),meta 里可见
  if (b.kind === 'count') return <span className={`text-[10px] tnum shrink-0 ${tone}`}>{b.value}</span>
  return <span className={`text-[10px] tnum shrink-0 ${tone}`}>{b.value}{b.kind === 'qc' ? '⚠' : ''}</span>
}

function NodeRow({ node, depth, selId, expanded, onToggle, onSelect }) {
  const isContainer = CONTAINER_TYPES.has(node.type) || (node.children && node.children.length > 0)
  const open = expanded.has(node.id)
  const selected = node.id === selId
  const CatIcon = node.type === 'codex_category' ? (CAT_ICON[node.ref] || BookText)
    : node.type === 'volume' ? BookOpen
    : node.type === 'chapter' ? FileText
    : node.type === 'scene' ? null
    : null

  const click = () => {
    if (CONTAINER_TYPES.has(node.type)) onToggle(node.id)
    onSelect(node)
  }

  return (
    <>
      <button
        onClick={click}
        title={node.label}
        className={`group w-full flex items-center gap-1 rounded-lg pr-1.5 py-1 text-left transition-colors cursor-pointer ${selected ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}
        style={{ paddingLeft: 6 + depth * 12 }}
      >
        {isContainer ? (
          <span className="shrink-0 w-3.5 inline-flex justify-center text-faint/70">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        ) : <span className="shrink-0 w-3.5" />}
        {CatIcon && <CatIcon size={13} className="shrink-0 opacity-70" />}
        <span className="truncate flex-1 text-[12.5px] leading-tight">{node.label}</span>
        {(node.badges || []).map((b, i) => <Badge key={i} b={b} />)}
      </button>
      {isContainer && open && (node.children || []).map((c) => (
        <NodeRow key={c.id} node={c} depth={depth + 1} selId={selId}
          expanded={expanded} onToggle={onToggle} onSelect={onSelect} />
      ))}
    </>
  )
}

function Section({ root, selId, expanded, onToggle, onSelect }) {
  if (!root) return null
  return (
    <div className="mb-2">
      <NodeRow node={root} depth={0} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} />
    </div>
  )
}

/**
 * 左侧常驻项目树:手稿支(卷→章→场景)+ 素材支(分类→条目)。
 * 单一真相源由父层持有:selId(选中节点 id)、expanded(展开集合)。
 */
export function ProjectTree({ tree, selId, expanded, onToggle, onSelect }) {
  if (!tree) return <div className="p-3 text-[12px] text-faint/60">加载项目树…</div>
  return (
    <div className="p-2 select-none">
      <Section root={tree.manuscript} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} />
      <div className="h-px bg-line/60 my-2 mx-2" />
      <Section root={tree.codex} selId={selId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} />
    </div>
  )
}
