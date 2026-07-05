import { useState } from 'react'
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor,
  useSensor, useSensors, DragOverlay, useDroppable,
} from '@dnd-kit/core'
import {
  SortableContext, arrayMove, rectSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { ChapterCard } from './ChapterCard'
import { wcLabel } from './outlineColors'
import { showToast } from './ui/Toast'

// 计算重排后顺序(纯函数,便于单测)
export function computeReorder(seqs, activeSeq, overSeq) {
  const from = seqs.indexOf(activeSeq)
  const to = seqs.indexOf(overSeq)
  if (from < 0 || to < 0 || from === to) return seqs
  return arrayMove(seqs, from, to)
}

// 空卷占位投放区:注册 useDroppable 让拖拽感知空卷
function EmptyLaneDropZone({ volumeId }) {
  const droppableId = `empty-lane-${volumeId ?? '__null__'}`
  const { setNodeRef, isOver } = useDroppable({
    id: droppableId,
    data: { isEmptyLane: true, volumeId },
  })
  return (
    <div ref={setNodeRef}
      className={`col-span-full text-f12 py-4 flex items-center justify-center border border-dashed rounded-xl transition-colors ${isOver ? 'border-brand/60 bg-brand/5 text-brand' : 'border-line/40 text-faint/50'}`}>
      拖到此处移入本卷
    </div>
  )
}

// 卷泳道(只负责渲染,不持有 DndContext)
function VolumeLane({ lane, colorMode, onOpen, onPatchSynopsis, onPatchLabel, activeSeq }) {
  const seqs = lane.chapters.map((c) => c.seq)
  const totalWc = lane.chapters.reduce((s, c) => s + (c.word_count || 0), 0)

  return (
    <div className="mb-6" data-volume-id={lane.volumeId ?? '__null__'}>
      <div className="flex items-baseline gap-2 mb-2 px-0.5">
        <h3 className="text-f14 font-semibold text-ink">{lane.title}</h3>
        <span className="text-f11 text-faint">{lane.chapters.length} 章 · 总 {wcLabel(totalWc)} 字</span>
      </div>
      <SortableContext items={seqs.map((s) => `card-${s}`)} strategy={rectSortingStrategy}>
        <div className="grid gap-3 min-h-[64px]" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
          {lane.chapters.map((c) => (
            <ChapterCard key={c.seq} chapter={c} colorMode={colorMode}
              onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} onPatchLabel={onPatchLabel} />
          ))}
          {lane.chapters.length === 0 && (
            <EmptyLaneDropZone volumeId={lane.volumeId} />
          )}
        </div>
      </SortableContext>
    </div>
  )
}

/**
 * 卡片墙:单 DndContext 包住所有泳道,支持卷内重排 + 跨卷拖拽。
 * lanes = [{ volumeId, title, chapters:[...] }]
 * onReorder(volumeId, newSeqs, prevSeqs, fromVolumeId?) → 父层乐观+回滚
 */
export function Corkboard({ lanes, colorMode, onOpen, onPatchSynopsis, onPatchLabel, onReorder, onCrossVolumeMove }) {
  const [guarded, setGuarded] = useState(() => {
    try { return localStorage.getItem('s3.reorder.guarded') === '1' } catch { return false }
  })
  const [activeSeq, setActiveSeq] = useState(null)

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

  // 建 seq → volumeId 的快速查找表
  const seqToVolume = new Map()
  for (const lane of lanes) {
    for (const c of lane.chapters) {
      seqToVolume.set(c.seq, lane.volumeId)
    }
  }

  const onDragStart = (e) => {
    const seq = e.active.data.current?.seq
    if (seq != null) setActiveSeq(seq)
  }

  const onDragEnd = (e) => {
    setActiveSeq(null)
    const { active, over } = e
    if (!over || active.id === over.id) return
    const activeSeq = active.data.current?.seq
    if (activeSeq == null) return

    // 识别落在空卷投放区的情况
    if (over.data.current?.isEmptyLane) {
      const toVolumeId = over.data.current.volumeId
      const fromVid = seqToVolume.get(activeSeq)
      if (fromVid !== toVolumeId) {
        guardOnce()
        onCrossVolumeMove?.(activeSeq, toVolumeId, null)
      }
      return
    }

    const overSeq = over.data.current?.seq
    if (overSeq == null) return

    const fromVid = seqToVolume.get(activeSeq)
    const toVid = seqToVolume.get(overSeq)

    guardOnce()

    if (fromVid === toVid) {
      // 卷内重排
      const lane = lanes.find((l) => l.volumeId === fromVid)
      if (!lane) return
      const seqs = lane.chapters.map((c) => c.seq)
      const next = computeReorder(seqs, activeSeq, overSeq)
      if (next === seqs) return
      onReorder?.(fromVid, next, seqs)
    } else {
      // 跨卷移动
      onCrossVolumeMove?.(activeSeq, toVid, overSeq)
    }
  }

  const activeChapter = activeSeq != null
    ? lanes.flatMap((l) => l.chapters).find((c) => c.seq === activeSeq)
    : null

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}
      onDragStart={onDragStart} onDragEnd={onDragEnd}>
      {lanes.map((lane) => (
        <VolumeLane key={lane.volumeId ?? 'null'} lane={lane} colorMode={colorMode}
          onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} onPatchLabel={onPatchLabel} activeSeq={activeSeq} />
      ))}
      <DragOverlay>
        {activeChapter && (
          <div style={{ opacity: 0.9, pointerEvents: 'none' }}>
            <ChapterCard chapter={activeChapter} colorMode={colorMode}
              onOpen={undefined} onPatchSynopsis={undefined} dragHandle={false} />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  )
}
