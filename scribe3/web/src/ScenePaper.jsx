import { seedChapterScene } from './lib/chiefSeed.js'
import { scenePaperView, loadEvidenceMustShow } from './lib/scenePaper.js'

/**
 * 只读场面纸。不定格、不手填、不调 patchChapter。
 * 按钮只「跟主编定这场」。
 */
export function ScenePaper({ chapter, seq, suggest }) {
  const view = scenePaperView({ ...(chapter || {}), seq })
  const sug = suggest || chapter?.scene_suggest || {}
  const lock = sug.lock_warnings || []
  const draft = sug.draft || {}
  const candidates = sug.candidates || {}
  const traces = view.traces.length ? view.traces : loadEvidenceMustShow(chapter || {})
  return (
    <section
      className="shrink-0 border-b border-brand/30 bg-brand/5 px-3 py-1"
      data-testid="scene-paper"
    >
      <details className="text-f12 text-ink" data-testid="scene-paper-expand">
        <summary className="cursor-pointer list-none flex items-center gap-2 min-w-0 [&::-webkit-details-marker]:hidden">
          <span className="text-meta text-faint shrink-0">场面纸</span>
          <span className="min-w-0 truncate text-ink">
            日子 {view.day || '未标'} · {view.mustHappen || '尚未写必须发生'}
            {view.trace ? ` · 痕迹 ${view.trace}` : ''}
          </span>
          <span className="ml-auto shrink-0 text-meta text-faint">展开</span>
        </summary>
        <div className="mt-1.5 space-y-0.5 text-f13">
          <div>日子：{view.day}</div>
          <div>必须发生：{view.mustHappen || '尚未写必须发生'}</div>
          <div>痕迹：{view.trace || '尚未标痕迹'}</div>
          <div>欲望：{view.desire || '（空）'}</div>
          <div>阻力：{view.obstacle || '（空）'}</div>
          <div>回合：{view.turn || '（空）'}</div>
          <div>代价：{view.cost || '（空）'}</div>
          {traces.length > 1 ? (
            <div>痕迹：{traces.join('；')}</div>
          ) : null}
          <p className="text-faint">要宣称本章戏成立 / 交给无人值守，还需要阻力与代价。</p>
          {sug.needs_author ? (
            <p className="text-warn">材料不够定这场，跟主编说人话，不要凑字。</p>
          ) : null}
          {lock.length ? (
            <ul className="text-warn list-disc pl-4">
              {lock.map((w) => (
                <li key={w.code || w.message}>{w.message || w.code}</li>
              ))}
            </ul>
          ) : null}
          {draft && (draft.desire || draft.turn) ? (
            <p className="text-faint">建议草稿（不是已落库）：{draft.turn || draft.desire}</p>
          ) : null}
          {Array.isArray(candidates.turn) && candidates.turn.length ? (
            <p className="text-faint">候选回合：{candidates.turn.slice(0, 3).map((c) => c.text).join(' / ')}</p>
          ) : null}
          <button
            type="button"
            data-testid="scene-paper-ask-chief"
            className="mt-2 h-7 px-2 rounded-lg border border-brand/40 bg-canvas text-f12 text-brand hover:bg-brand/10 cursor-pointer"
            onClick={() => seedChapterScene(seq)}
          >
            跟主编定这场
          </button>
        </div>
      </details>
    </section>
  )
}
