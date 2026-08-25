import { useState } from 'react'
import { X, CornerDownRight } from 'lucide-react'
import { api } from '../../api'
import { relColor, relLabel } from '../../lib/relColors'
import { showToast } from '../../ui/Toast.jsx'
import { withFeedback } from '../../lib/withFeedback.js'
import { seedTimelineNextStroke } from '../../lib/timelineChiefSeed.js'
import {
  palette, evColor, arcColor, PROMISE_COLOR, PROMISE_HERRING, stripRole,
} from './timelineTokens.js'

export function timelineTarget(raw, cat) {
  const ch = raw?._jump ?? raw?.story_chapter ?? raw?.chapter
  if (cat === 'promise') {
    const id = raw?.id ? (String(raw.id).startsWith('promise:') ? raw.id : `promise:${raw.id}`) : ''
    return { id, type: 'promise', label: raw?.label || '伏笔', chapter: ch, ref: 'open' }
  }
  if (cat === 'relation') {
    return { id: raw?.id || '', type: 'relation', label: raw?.label || raw?.refs?.relation || '关系', chapter: ch }
  }
  if (cat === 'faction') {
    return { id: raw?.id || '', type: 'faction', label: raw?.refs?.faction || raw?.label || '势力', chapter: ch }
  }
  return { id: raw?.id || '', type: 'event', label: raw?.label || raw?.event_type || '事件', chapter: ch }
}

function Field({ k, v }) {
  if (v == null || v === '' || (Array.isArray(v) && !v.length)) return null
  const val = Array.isArray(v) ? v.map(stripRole).join('、') : String(v)
  return (
    <div className="flex gap-2 text-f12 leading-relaxed">
      <span className="shrink-0 w-16 text-faint">{k}</span>
      <span className="text-ink break-words min-w-0">{val}</span>
    </div>
  )
}

function CausalRootEditor({ eventId, initial }) {
  const [v, setV] = useState(initial || '')
  const [busy, setBusy] = useState(false)
  if (!eventId) return null
  return (
    <div className="mt-2">
      <div className="text-meta text-faint mb-1">因果根（为什么发生）</div>
      <textarea className="w-full text-f12 border border-line rounded-md px-2 py-1 bg-canvas" rows={2}
        value={v} onChange={(e) => setV(e.target.value)} />
      <button type="button" disabled={busy}
        className="mt-1 text-f12 px-2 py-1 rounded border border-line hover:bg-soft cursor-pointer"
        onClick={async () => {
          setBusy(true)
          try {
            await api.patchEventCausalRoot(eventId, v)
            showToast('因果根已保存', { tone: 'ok' })
          } catch (e) {
            showToast('保存失败: ' + (e?.body?.detail || e?.message || '未知错误'), { tone: 'danger' })
          } finally { setBusy(false) }
        }}>保存因果根</button>
    </div>
  )
}

function PromiseActions({ raw, defaultChapter, onDone }) {
  const [payoff, setPayoff] = useState(String(defaultChapter || raw?.chapter || ''))
  const [busy, setBusy] = useState(false)
  const pid = String(raw?.id || '').replace(/^promise:/, '')
  const st = raw?.refs?.status
  const closed = !!(raw?._payoff || st === 'closed' || st === 'abandoned')
  if (!pid || closed) return null
  const run = async (fn, ok) => {
    setBusy(true)
    try {
      await withFeedback(fn(), { ok, fail: '没做成' })
      onDone?.()
    } finally { setBusy(false) }
  }
  return (
    <div className="mt-2 space-y-1.5" data-testid="timeline-promise-actions">
      <div className="flex items-center gap-1">
        <input
          type="number"
          min={1}
          className="w-16 h-7 px-1.5 text-f12 border border-line rounded-md bg-canvas"
          value={payoff}
          onChange={(e) => setPayoff(e.target.value)}
          aria-label="兑现章号"
        />
        <button type="button" disabled={busy}
          className="h-7 px-2 rounded-md text-f12 bg-brand/15 text-brand cursor-pointer disabled:opacity-40"
          onClick={() => run(() => api.advancePromise(pid, Number(payoff) || Number(raw.chapter) || 1), '已兑现')}>
          兑现
        </button>
      </div>
      <div className="flex gap-1">
        <button type="button" disabled={busy}
          className="h-7 px-2 rounded-md text-f12 border border-line cursor-pointer disabled:opacity-40"
          onClick={() => run(() => api.abandonPromise(pid), '已弃置')}>
          弃置
        </button>
        <button type="button" disabled={busy}
          className="h-7 px-2 rounded-md text-f12 border border-line cursor-pointer disabled:opacity-40"
          onClick={() => run(() => api.markHerring(pid), '已标障眼法')}>
          标障眼法
        </button>
      </div>
    </div>
  )
}

export function TimelineDetailPanel({ raw, cat, onJump, onNavigate, onClose, onChanged, defaultChapter }) {
  if (!raw) return null
  const r = raw.refs || {}
  const sc = raw.story_chapter ?? raw.chapter
  const np = raw.narrative_position
  let title = '', headColor = palette().faint, body = null

  if (cat === 'event') {
    title = raw.label || raw.event_type; headColor = evColor(raw.event_type)
    body = (
      <>
        <Field k="类型" v={raw.event_type} />
        <Field k="故事章" v={sc} />
        {np != null && np !== sc && <Field k="叙事位" v={np} />}
        <Field k="主体" v={r.subj} />
        <Field k="客体" v={r.obj} />
        <Field k="见证" v={r.witness} />
        <Field k="目标" v={raw.goal} />
        <Field k="地点" v={r.location} />
        <Field k="效果" v={r.effects} />
        <Field k="因果前驱" v={(r.causal_in || []).map((c) => (typeof c === 'string' ? c : `${c.id}${c.chapter != null ? '(ch' + c.chapter + ')' : ''}`))} />
        <CausalRootEditor eventId={raw.id || r.id} initial={raw.causal_root_reason || r.causal_root_reason || ''} />
      </>
    )
  } else if (cat === 'arc') {
    title = raw.label || '弧光'; headColor = arcColor(r.change_type)
    body = (
      <>
        <Field k="章号" v={raw.chapter} />
        <Field k="质变类型" v={r.change_type} />
        <Field k="弧光阶段" v={r.arc_phase} />
        <Field k="角色" v={r.character ? stripRole(r.character) : null} />
        <Field k="影响声音" v={r.affects_voice ? '是' : null} />
        <Field k="摘要" v={raw.label} />
      </>
    )
  } else if (cat === 'promise') {
    title = raw.label || '伏笔'; headColor = r.promise_kind === 'red_herring' ? PROMISE_HERRING() : PROMISE_COLOR()
    const payoff = raw._payoff
    body = (
      <>
        <Field k="文本" v={raw.label} />
        <Field k="埋设章" v={raw.chapter} />
        <Field k="收束章" v={payoff?.chapter ?? r.payoff_chapter} />
        <Field k="状态" v={r.status} />
        <Field k="种类" v={r.promise_kind === 'red_herring' ? '障眼法' : r.promise_kind} />
        {r.overdue && !payoff && <Field k="提示" v="超期未收" />}
        <PromiseActions raw={raw} defaultChapter={defaultChapter} onDone={onChanged} />
      </>
    )
  } else if (cat === 'faction') {
    title = raw.label || r.faction || '势力'; headColor = palette().irony
    body = (
      <>
        <Field k="势力" v={r.faction} />
        <Field k="章号" v={raw.chapter} />
        <Field k="大事" v={r.event || raw.label} />
      </>
    )
  } else if (cat === 'relation') {
    title = relLabel(r.relation || raw.label); headColor = relColor(r.relation || raw.label)
    const end = raw._end
    body = (
      <>
        <Field k="关系" v={relLabel(r.relation || raw.label)} />
        <Field k="源" v={r.src ? stripRole(r.src) : null} />
        <Field k="目标" v={r.dst ? stripRole(r.dst) : null} />
        <Field k="建立章" v={raw.chapter} />
        <Field k="失效章" v={end?.chapter ?? r.until_chapter} />
        <Field k="备注" v={r.note} />
      </>
    )
  }

  const jumpCh = raw._jump ?? raw.chapter

  return (
    <div className="w-64 shrink-0 border-l border-line bg-surface flex flex-col" data-testid="timeline-detail">
      <div className="flex items-center gap-2 px-3 h-10 border-b border-line">
        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: headColor }} />
        <span className="text-f13 font-semibold text-ink truncate flex-1" title={title}>{title}</span>
        <button type="button" onClick={onClose} className="shrink-0 text-faint hover:text-ink cursor-pointer" title="关闭">
          <X size={14} />
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-auto px-3 py-3 flex flex-col gap-1.5">{body}</div>
      <div className="shrink-0 border-t border-line p-2 flex flex-col gap-1.5">
        <button
          type="button"
          onClick={() => {
            if (onNavigate) onNavigate(timelineTarget(raw, cat))
            else onJump?.(jumpCh)
          }}
          className="w-full h-8 rounded-lg bg-brand text-brandfg text-f12 font-medium cursor-pointer hover:opacity-85 flex items-center justify-center gap-1.5"
        >
          <CornerDownRight size={13} /> 跳到第{jumpCh}章
        </button>
        <button
          type="button"
          data-testid="timeline-next-stroke"
          onClick={() => seedTimelineNextStroke(raw, { cat, chapter: jumpCh })}
          className="w-full h-8 rounded-lg border border-line text-f12 text-ink hover:border-brand cursor-pointer"
        >
          围绕这件事写下一笔
        </button>
      </div>
    </div>
  )
}
