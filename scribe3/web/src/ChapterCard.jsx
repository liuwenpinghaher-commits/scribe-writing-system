import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, TriangleAlert, Check, Diamond } from 'lucide-react'
import { chapterLabel } from './chapterLabel'
import { cardColorVar, wcLabel, povLabel, POV_HINT, LABEL_META } from './outlineColors'
import { LabelSelect } from './LabelSelect'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'

// 卡片墙单卡:色条 + 章号标题 + synopsis(只读 + 主编种子)+ 字数/POV/QC/状态角标。
// 拖拽手柄(GripVertical)单独绑 listeners,正文区可点击进写作台。
export function ChapterCard({ chapter, colorMode, onOpen, onPatchLabel, dragHandle = true }) {
  const seq = chapter.seq
  const sortable = useSortable({ id: `card-${seq}`, data: { seq } })
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = sortable
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  const askSynopsis = (e) => {
    e?.stopPropagation?.()
    seedChiefNarrativeWrite(
      'outline',
      `第 ${seq} 章大纲`,
      `请更新第 ${seq} 章 synopsis。当前:\n${chapter.synopsis || '（空）'}`,
    )
  }

  const qc = chapter.qc_issues || 0
  const labelMeta = LABEL_META[chapter.label]

  return (
    <div ref={setNodeRef} style={style}
      className="relative rounded-md bg-surface/90 overflow-hidden flex flex-col shadow-[0_0_0_1px_color-mix(in_srgb,var(--color-line)_55%,transparent)] hover:shadow-[0_0_0_1px_color-mix(in_srgb,var(--color-brand)_40%,transparent)] transition-shadow">
      {/* 顶部色条(label/POV) — 薄一点 */}
      <div className="h-0.5 w-full shrink-0" style={{ background: cardColorVar(chapter, colorMode) }} />
      <div className="p-2.5 flex flex-col gap-1.5 flex-1 min-h-0">
        {/* 标题行 + 拖拽手柄 */}
        <div className="flex items-start gap-1.5">
          {dragHandle && (
            <button {...attributes} {...listeners}
              className="shrink-0 mt-0.5 text-faint hover:text-ink cursor-grab active:cursor-grabbing touch-none"
              title="拖拽重排" aria-label="拖拽重排">
              <GripVertical size={14} />
            </button>
          )}
          <button onClick={() => onOpen?.(chapter)}
            className="flex-1 min-w-0 text-left text-f14 font-semibold text-ink leading-snug hover:text-brand transition-colors cursor-pointer truncate">
            {chapterLabel(seq, chapter.title || '')}
          </button>
        </div>

        {/* synopsis:只读展示 · 点 CTA 送主编(禁止表单直填) */}
        {chapter.synopsis ? (
          <button type="button" onClick={askSynopsis} title="让主编写入/更新梗概(章级大纲)"
            data-testid="chapter-card-synopsis-seed"
            className="w-full text-left text-f12 text-faint leading-relaxed line-clamp-3 break-words cursor-pointer hover:bg-soft/40 hover:text-ink rounded-md px-1 -mx-1 py-0.5 transition-colors">
            {chapter.synopsis}
          </button>
        ) : (
          <button type="button" onClick={askSynopsis} data-testid="chapter-card-synopsis-seed"
            className="text-left text-f12 text-faint hover:text-brand cursor-pointer transition-colors px-1 -mx-1">
            + 让主编写梗概
          </button>
        )}

        {/* 角标行:字数 · POV · QC · 状态 */}
        <div className="mt-auto flex items-center gap-2 flex-wrap text-meta">
          <span className="tnum text-faint">{wcLabel(chapter.word_count)}</span>
          <span className="inline-flex items-center gap-1 text-faint" title={POV_HINT}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: cardColorVar(chapter, 'pov') }} />
            {povLabel(chapter.focalizer)}
          </span>
          {qc > 0
            ? <span className="inline-flex items-center gap-1 text-warn tnum"><TriangleAlert size={12} className="shrink-0" />{qc}</span>
            : <Check size={13} className="text-ok" />}
          <span className="ml-auto inline-flex items-center gap-0.5">
            {labelMeta && <Diamond size={11} className="shrink-0" style={{ color: `var(--color-${labelMeta.token})` }} />}
            <LabelSelect value={chapter.label} onChange={(v) => onPatchLabel?.(seq, v)} className="text-meta max-w-[76px]" />
          </span>
        </div>
      </div>
    </div>
  )
}
