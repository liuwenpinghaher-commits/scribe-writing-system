import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from './api'
import { liveTouchesChapter } from './lib/liveRefresh.js'

// 主编主动化 T2:六维脉搏条(方案 §三 感知层出口①)。
// 绿=info 安 / 黄=nudge 有建议 / 红=decision 需决策——颜色自动可见,信号不再靠作者点 tab。
// 点维度点 → 弹层(条目+「聊这个」预填右栏写作对话);tension 弹层含压力级 sparkline
// (作者自标的目标节奏,非 LLM 打分)。s3-live chapter 变更→重拉(防 stale)。
const DIM_LABEL = {
  promise: '伏笔', arc: '弧光', relation: '关系',
  tension: '张力', causal: '因果', quality: '质量',
}
const SEV_DOT = {
  info: 'bg-ok/70', nudge: 'bg-warn', decision: 'bg-danger',
}

function Sparkline({ curve }) {
  const pts = (curve || []).filter((c) => c.pressure != null)
  if (pts.length < 2) return null
  const w = 180, h = 36, max = 5
  const step = w / (pts.length - 1)
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${(h - (p.pressure / max) * h).toFixed(1)}`).join(' ')
  return (
    <div className="mt-1.5">
      <div className="text-meta text-faint mb-0.5">全书压力级(1-5,你标的目标节奏)</div>
      <svg width={w} height={h} className="block">
        <path d={d} fill="none" stroke="var(--color-brand)" strokeWidth="1.5" />
      </svg>
    </div>
  )
}

const MUTE_DIMS = ['promise', 'arc', 'relation', 'tension', 'causal', 'quality', 'stuck']

export function PulseBar({ seq, onChat }) {
  const [pulse, setPulse] = useState(null)
  const [open, setOpen] = useState(null)   // 展开的维度名
  const [muteTick, setMuteTick] = useState(0)   // R2-10:静音恢复后强制重渲染
  const [popPos, setPopPos] = useState(null)
  const wrapRef = useRef(null)
  const popRef = useRef(null)

  useEffect(() => {
    if (seq == null) { setPulse(null); return }
    let dead = false
    const pull = () => api.chapterPulse(seq).then((p) => { if (!dead) setPulse(p) }).catch(() => {})
    pull()
    const onLive = (e) => {
      if (liveTouchesChapter(e?.detail, seq)) pull()
    }
    window.addEventListener('s3-live', onLive)
    return () => { dead = true; window.removeEventListener('s3-live', onLive) }
  }, [seq])

  // 点外面关弹层（浮层 portal 到 body，不能只查 wrapRef）
  useEffect(() => {
    const onDoc = (e) => {
      if (wrapRef.current?.contains(e.target)) return
      if (popRef.current?.contains(e.target)) return
      setOpen(null)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  useLayoutEffect(() => {
    if (!open || !wrapRef.current) { setPopPos(null); return undefined }
    const place = () => {
      const r = wrapRef.current.getBoundingClientRect()
      setPopPos({ top: Math.round(r.bottom + 4), right: Math.round(window.innerWidth - r.right) })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  if (!pulse) return null
  const dims = pulse.dimensions || []
  const cur = dims.find((d) => d.dimension === open)
  const sevLabel = (s) => (s === 'decision' ? '需决策' : s === 'nudge' ? '有建议' : '安')
  return (
    <div
      ref={wrapRef}
      className="relative flex items-center shrink-0"
      data-testid="pulse-bar"
      role="group"
      aria-label="本章脉搏"
    >
      {dims.map((d) => (
        <button
          key={d.dimension}
          type="button"
          data-testid={`pulse-${d.dimension}`}
          onClick={() => setOpen(open === d.dimension ? null : d.dimension)}
          title={`${DIM_LABEL[d.dimension]} · ${sevLabel(d.severity)}`}
          aria-label={`${DIM_LABEL[d.dimension]}：${sevLabel(d.severity)}`}
          aria-pressed={open === d.dimension}
          className={`w-6 h-7 grid place-items-center rounded-md cursor-pointer hover:bg-soft ${
            open === d.dimension ? 'bg-soft' : ''
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${SEV_DOT[d.severity] || 'bg-line'}`} />
        </button>
      ))}
      {(() => {
        // R2-10:解除入口——列出本书已静音维度,一键全部恢复(此前静音后全 UI 无解除;stuck 维亦在此可恢复)
        const w = api.getWork()
        const muted = MUTE_DIMS.filter((d) => { try { return localStorage.getItem(`s3.pulse.mute.${w}.${d}`) === '1' } catch { return false } })
        if (!muted.length) return null
        return (
          <button key={`m${muteTick}`}
            onClick={() => { muted.forEach((d) => { try { localStorage.removeItem(`s3.pulse.mute.${w}.${d}`) } catch { /* */ } }); setMuteTick((t) => t + 1) }}
            title={`已静音:${muted.join('/')} — 点击全部恢复`}
            className="text-meta text-faint hover:text-ink cursor-pointer px-1">已静音{muted.length}</button>
        )
      })()}
      {cur && popPos && createPortal(
        <div
          ref={popRef}
          data-testid="pulse-popover"
          className="fixed z-[80] w-[340px] max-h-72 overflow-y-auto rounded-md border border-line bg-surface shadow-[var(--shadow-pop)] p-2.5 space-y-1.5"
          style={{ top: popPos.top, right: popPos.right }}
        >
          <div className="text-f13 font-medium text-ink">{DIM_LABEL[cur.dimension]}{cur.degraded ? '(该维降级:没查≠没病)' : ''}</div>
          {cur.items.map((it, i) => (
            <div key={i} className="text-f13 leading-snug border-b border-line/40 last:border-0 pb-1.5 last:pb-0">
              <div className={it.severity === 'decision' ? 'text-danger' : it.severity === 'nudge' ? 'text-warn' : 'text-faint'}>
                {it.message}
              </div>
              {it.action?.kind === 'chat' && (
                <button onClick={() => { onChat?.(it.action.payload); setOpen(null) }}
                  className="mt-0.5 text-meta text-brand hover:underline cursor-pointer">跟主编聊这个 →</button>
              )}
            </div>
          ))}
          {cur.dimension === 'tension' && <Sparkline curve={cur.curve} />}
        </div>,
        document.body,
      )}
    </div>
  )
}
