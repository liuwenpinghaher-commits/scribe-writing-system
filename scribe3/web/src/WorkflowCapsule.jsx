import { useCallback, useEffect, useRef, useState } from 'react'
import { Compass } from 'lucide-react'
import { api } from './api'
import { liveTouchesTable } from './lib/liveRefresh.js'
import { domainHintFromNext, maybeToastRollback } from './lib/pilotRollback.js'

/** 影响旅程/胶囊 next_step 的表（其它 LIVE 不重拉） */
const WORKFLOW_LIVE_TABLES = [
  'chapter', 'pilot_state', 'promise', 'outline', 'beats',
  'chapter_scorecard', 'manuscript', 'volume',
]

/**
 * 顶栏进度胶囊：与 /workflow/snapshot 同源。
 * onOpenJourney → 打开旅程视图；onContinue(snap) → 预填聊天并跟焦。
 */
export function WorkflowCapsule({ work, onOpenJourney, onContinue }) {
  const [snap, setSnap] = useState(null)
  const [stale, setStale] = useState(false)
  const failRef = useRef(0)
  const timerRef = useRef(null)
  const deadRef = useRef(false)

  const schedule = useCallback((ms) => {
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => { loadRef.current?.() }, ms)
  }, [])

  const load = useCallback(() => {
    if (!work || typeof api.workflowSnapshot !== 'function') { setSnap(null); setStale(false); return }
    api.workflowSnapshot()
      .then((s) => {
        if (deadRef.current) return
        failRef.current = 0
        setStale(false)
        setSnap(s)
        maybeToastRollback(s)
        schedule(12000)
      })
      .catch(() => {
        if (deadRef.current) return
        failRef.current += 1
        setStale(true)
        const wait = Math.min(48000, 12000 * (2 ** Math.min(failRef.current, 2)))
        schedule(wait)
      })
  }, [work, schedule])
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    deadRef.current = false
    failRef.current = 0
    load()
    const onLive = (e) => {
      if (liveTouchesTable(e?.detail, WORKFLOW_LIVE_TABLES)) load()
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      deadRef.current = true
      clearTimeout(timerRef.current)
      window.removeEventListener('s3-live', onLive)
    }
  }, [load])

  if (!work) return null
  if (!snap?.next_step) {
    if (!stale) return null
    return (
      <div
        data-testid="workflow-capsule-stale"
        className="hidden md:flex items-center gap-1.5 text-meta text-faint/70"
        title="进度暂时连不上，过一会儿会再试"
      >
        <Compass size={13} className="shrink-0" />
        进度暂时连不上
      </div>
    )
  }

  const lane = snap.chapter_lane
  const next = snap.next_step
  const station = snap.journey?.current_station
  const stationLabel = (snap.journey?.stations || []).find((s) => s.id === station)?.label || '旅程'
  const chapterBit = lane
    ? `第${lane.seq}章 · ${lane.pilot_state_label || lane.pilot_state}`
    : stationLabel
  const suggestions = Array.isArray(snap.creative_suggestions)
    ? snap.creative_suggestions
    : (Array.isArray(next?.creative_suggestions) ? next.creative_suggestions : [])
  const tip0 = suggestions[0]

  return (
    <div
      data-testid="workflow-capsule"
      className={`hidden md:flex items-center gap-1.5 max-w-[min(42rem,46vw)] min-w-0 text-meta ${stale ? 'opacity-60' : ''}`}
      title={stale ? '进度可能过时，网络不稳' : undefined}
    >
      <button
        type="button"
        onClick={onOpenJourney}
        title="打开写作旅程"
        className="flex items-center gap-1.5 min-w-0 px-2 py-1 rounded-md text-faint hover:text-ink hover:bg-soft cursor-pointer"
      >
        <Compass size={13} className="shrink-0 text-brand" />
        <span className="truncate">
          <span className="text-faint">{stationLabel}</span>
          <span className="mx-1 text-faint/40">·</span>
          <span className="text-ink/80">{chapterBit}</span>
          <span className="mx-1 text-faint/40">→</span>
          <span className="text-brand font-medium">{next.title}</span>
        </span>
      </button>
      {tip0?.title && (
        <span
          data-testid="workflow-creative-suggestion"
          className="hidden lg:inline truncate max-w-[12rem] text-faint/90 px-1.5 py-0.5 rounded bg-soft border border-line"
          title={[tip0.detail, tip0.kind].filter(Boolean).join(' · ')}
        >
          💡 {tip0.title}
        </span>
      )}
      <button
        type="button"
        data-testid="workflow-capsule-continue"
        onClick={() => onContinue?.(snap)}
        className="shrink-0 h-7 px-2 rounded-md bg-brand/15 text-brand hover:bg-brand/25 font-medium cursor-pointer"
      >
        继续
      </button>
    </div>
  )
}

/** 执行 ui_directive + 预填主编；并 resolve 工作包（旅程继续 → 编排）。 */
export function applyWorkflowContinue(snap, { onSel, onJumpChapter } = {}) {
  if (!snap) return
  const prompt = snap.suggested_prompt || ''
  const ui = snap.ui_directive || {}
  const node = ui.node
  try {
    if (prompt) {
      sessionStorage.setItem('s3.chief.seed', prompt)
      window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: prompt }))
    }
  } catch { /* */ }
  try {
    window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: ui.right_tab || 'chief' }))
  } catch { /* */ }
  const seq = node?.ref ?? snap.chapter_lane?.seq
  const phase = ui.phase || snap.chapter_lane?.phase_hint
  if (seq != null) {
    onJumpChapter?.(Number(seq))
    onSel?.({
      mode: 'node',
      node: {
        id: node?.id || `ch:${seq}`,
        type: 'chapter',
        ref: Number(seq),
        label: node?.label || `${seq}`,
      },
    })
    if (phase) {
      try {
        window.dispatchEvent(new CustomEvent('s3-chapter-phase', { detail: { phase, seq: Number(seq) } }))
      } catch { /* */ }
    }
  }
  // 旅程下一步 → 激活编排工作包（async，不阻塞 UI）
  import('./lib/orchestrateSend.js').then(({ orchestrateBeforeSend }) => {
    const domainHint = snap.next_step?.domain
      || domainHintFromNext(snap.next_step?.id, phase)
    return orchestrateBeforeSend(prompt || '继续', {
      chapter: seq != null ? Number(seq) : null,
      phase: phase || '',
      action: 'create',
      journey_next_domain: domainHint,
      applyFocus: true,
      onSel,
    })
  }).catch(() => {})
}
