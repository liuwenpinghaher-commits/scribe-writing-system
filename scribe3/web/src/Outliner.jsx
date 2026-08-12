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
import { LabelSelect } from './LabelSelect'
import { showToast } from './ui/Toast'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'

// 单元格 synopsis inline 编辑。梗概是章级大纲的单一真相源(与 ChapterStudio OutlineTab
// 同写 chapter.synopsis / api.patchChapter);大纲常含多段 markdown,故用多行 <textarea>——
// 单行 <input> 无法承载换行,inline 编辑一次即把多段梗概静默压平(块四a-2 审查 Important-1)。
// Enter=换行(不提交);⌘/Ctrl+Enter 或失焦=提交;Esc=取消(还原)。
function SynopsisCell({ chapter }) {
  const ask = () => seedChiefNarrativeWrite(
    'outline',
    `第 ${chapter.seq} 章大纲`,
    `请更新第 ${chapter.seq} 章大纲。当前:\n${chapter.synopsis || '（空）'}`,
  )
  return (
    <button type="button" onClick={ask} title="让主编写入梗概(章级大纲)"
      className="w-full text-left text-f12 leading-snug cursor-pointer rounded px-1 -mx-1 py-0.5 hover:bg-soft/40 transition-colors"
      data-testid="outliner-synopsis-seed">
      {chapter.synopsis
        ? <span className="text-faint line-clamp-2 break-words whitespace-pre-line">{chapter.synopsis}</span>
        : <span className="text-faint">+ 让主编写梗概</span>}
    </button>
  )
}

function Row({ chapter, idx, colorMode, onOpen, onPatchSynopsis, onPatchLabel }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `row-${chapter.seq}`, data: { seq: chapter.seq } })
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }
  const qc = chapter.qc_issues || 0
  const labelMeta = LABEL_META[chapter.label]
  return (
    <tr ref={setNodeRef} style={style} className="border-b border-line/60 hover:bg-brand/[0.03] transition-colors">
      <td className="px-1 py-2 align-top">
        <button {...attributes} {...listeners}
          className="text-faint hover:text-ink cursor-grab active:cursor-grabbing touch-none" title="拖拽重排" aria-label="拖拽重排">
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
      {/* 状态:可编辑下拉(#70 色源生产入口);有值时前置 ◇ 保留原徽章视觉 */}
      <td className="px-2 py-2 align-top whitespace-nowrap">
        <span className="inline-flex items-center gap-0.5">
          {labelMeta && <Diamond size={11} className="shrink-0" style={{ color: `var(--color-${labelMeta.token})` }} />}
          <LabelSelect value={chapter.label} onChange={(v) => onPatchLabel?.(chapter.seq, v)} className="text-meta" />
        </span>
      </td>
      <td className="px-2 py-2 align-top whitespace-nowrap text-f12">
        <span className="inline-flex items-center gap-1.5">
          {chapter.hook_structured ? (
            <span
              className="inline-flex items-center rounded px-1 py-0.5 text-meta bg-ok/10 text-ok"
              title={chapter.hook_preview || '钩子已结构化'}
              data-testid="outliner-hook-badge"
            >
              钩
            </span>
          ) : null}
          {chapter.craft_compliance && chapter.craft_compliance.ok === false ? (
            <span
              className="inline-flex items-center rounded px-1 py-0.5 text-meta bg-danger/10 text-danger"
              title={chapter.craft_compliance.detail || 'C-Det 未通过'}
              data-testid="outliner-compliance-fail"
            >
              合规
            </span>
          ) : null}
          {qc > 0
            ? <span className="inline-flex items-center gap-0.5 text-warn tnum"><TriangleAlert size={12} className="shrink-0" />{qc}</span>
            : <Check size={13} className="text-ok" />}
        </span>
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
function LaneTable({ lane, colorMode, onOpen, onPatchSynopsis, onPatchLabel }) {
  const seqs = lane.chapters.map((c) => c.seq)
  return (
    <div className="mb-6">
      <h3 className="text-f14 font-semibold text-ink mb-2 px-0.5">{lane.title}
        <span className="ml-2 text-meta font-normal text-faint">{lane.chapters.length} 章</span>
      </h3>
      {lane.chapters.length === 0 ? (
        <EmptyLaneDropZone volumeId={lane.volumeId} />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-meta text-faint uppercase tracking-wider">
              <th className="w-6" />
              <th className="text-left font-medium px-2 py-1.5">章</th>
              <th className="text-left font-medium px-2 py-1.5 whitespace-nowrap">梗概<span className="ml-1 normal-case tracking-normal text-faint/60">(即章级大纲 · 处处同步)</span></th>
              <th className="text-left font-medium px-2 py-1.5">字数</th>
              <th className="text-left font-medium px-2 py-1.5 whitespace-nowrap" title={POV_HINT}>视角</th>
              <th className="text-left font-medium px-2 py-1.5">状态</th>
              <th className="text-left font-medium px-2 py-1.5" title="钩=钩子已结构化；合规=C-Det 未过；数字=QC">标记</th>
            </tr>
          </thead>
          <SortableContext items={seqs.map((s) => `row-${s}`)} strategy={verticalListSortingStrategy}>
            <tbody>
              {lane.chapters.map((c, i) => (
                <Row key={c.seq} chapter={c} idx={i} colorMode={colorMode}
                  onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} onPatchLabel={onPatchLabel} />
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
export function Outliner({ lanes, colorMode, onOpen, onPatchSynopsis, onPatchLabel, onReorder, onCrossVolumeMove }) {
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
          onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} onPatchLabel={onPatchLabel} />
      ))}
    </DndContext>
  )
}
