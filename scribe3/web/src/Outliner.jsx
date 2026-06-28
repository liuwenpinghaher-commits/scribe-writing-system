import { useEffect, useRef, useState } from 'react'
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor,
  useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, arrayMove, verticalListSortingStrategy,
  useSortable, sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical } from 'lucide-react'
import { chapterLabel } from './chapterLabel'
import { cardColorVar, wcLabel, LABEL_META } from './outlineColors'

// 单元格 synopsis inline 编辑
function SynopsisCell({ chapter, onPatchSynopsis }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(chapter.synopsis || '')
  const ref = useRef(null)
  useEffect(() => { if (!editing) setVal(chapter.synopsis || '') }, [chapter.synopsis, editing])
  useEffect(() => { if (editing && ref.current) { ref.current.focus(); ref.current.select() } }, [editing])
  const commit = () => {
    setEditing(false)
    const next = val.trim()
    if (next !== (chapter.synopsis || '')) onPatchSynopsis?.(chapter.seq, next)
  }
  if (editing) {
    return (
      <input ref={ref} value={val} onChange={(e) => setVal(e.target.value)} onBlur={commit}
        onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') { setVal(chapter.synopsis || ''); setEditing(false) } }}
        className="w-full rounded border border-brand/40 bg-canvas px-2 py-1 text-[12px] text-ink outline-none focus:border-brand" />
    )
  }
  return (
    <div onClick={() => setEditing(true)}
      className="text-[12px] leading-snug cursor-text rounded px-1 -mx-1 py-0.5 hover:bg-soft/40 transition-colors truncate">
      {chapter.synopsis
        ? <span className="text-faint">{chapter.synopsis}</span>
        : <span className="text-faint/40">+ 写梗概</span>}
    </div>
  )
}

function Row({ chapter, idx, colorMode, onOpen, onPatchSynopsis }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `row-${chapter.seq}`, data: { seq: chapter.seq } })
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }
  const qc = chapter.qc_issues || 0
  const labelMeta = LABEL_META[chapter.label]
  return (
    <tr ref={setNodeRef} style={style} className="border-b border-line/60 hover:bg-brand/[0.03] transition-colors">
      <td className="px-1 py-2 align-top">
        <button {...attributes} {...listeners}
          className="text-faint/40 hover:text-faint cursor-grab active:cursor-grabbing touch-none" title="拖拽重排" aria-label="拖拽重排">
          <GripVertical size={13} />
        </button>
      </td>
      <td className="px-2 py-2 align-top">
        <div className="flex items-center gap-1.5">
          <span className="w-1 h-4 rounded-sm shrink-0" style={{ background: cardColorVar(chapter, colorMode) }} />
          <button onClick={() => onOpen?.(chapter)}
            className="text-left text-[13px] text-ink font-medium hover:text-brand transition-colors cursor-pointer truncate">
            {chapterLabel(chapter.seq, chapter.title || '')}
          </button>
        </div>
      </td>
      <td className="px-2 py-2 align-top min-w-[180px]"><SynopsisCell chapter={chapter} onPatchSynopsis={onPatchSynopsis} /></td>
      <td className="px-2 py-2 align-top text-[12px] text-faint tnum whitespace-nowrap">{wcLabel(chapter.word_count)}</td>
      <td className="px-2 py-2 align-top text-[12px] text-faint whitespace-nowrap">{chapter.focalizer || '—'}</td>
      <td className="px-2 py-2 align-top whitespace-nowrap">
        {labelMeta
          ? <span className="text-[11px]" style={{ color: `var(--color-${labelMeta.token})` }}>◆ {labelMeta.text}</span>
          : <span className="text-[11px] text-faint/40">—</span>}
      </td>
      <td className="px-2 py-2 align-top whitespace-nowrap text-[12px]">
        {qc > 0 ? <span className="text-warn tnum">⚠{qc}</span> : <span className="text-ok">✓</span>}
      </td>
    </tr>
  )
}

function LaneTable({ lane, colorMode, onOpen, onPatchSynopsis, onReorder, guardOnce }) {
  const seqs = lane.chapters.map((c) => c.seq)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const onDragEnd = (e) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const a = active.data.current?.seq, o = over.data.current?.seq
    if (a == null || o == null) return
    const from = seqs.indexOf(a), to = seqs.indexOf(o)
    if (from < 0 || to < 0 || from === to) return
    guardOnce?.()
    onReorder?.(lane.volumeId, arrayMove(seqs, from, to), seqs)
  }
  return (
    <div className="mb-6">
      <h3 className="text-[14px] font-semibold text-ink mb-2 px-0.5">{lane.title}
        <span className="ml-2 text-[11px] font-normal text-faint">{lane.chapters.length} 章</span>
      </h3>
      {lane.chapters.length === 0 ? (
        <div className="text-[12px] text-faint/50 py-3">本卷暂无章。</div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-[10px] text-faint uppercase tracking-wider">
                <th className="w-6" />
                <th className="text-left font-medium px-2 py-1.5">章</th>
                <th className="text-left font-medium px-2 py-1.5">梗概</th>
                <th className="text-left font-medium px-2 py-1.5">字数</th>
                <th className="text-left font-medium px-2 py-1.5">视角</th>
                <th className="text-left font-medium px-2 py-1.5">状态</th>
                <th className="text-left font-medium px-2 py-1.5">QC</th>
              </tr>
            </thead>
            <SortableContext items={seqs.map((s) => `row-${s}`)} strategy={verticalListSortingStrategy}>
              <tbody>
                {lane.chapters.map((c, i) => (
                  <Row key={c.seq} chapter={c} idx={i} colorMode={colorMode}
                    onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} />
                ))}
              </tbody>
            </SortableContext>
          </table>
        </DndContext>
      )}
    </div>
  )
}

// 大纲表:按卷分组的电子表格,行可拖拽重排、梗概格 inline 编辑。
export function Outliner({ lanes, colorMode, onOpen, onPatchSynopsis, onReorder }) {
  const [guarded, setGuarded] = useState(() => {
    try { return localStorage.getItem('s3.reorder.guarded') === '1' } catch { return false }
  })
  const guardOnce = () => {
    if (guarded) return
    setGuarded(true)
    try { localStorage.setItem('s3.reorder.guarded', '1') } catch { /* */ }
    setTimeout(() => window.alert('重排只改阅读顺序,章号(故事时间轴)不变。'), 0)
  }
  return (
    <div>
      {lanes.map((lane) => (
        <LaneTable key={lane.volumeId ?? 'null'} lane={lane} colorMode={colorMode}
          onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} onReorder={onReorder} guardOnce={guardOnce} />
      ))}
    </div>
  )
}
