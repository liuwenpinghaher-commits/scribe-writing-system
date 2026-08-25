import { chapterLabel } from '../../chapterLabel.js'
import { seedInsightNextStroke } from '../../lib/insightChiefSeed.js'
import {
  rankWeakChapters,
  weakChapterEmptyCopy,
  weakChapterEmptyKind,
} from '../../lib/insightReadable.js'

export function WeakChapterList({ chapters, qErr, cacheStale, currentChapter, onNavigateToObject }) {
  const kind = weakChapterEmptyKind({ qErr, cacheStale, chapters })
  const copy = weakChapterEmptyCopy(kind)
  const weak = kind ? [] : rankWeakChapters(chapters, { currentChapter })
  const cur = Number(currentChapter)

  return (
    <div className="mb-5" data-testid="insight-weak-list">
      <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">弱章诊断</div>
      {kind ? (
        <div data-testid="insight-weak-empty">
          <div className="text-f13 text-ink">{copy.title}</div>
          <div className="text-meta text-faint mt-0.5">{copy.body}</div>
        </div>
      ) : weak.map((c) => {
        const title = chapterLabel(c.seq, c.title)
        const isCurrent = Number.isFinite(cur) && Number(c.seq) === cur
        return (
          <div key={c.seq} className="flex w-full items-center gap-2 py-1.5 border-b border-line/50 last:border-0">
            <button
              type="button"
              onClick={() => onNavigateToObject?.({
                type: 'weak_chapter',
                id: `quality:${c.seq}`,
                chapter: c.seq,
                title: `${title} · 弱章诊断`,
                reason: `该章有 ${c.qc_issues || 0} 个 QC 问题、${c.causal || 0} 个因果问题。`,
                target_node: { id: `ch:${c.seq}`, type: 'chapter', ref: c.seq, label: title },
              })}
              className="flex min-w-0 flex-1 items-center gap-2 text-left text-f13 hover:bg-soft/60 cursor-pointer"
            >
              <span className="text-ink flex-1 truncate">{title}</span>
              {isCurrent && <span className="text-meta text-brand shrink-0">当前章</span>}
              {c.qc_issues > 0 && <span className="text-danger text-f12 shrink-0">QC {c.qc_issues}</span>}
              {c.causal > 0 && <span className="text-fore text-f12 shrink-0">因果 {c.causal}</span>}
            </button>
            <button
              type="button"
              data-testid="insight-next-stroke"
              onClick={() => seedInsightNextStroke(c, { kind: 'weak_chapter', chapter: c.seq })}
              className="shrink-0 h-7 px-2 rounded-md border border-line text-meta text-ink hover:border-brand cursor-pointer"
            >
              针对这条体检写下一笔
            </button>
          </div>
        )
      })}
    </div>
  )
}
