import { useEffect, useRef, useState } from 'react'
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor,
  useSensor, useSensors, useDroppable,
} from '@dnd-kit/core'
import {
  SortableContext, arrayMove, verticalListSortingStrategy,
  useSortable, sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, TriangleAlert, Check, Diamond } from 'lucide-react'
import { chapterLabel } from './chapterLabel'
import { cardColorVar, wcLabel, povLabel, POV_HINT, LABEL_META } from './outlineColors'
import { showToast } from './ui/Toast'

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
        className="w-full rounded-md border border-brand/40 bg-canvas px-2 py-1 text-f12 text-ink outline-none focus:border-brand" />
    )
  }
  return (
    <div onClick={() => setEditing(true)} title="点击编辑 · 即章级大纲,处处同步"
      className="text-f12 leading-snug cursor-text rounded px-1 -mx-1 py-0.5 hover:bg-soft/40 transition-colors">
      {chapter.synopsis
        ? <span className="text-faint line-clamp-2 break-words">{chapter.synopsis}</span>
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
            className="text-left text-f13 text-ink font-medium hover:text-brand transition-colors cursor-pointer truncate">
            {chapterLabel(chapter.seq, chapter.title || '')}
          </button>
        </div>
      </td>
      {/* 梗概列:w-full+max-w-0 让 auto 表格布局把剩余宽度全给梗概且不被长文撑破(截断/换行在 SynopsisCell) */}
      <td className="px-2 py-2 align-top min-w-[180px] w-full max-w-0"><SynopsisCell chapter={chapter} onPatchSynopsis={onPatchSynopsis} /></td>
      <td className="px-2 py-2 align-top text-f12 text-faint tnum whitespace-nowrap">{wcLabel(chapter.word_count)}</td>
      <td className="px-2 py-2 align-top text-f12 text-faint whitespace-nowrap" title={POV_HINT}>{povLabel(chapter.focalizer)}</td>
      <td className="px-2 py-2 align-top whitespace-nowrap">
        {labelMeta
          ? <span className="inline-flex items-center gap-1 text-f11" style={{ color: `var(--color-${labelMeta.token})` }}><Diamond size={11} className="shrink-0" />{labelMeta.text}</span>
          : <span className="text-f11 text-faint/40">—</span>}
      </td>
      <td className="px-2 py-2 align-top whitespace-nowrap text-f12">
        {qc > 0
          ? <span className="inline-flex items-center gap-0.5 text-warn tnum"><TriangleAlert size={12} className="shrink-0" />{qc}</span>
          : <Check size={13} className="text-ok" />}
      </td>
    </tr>
  )
}

// 空卷占位投放区(大纲表模式)
function EmptyLaneDropZone({ volumeId }) {
  const droppableId = `empty-lane-outliner-${volumeId ?? '__null__'}`
  const { setNodeRef, isOver } = useDroppable({
    id: droppableId,
    data: { isEmptyLane: true, volumeId },
  })
  return (
    <div ref={setNodeRef}
      className={`text-f12 py-3 border border-dashed rounded-lg text-center transition-colors ${isOver ? 'border-brand/60 bg-brand/5 text-brand' : 'border-line/40 text-faint/50'}`}>
      拖到此处移入本卷
    </div>
  )
}

// 卷泳道表格(只负责渲染,不持有 DndContext)
function LaneTable({ lane, colorMode, onOpen, onPatchSynopsis }) {
  const seqs = lane.chapters.map((c) => c.seq)
  return (
    <div className="mb-6">
      <h3 className="text-f14 font-semibold text-ink mb-2 px-0.5">{lane.title}
        <span className="ml-2 text-f11 font-normal text-faint">{lane.chapters.length} 章</span>
      </h3>
      {lane.chapters.length === 0 ? (
        <EmptyLaneDropZone volumeId={lane.volumeId} />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-f10 text-faint uppercase tracking-wider">
              <th className="w-6" />
              <th className="text-left font-medium px-2 py-1.5">章</th>
              <th className="text-left font-medium px-2 py-1.5 whitespace-nowrap">梗概<span className="ml-1 normal-case tracking-normal text-faint/60">(即章级大纲 · 处处同步)</span></th>
              <th className="text-left font-medium px-2 py-1.5">字数</th>
              <th className="text-left font-medium px-2 py-1.5 whitespace-nowrap" title={POV_HINT}>视角</th>
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
      )}
    </div>
  )
}

/**
 * 大纲表:单 DndContext 包住所有泳道,支持卷内重排 + 跨卷拖拽。
 * onReorder(volumeId, newSeqs, prevSeqs) → 卷内重排
 * onCrossVolumeMove(activeSeq, toVolumeId, overSeq) → 跨卷
 */
export function Outliner({ lanes, colorMode, onOpen, onPatchSynopsis, onReorder, onCrossVolumeMove }) {
  const [guarded, setGuarded] = useState(() => {
    try { return localStorage.getItem('s3.reorder.guarded') === '1' } catch { return false }
  })
  const guardOnce = () => {
    if (guarded) return
    setGuarded(true)
    try { localStorage.setItem('s3.reorder.guarded', '1') } catch { /* */ }
    showToast('重排只改阅读顺序,章号(故事时间轴)不变。')
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  // seq → volumeId 快速查找
  const seqToVolume = new Map()
  for (const lane of lanes) {
    for (const c of lane.chapters) seqToVolume.set(c.seq, lane.volumeId)
  }

  const onDragEnd = (e) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const a = active.data.current?.seq
    if (a == null) return

    // 识别落在空卷投放区的情况
    if (over.data.current?.isEmptyLane) {
      const toVolumeId = over.data.current.volumeId
      const fromVid = seqToVolume.get(a)
      if (fromVid !== toVolumeId) {
        guardOnce()
        onCrossVolumeMove?.(a, toVolumeId, null)
      }
      return
    }

    const o = over.data.current?.seq
    if (o == null) return
    const fromVid = seqToVolume.get(a)
    const toVid = seqToVolume.get(o)
    guardOnce()
    if (fromVid === toVid) {
      const lane = lanes.find((l) => l.volumeId === fromVid)
      if (!lane) return
      const seqs = lane.chapters.map((c) => c.seq)
      const from = seqs.indexOf(a), to = seqs.indexOf(o)
      if (from < 0 || to < 0 || from === to) return
      onReorder?.(fromVid, arrayMove(seqs, from, to), seqs)
    } else {
      onCrossVolumeMove?.(a, toVid, o)
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      {lanes.map((lane) => (
        <LaneTable key={lane.volumeId ?? 'null'} lane={lane} colorMode={colorMode}
          onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} />
      ))}
    </DndContext>
  )
}
