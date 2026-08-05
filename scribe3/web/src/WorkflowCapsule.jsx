import { useCallback, useEffect, useState } from 'react'
import { Compass } from 'lucide-react'
import { api } from './api'

/**
 * 顶栏进度胶囊：与 /workflow/snapshot 同源。
 * onOpenJourney → 打开旅程视图；onContinue(snap) → 预填聊天并跟焦。
 */
export function WorkflowCapsule({ work, onOpenJourney, onContinue }) {
  const [snap, setSnap] = useState(null)

  const load = useCallback(() => {
    if (!work) { setSnap(null); return undefined }
    let dead = false
    api.workflowSnapshot()
      .then((s) => { if (!dead) setSnap(s) })
      .catch(() => { if (!dead) setSnap(null) })
    return () => { dead = true }
  }, [work])

  useEffect(() => {
    const cleanup = load()
    const t = setInterval(() => { load() }, 12000)
    const onLive = () => { load() }
    window.addEventListener('s3-live', onLive)
    return () => {
      cleanup?.()
      clearInterval(t)
      window.removeEventListener('s3-live', onLive)
    }
  }, [load])

  if (!work || !snap?.next_step) return null

  const lane = snap.chapter_lane
  const next = snap.next_step
  const station = snap.journey?.current_station
  const stationLabel = (snap.journey?.stations || []).find((s) => s.id === station)?.label || '旅程'
  const chapterBit = lane
    ? `第${lane.seq}章 · ${lane.pilot_state_label || lane.pilot_state}`
    : stationLabel

  return (
    <div
      data-testid="workflow-capsule"
      className="hidden md:flex items-center gap-1.5 max-w-[min(42rem,46vw)] min-w-0 text-meta"
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

/** 执行 ui_directive + 预填主编（P0） */
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
}
