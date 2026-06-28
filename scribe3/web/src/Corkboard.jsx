import { useState } from 'react'
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor,
  useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, arrayMove, rectSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { ChapterCard } from './ChapterCard'
import { wcLabel } from './outlineColors'

// 计算重排后顺序(纯函数,便于单测)
export function computeReorder(seqs, activeSeq, overSeq) {
  const from = seqs.indexOf(activeSeq)
  const to = seqs.indexOf(overSeq)
  if (from < 0 || to < 0 || from === to) return seqs
  return arrayMove(seqs, from, to)
}

// 一卷一泳道:卡片网格 + 卷内拖拽重排。
function VolumeLane({ lane, colorMode, onOpen, onPatchSynopsis, onReorder, guardOnce }) {
  const seqs = lane.chapters.map((c) => c.seq)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const onDragEnd = (e) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const activeSeq = active.data.current?.seq
    const overSeq = over.data.current?.seq
    if (activeSeq == null || overSeq == null) return
    const next = computeReorder(seqs, activeSeq, overSeq)
    guardOnce?.()
    onReorder?.(lane.volumeId, next, seqs)   // 乐观 + 回滚由父层据 prevSeqs 处理
  }

  const totalWc = lane.chapters.reduce((s, c) => s + (c.word_count || 0), 0)

  return (
    <div className="mb-6">
      <div className="flex items-baseline gap-2 mb-2 px-0.5">
        <h3 className="text-[14px] font-semibold text-ink">{lane.title}</h3>
        <span className="text-[11px] text-faint">{lane.chapters.length} 章 · 总 {wcLabel(totalWc)} 字</span>
      </div>
      {lane.chapters.length === 0 ? (
        <div className="text-[12px] text-faint/50 py-4">本卷暂无章。</div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={seqs.map((s) => `card-${s}`)} strategy={rectSortingStrategy}>
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
              {lane.chapters.map((c) => (
                <ChapterCard key={c.seq} chapter={c} colorMode={colorMode}
                  onOpen={onOpen} onPatchSynopsis={onPatchSynopsis} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </div>
  )
}

// 卡片墙:按卷分泳道。lanes = [{ volumeId, title, chapters:[...] }]
export function Corkboard({ lanes, colorMode, onOpen, onPatchSynopsis, onReorder }) {
  const [guarded, setGuarded] = useState(() => {
    try { return localStorage.getItem('s3.reorder.guarded') === '1' } catch { return false }
  })
  const guardOnce = () => {
    if (guarded) return
    setGuarded(true)
    try { localStorage.setItem('s3.reorder.guarded', '1') } catch { /* */ }
    // 一次性守卫提示:重排只改阅读顺序,不动章号(故事时间轴)
    setTimeout(() => window.alert('重排只改阅读顺序,章号(故事时间轴)不变。'), 0)
  }

  return (
    <div>
      {lanes.map((lane) => (
        <VolumeLane key={lane.volumeId ?? 'null'} lane={lane} colorMode={colorMode}
          onOpen={onOpen} onPatchSynopsis={onPatchSynopsis}
          onReorder={onReorder} guardOnce={guardOnce} />
      ))}
    </div>
  )
}
