import { useEffect, useRef, useState } from 'react'
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
  const wrapRef = useRef(null)

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

  // 点外面关弹层
  useEffect(() => {
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(null) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  if (!pulse) return null
  const dims = pulse.dimensions || []
  const cur = dims.find((d) => d.dimension === open)
  return (
    <div ref={wrapRef} className="relative flex items-center gap-2.5 px-2 h-7 shrink-0">
      {dims.map((d) => (
        <button key={d.dimension} data-testid={`pulse-${d.dimension}`}
          onClick={() => setOpen(open === d.dimension ? null : d.dimension)}
          title={`${DIM_LABEL[d.dimension]}:${d.severity === 'decision' ? '需决策' : d.severity === 'nudge' ? '有建议' : '安'}`}
          className="flex items-center gap-1 text-meta text-faint hover:text-ink cursor-pointer">
          <span className={`w-2 h-2 rounded-full ${SEV_DOT[d.severity] || 'bg-line'}`} />
          {DIM_LABEL[d.dimension]}
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
            className="text-meta text-faint hover:text-ink cursor-pointer">🔕{muted.length}</button>
        )
      })()}
      {cur && (
        <div className="absolute left-0 top-full mt-1 z-30 w-[340px] max-h-72 overflow-y-auto rounded-md border border-line bg-surface shadow-lg p-2.5 space-y-1.5">
          <div className="text-f12 font-medium text-ink">{DIM_LABEL[cur.dimension]}{cur.degraded ? '(该维降级:没查≠没病)' : ''}</div>
          {cur.items.map((it, i) => (
            <div key={i} className="text-f12 leading-snug border-b border-line/40 last:border-0 pb-1.5 last:pb-0">
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
        </div>
      )}
    </div>
  )
}
