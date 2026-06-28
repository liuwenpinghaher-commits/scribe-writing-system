import { useEffect, useRef, useState } from 'react'
import {
  ChevronRight, ChevronDown, BookText, BookOpen, FileText,
  Users, Swords, Package, Tags, Shield, Bookmark, Flame, Lock,
  Pencil, Trash2, Check, X, Plus,
} from 'lucide-react'

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
  if (b.kind === 'pov') return null
  if (b.kind === 'count') return <span className={`text-[10px] tnum shrink-0 ${tone}`}>{b.value}</span>
  return <span className={`text-[10px] tnum shrink-0 ${tone}`}>{b.value}{b.kind === 'qc' ? '⚠' : ''}</span>
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
        onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') onCancel() }}
        className="flex-1 min-w-0 rounded border border-brand/40 bg-canvas px-1 py-0 text-[12px] text-ink outline-none focus:border-brand" />
      <button onMouseDown={(e) => { e.preventDefault(); commit() }}
        className="text-ok cursor-pointer shrink-0"><Check size={11} /></button>
      <button onMouseDown={(e) => { e.preventDefault(); onCancel() }}
        className="text-faint hover:text-ink cursor-pointer shrink-0"><X size={11} /></button>
    </span>
  )
}

function NodeRow({ node, depth, selId, expanded, onToggle, onSelect, onVolumeRename, onVolumeDelete, onAddVolume }) {
  const isContainer = CONTAINER_TYPES.has(node.type) || (node.children && node.children.length > 0)
  const open = expanded.has(node.id)
  const selected = node.id === selId
  const isVolume = node.type === 'volume'
  const isManuscriptRoot = node.type === 'manuscript_root'
  const [renaming, setRenaming] = useState(false)
  const [hovered, setHovered] = useState(false)

  const CatIcon = node.type === 'codex_category' ? (CAT_ICON[node.ref] || BookText)
    : isVolume ? BookOpen
    : node.type === 'chapter' ? FileText
    : node.type === 'scene' ? null
    : null

  const click = () => {
    if (CONTAINER_TYPES.has(node.type)) onToggle(node.id)
    onSelect(node)
  }

  const handleRename = (newTitle) => {
    setRenaming(false)
    onVolumeRename?.(node.ref, newTitle)
  }

  const handleDelete = (e) => {
    e.stopPropagation()
    onVolumeDelete?.(node.ref, node.label)
  }

  return (
    <>
      <div className="relative group/row"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}>
        <button
          onClick={click}
          title={node.label}
          className={`w-full flex items-center gap-1 rounded-lg pr-1.5 py-1 text-left transition-colors cursor-pointer ${selected ? 'bg-soft text-ink ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink'}`}
          style={{ paddingLeft: 6 + depth * 12 }}
        >
          {isContainer ? (
            <span className="shrink-0 w-3.5 inline-flex justify-center text-faint/70">
              {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </span>
          ) : <span className="shrink-0 w-3.5" />}
          {CatIcon && <CatIcon size={13} className="shrink-0 opacity-70" />}
          {renaming ? (
            <VolumeInlineEdit label={node.label}
              onCommit={handleRename} onCancel={() => setRenaming(false)} />
          ) : (
            <span className="truncate flex-1 text-[12.5px] leading-tight">{node.label}</span>
          )}
          {!renaming && (node.badges || []).map((b, i) => <Badge key={i} b={b} />)}
        </button>

        {/* 卷行 hover 操作:重命名 + 删除(不遮已选态) */}
        {isVolume && !renaming && hovered && (
          <span className="absolute right-1 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 bg-surface/90 rounded px-0.5">
            <button onClick={(e) => { e.stopPropagation(); setRenaming(true) }}
              title="重命名卷" className="text-faint hover:text-ink cursor-pointer p-0.5">
              <Pencil size={11} />
            </button>
            <button onClick={handleDelete}
              title="删除卷" className="text-faint hover:text-danger cursor-pointer p-0.5">
              <Trash2 size={11} />
            </button>
          </span>
        )}

        {/* 手稿根 hover:新建卷按钮 */}
        {isManuscriptRoot && hovered && (
          <span className="absolute right-1 top-1/2 -translate-y-1/2 inline-flex items-center bg-surface/90 rounded px-0.5">
            <button onClick={(e) => { e.stopPropagation(); onAddVolume?.() }}
              title="新建卷" className="text-faint hover:text-ink cursor-pointer p-0.5">
              <Plus size={11} />
            </button>
          </span>
        )}
      </div>

      {isContainer && open && (node.children || []).map((c) => (
        <NodeRow key={c.id} node={c} depth={depth + 1} selId={selId}
          expanded={expanded} onToggle={onToggle} onSelect={onSelect}
          onVolumeRename={onVolumeRename} onVolumeDelete={onVolumeDelete}
          onAddVolume={onAddVolume} />
      ))}
    </>
  )
}

function Section({ root, selId, expanded, onToggle, onSelect, onVolumeRename, onVolumeDelete, onAddVolume }) {
  if (!root) return null
  return (
    <div className="mb-2">
      <NodeRow node={root} depth={0} selId={selId} expanded={expanded}
        onToggle={onToggle} onSelect={onSelect}
        onVolumeRename={onVolumeRename} onVolumeDelete={onVolumeDelete}
        onAddVolume={onAddVolume} />
    </div>
  )
}

/**
 * 左侧常驻项目树:手稿支(卷→章→场景)+ 素材支(分类→条目)。
 * onVolumeRename(vid, newTitle), onVolumeDelete(vid, label), onAddVolume() 由父层传入。
 */
export function ProjectTree({ tree, selId, expanded, onToggle, onSelect, onVolumeRename, onVolumeDelete, onAddVolume }) {
  if (!tree) return <div className="p-3 text-[12px] text-faint/60">加载项目树…</div>
  return (
    <div className="p-2 select-none">
      <Section root={tree.manuscript} selId={selId} expanded={expanded}
        onToggle={onToggle} onSelect={onSelect}
        onVolumeRename={onVolumeRename} onVolumeDelete={onVolumeDelete}
        onAddVolume={onAddVolume} />
      <div className="h-px bg-line/60 my-2 mx-2" />
      <Section root={tree.codex} selId={selId} expanded={expanded}
        onToggle={onToggle} onSelect={onSelect} />
    </div>
  )
}
