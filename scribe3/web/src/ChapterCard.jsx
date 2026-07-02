import { useEffect, useRef, useState } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, TriangleAlert, Check, Diamond } from 'lucide-react'
import { chapterLabel } from './chapterLabel'
import { cardColorVar, wcLabel, LABEL_META } from './outlineColors'

// 卡片墙单卡:色条 + 章号标题 + synopsis(inline 编辑)+ 字数/POV/QC/状态角标。
// 拖拽手柄(GripVertical)单独绑 listeners,正文区可点击进写作台。
export function ChapterCard({ chapter, colorMode, onOpen, onPatchSynopsis, dragHandle = true }) {
  const seq = chapter.seq
  const sortable = useSortable({ id: `card-${seq}`, data: { seq } })
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = sortable
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(chapter.synopsis || '')
  const taRef = useRef(null)
  useEffect(() => { if (!editing) setVal(chapter.synopsis || '') }, [chapter.synopsis, editing])
  useEffect(() => { if (editing && taRef.current) { taRef.current.focus(); taRef.current.select() } }, [editing])

  const commit = () => {
    setEditing(false)
    const next = val.trim()
    if (next !== (chapter.synopsis || '')) onPatchSynopsis?.(seq, next)
  }
  const cancel = () => { setVal(chapter.synopsis || ''); setEditing(false) }

  const qc = chapter.qc_issues || 0
  const labelMeta = LABEL_META[chapter.label]

  return (
    <div ref={setNodeRef} style={style}
      className="relative rounded-xl border border-line bg-surface overflow-hidden flex flex-col hover:border-brand/30 transition-colors">
      {/* 顶部色条(label/POV) */}
      <div className="h-1 w-full shrink-0" style={{ background: cardColorVar(chapter, colorMode) }} />
      <div className="p-3 flex flex-col gap-2 flex-1 min-h-0">
        {/* 标题行 + 拖拽手柄 */}
        <div className="flex items-start gap-1.5">
          {dragHandle && (
            <button {...attributes} {...listeners}
              className="shrink-0 mt-0.5 text-faint/40 hover:text-faint cursor-grab active:cursor-grabbing touch-none"
              title="拖拽重排" aria-label="拖拽重排">
              <GripVertical size={14} />
            </button>
          )}
          <button onClick={() => onOpen?.(chapter)}
            className="flex-1 min-w-0 text-left text-f14 font-semibold text-ink leading-snug hover:text-brand transition-colors cursor-pointer truncate">
            {chapterLabel(seq, chapter.title || '')}
          </button>
        </div>

        {/* synopsis(inline 编辑) */}
        {editing ? (
          <textarea ref={taRef} value={val} rows={3}
            onChange={(e) => setVal(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => { if (e.key === 'Escape') cancel(); if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) commit() }}
            placeholder="写本章梗概…(⌘/Ctrl+Enter 保存,Esc 取消)"
            className="w-full rounded-md border border-brand/40 bg-canvas px-2 py-1.5 text-f12 text-ink leading-relaxed outline-none focus:border-brand resize-y" />
        ) : chapter.synopsis ? (
          <div onClick={() => setEditing(true)}
            className="text-f12 text-faint leading-relaxed line-clamp-3 cursor-text hover:text-ink/80 transition-colors">
            {chapter.synopsis}
          </div>
        ) : (
          <button onClick={() => setEditing(true)}
            className="text-left text-f12 text-faint/40 hover:text-brand cursor-text transition-colors">
            + 写梗概
          </button>
        )}

        {/* 角标行:字数 · POV · QC · 状态 */}
        <div className="mt-auto flex items-center gap-2 flex-wrap text-f11">
          <span className="tnum text-faint">{wcLabel(chapter.word_count)}</span>
          {chapter.focalizer && (
            <span className="inline-flex items-center gap-1 text-faint">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: cardColorVar(chapter, 'pov') }} />
              {chapter.focalizer}
            </span>
          )}
          {qc > 0
            ? <span className="inline-flex items-center gap-0.5 text-warn tnum"><TriangleAlert size={12} className="shrink-0" />{qc}</span>
            : <Check size={13} className="text-ok" />}
          {labelMeta && (
            <span className="ml-auto inline-flex items-center gap-1" style={{ color: `var(--color-${labelMeta.token})` }}>
              <Diamond size={11} className="shrink-0" />{labelMeta.text}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
