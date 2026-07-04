import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Tree } from 'react-arborist'
import {
  ChevronRight, ChevronDown, BookText, BookOpen, FileText,
  Users, Swords, Package, Tags, Shield, Bookmark, Flame, Lock, Boxes,
  Pencil, Trash2, Check, X, Plus, TriangleAlert,
  Microscope, Quote, Scissors, Lightbulb, StickyNote,
} from 'lucide-react'

// 容器节点类型:点击=展开/折叠(也可选中出卡片墙,MVP 仅展开)
export const CONTAINER_TYPES = new Set(['manuscript_root', 'codex_root', 'volume', 'codex_category',
  'material_root', 'material_category'])

// 分类 ref → 图标
const CAT_ICON = {
  character: Users, faction: Swords, item: Package, term: Tags,
  world_rule: Shield, promise: Bookmark, motif: Flame, proposition: Boxes,
}

// 素材库分类 ref(kind)→ 图标
const MAT_ICON = {
  research: Microscope, reference: Quote, snippet: Scissors,
  inspiration: Lightbulb, note: StickyNote,
}

const ROW_HEIGHT = 28
const INDENT = 12

function Badge({ b }) {
  const tone = b.tone === 'danger' ? 'text-danger' : b.tone === 'warn' ? 'text-warn'
    : b.tone === 'ok' ? 'text-ok' : 'text-faint'
  if (b.kind === 'secret') return <Lock size={11} className="text-faint/60 shrink-0" />
  if (b.kind === 'pov') return null
  if (b.kind === 'count') return <span className={`text-f10 tnum shrink-0 ${tone}`}>{b.value}</span>
  if (b.kind === 'qc') return <span className={`inline-flex items-center gap-0.5 text-f10 tnum shrink-0 ${tone}`}>{b.value}<TriangleAlert size={10} className="shrink-0" /></span>
  return <span className={`text-f10 tnum shrink-0 ${tone}`}>{b.value}</span>
}

// 卷节点内联重命名
function VolumeInlineEdit({ label, onCommit, onCancel }) {
  const [val, setVal] = useState(label)
  const ref = useRef(null)
  useEffect(() => { ref.current?.focus(); ref.current?.select() }, [])
  const commit = () => { const t = val.trim(); if (t) onCommit(t); else onCancel() }
  return (
    <span className="inline-flex items-center gap-0.5 flex-1 min-w-0" onClick={(e) => e.stopPropagation()}>
      <input ref={ref} value={val} onChange={(e) => setVal(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => { e.stopPropagation(); if (e.key === 'Enter') commit(); if (e.key === 'Escape') onCancel() }}
        className="flex-1 min-w-0 rounded border border-brand/40 bg-canvas px-1 py-0 text-f12 text-ink outline-none focus:border-brand" />
      <button onMouseDown={(e) => { e.preventDefault(); commit() }}
        className="text-ok cursor-pointer shrink-0"><Check size={11} /></button>
      <button onMouseDown={(e) => { e.preventDefault(); onCancel() }}
        className="text-faint hover:text-ink cursor-pointer shrink-0"><X size={11} /></button>
    </span>
  )
}

/**
 * arborist 行渲染器:单行(虚拟化下只渲可视行)。
 * node.data 是原始 TreeNode {id, type, ref, label, children?, badges?, meta?}。
 * style 由 arborist 提供(含 paddingLeft = level * indent + offset)。
 */
function Row({ node, style, dragHandle, tree }) {
  const data = node.data
  const isContainer = !node.isLeaf
  const open = node.isOpen
  const selected = node.isSelected
  const isVolume = data.type === 'volume'
  const isManuscriptRoot = data.type === 'manuscript_root'
  const [hovered, setHovered] = useState(false)
  const cb = tree.props.handlers   // 透传父层回调(见 ProjectTree)

  const CatIcon = data.type === 'codex_category' ? (CAT_ICON[data.ref] || BookText)
    : data.type === 'material_category' ? (MAT_ICON[data.ref] || BookText)
    : isVolume ? BookOpen
    : data.type === 'chapter' ? FileText
    : null

  const click = (e) => {
    e.stopPropagation()
    if (isContainer) node.toggle()
    cb.onSelect(data)
  }

  const handleRename = (newTitle) => {
    node.reset()
    cb.onVolumeRename?.(data.ref, newTitle)
  }

  return (
    <div
      ref={dragHandle}
      style={style}
      className="relative group/row"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={click}
        title={data.label}
        className={`w-full h-[28px] flex items-center gap-1 rounded-lg pr-1.5 text-left transition-colors cursor-pointer ${selected ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}
      >
        {isContainer ? (
          <span className="shrink-0 w-3.5 inline-flex justify-center text-faint/70"
            onClick={(e) => { e.stopPropagation(); node.toggle() }}>
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        ) : <span className="shrink-0 w-3.5" />}
        {CatIcon && <CatIcon size={13} className="shrink-0 opacity-70" />}
        {node.isEditing ? (
          <VolumeInlineEdit label={data.label}
            onCommit={handleRename} onCancel={() => node.reset()} />
        ) : (
          <span className="truncate flex-1 text-f13 leading-tight">{data.label}</span>
        )}
        {!node.isEditing && (data.badges || []).map((b, i) => <Badge key={i} b={b} />)}
      </button>

      {/* 卷行 hover 操作:重命名 + 删除(不遮已选态) */}
      {isVolume && !node.isEditing && hovered && (
        <span className="absolute right-1 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 bg-surface/90 rounded px-0.5">
          <button onClick={(e) => { e.stopPropagation(); node.edit() }}
            title="重命名卷" className="text-faint hover:text-ink cursor-pointer p-0.5">
            <Pencil size={11} />
          </button>
          <button onClick={(e) => { e.stopPropagation(); cb.onVolumeDelete?.(data.ref, data.label) }}
            title="删除卷" className="text-faint hover:text-danger cursor-pointer p-0.5">
            <Trash2 size={11} />
          </button>
        </span>
      )}

      {/* 手稿根 hover:新建卷按钮 */}
      {isManuscriptRoot && hovered && (
        <span className="absolute right-1 top-1/2 -translate-y-1/2 inline-flex items-center bg-surface/90 rounded px-0.5">
          <button onClick={(e) => { e.stopPropagation(); cb.onAddVolume?.() }}
            title="新建卷" className="text-faint hover:text-ink cursor-pointer p-0.5">
            <Plus size={11} />
          </button>
        </span>
      )}
    </div>
  )
}

// 容器尺寸测量:arborist 不自动撑满,需传数字 width/height。
// 用 callback ref(元素挂载时才触发)—— 关键:项目树先经「加载中」早返回、boxRef 尚未渲染,
// 待 tree 加载后 boxRef 才挂载;callback ref 此刻才跑,设 RO + 立即量,彻底避开 useLayoutEffect([])
// 只在首挂载(boxRef 还没渲染)跑一次的时序坑。
function useContainerSize() {
  const [size, setSize] = useState({ width: 0, height: 0 })
  const roRef = useRef(null)
  const ref = useCallback((el) => {
    if (roRef.current) { roRef.current.disconnect(); roRef.current = null }
    if (!el) return
    const measure = () => {
      const r = el.getBoundingClientRect()
      setSize({ width: Math.round(r.width), height: Math.round(r.height) })
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    roRef.current = ro
  }, [])
  return [ref, size]
}

// 默认展开:复用父层传入的 expanded Set → arborist initialOpenState(键为节点 id)。
function toOpenState(expanded) {
  const s = {}
  if (expanded) for (const id of expanded) s[id] = true
  return s
}

/**
 * 左侧常驻项目树(react-arborist 虚拟化):手稿支(卷→章→场景)+ 设定支(分类→条目)+ 素材库支(kind→素材)。
 * 单棵 Tree 含三根(manuscript_root / codex_root / material_root),内部 react-window 只渲可视行 —— 数千章不全量 DOM。
 *
 * props 契约(与旧版一致,BinderLayout 不改):
 *   tree / selId / expanded / onToggle / onSelect / onVolumeRename / onVolumeDelete / onAddVolume
 *   onReorder(volume, order):拖拽重排回调(走 sort_order,不动 seq);BinderLayout 新接一行。
 */
export function ProjectTree({
  tree, selId, expanded, onToggle, onSelect,
  onVolumeRename, onVolumeDelete, onAddVolume, onReorder,
}) {
  const [boxRef, size] = useContainerSize()

  // 三根并列为单棵树的顶层 data(原始节点已带 children,直接复用)。
  const data = useMemo(() => {
    if (!tree) return null
    const roots = []
    if (tree.manuscript) roots.push(tree.manuscript)
    if (tree.codex) roots.push(tree.codex)
    if (tree.materials) roots.push(tree.materials)
    return roots
  }, [tree])

  // initialOpenState 只在首挂载/数据切换时生效;之后 arborist 自管开合(虚拟化友好)。
  const initialOpenState = useMemo(() => toOpenState(expanded), [tree])  // eslint-disable-line react-hooks/exhaustive-deps

  // 透传给 Row 的回调(经 tree.props.handlers 取用,避免逐行 props)。
  const handlers = useMemo(() => ({ onSelect, onVolumeRename, onVolumeDelete, onAddVolume }),
    [onSelect, onVolumeRename, onVolumeDelete, onAddVolume])

  // 拖拽校验:只允许「章」拖动(disableDrag 收到的是 data 对象,非 NodeApi)。
  // 只能落在卷/未分卷容器(或其内章间)——素材支整支禁拖/禁落。
  const disableDrag = (d) => d.type !== 'chapter'
  const disableDrop = ({ parentNode }) => {
    // arborist 落点的目标父节点:必须是 volume(含未分卷 vol:null)。
    return !parentNode || parentNode.data.type !== 'volume'
  }

  // onMove:把拖动结果换算成「目标卷 + 该卷章 seq 全量新序」→ 走 reorderChapters(不动 seq)。
  const onMove = ({ dragIds, parentNode, index }) => {
    if (!onReorder || !parentNode || parentNode.data.type !== 'volume') return
    const movedId = dragIds[0]                       // 一次只拖一章
    const volRef = parentNode.data.ref               // 卷裸 id 或 null(未分卷)
    // 目标卷现有章 seq 序(排除被拖章),再在 index 处插入。
    const seqOf = (n) => n.ref
    const siblings = (parentNode.data.children || [])
      .filter((c) => c.type === 'chapter' && c.id !== movedId)
      .map(seqOf)
    const moved = findChapterSeq(tree, movedId)
    if (moved == null) return
    const insertAt = Math.min(index, siblings.length)
    siblings.splice(insertAt, 0, moved)
    onReorder(volRef, siblings)
  }

  if (!tree) return <div className="p-3 text-f12 text-faint/60">加载项目树…</div>
  if (!data || data.length === 0) return <div className="p-3 text-f12 text-faint/60">暂无内容</div>

  // 用 relative + absolute inset-0 让测量容器有确定尺寸(不受 Tree 条件渲染影响),
  // RO 量到真实宽高后再渲染 arborist Tree。
  return (
    <div className="relative h-full w-full select-none">
      <div ref={boxRef} className="absolute inset-0 p-1 overflow-hidden">
        {size.width > 0 && size.height > 0 && (
          <Tree
            data={data}
            handlers={handlers}
            openByDefault={false}
            initialOpenState={initialOpenState}
            selection={selId || undefined}
            width={size.width}
            height={size.height}
            indent={INDENT}
            rowHeight={ROW_HEIGHT}
            overscanCount={8}
            disableMultiSelection
            disableEdit={(d) => d.type !== 'volume'}
            disableDrag={disableDrag}
            disableDrop={disableDrop}
            onMove={onMove}
            onToggle={(id) => onToggle?.(id)}
            className="!overflow-x-hidden"
          >
            {Row}
          </Tree>
        )}
      </div>
    </div>
  )
}

// 在原始 tree 里按 arborist 节点 id 找到章的 seq(ref)。
function findChapterSeq(tree, id) {
  for (const vol of tree?.manuscript?.children || []) {
    for (const ch of vol.children || []) {
      if (ch.id === id) return ch.ref
    }
  }
  return null
}
