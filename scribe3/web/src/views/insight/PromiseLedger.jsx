import { useEffect, useState } from 'react'
import { Bookmark, Target, CheckCircle2, EyeOff, ArrowRight, AlertTriangle } from 'lucide-react'
import { api } from '../../api'
import { useSelection } from '../../selectionContext'
import { seedChiefCodexWrite } from '../../lib/chiefSeed.js'
import { seedInsightNextStroke } from '../../lib/insightChiefSeed.js'
import { liveTouchesTable } from '../../lib/liveRefresh.js'
import { promiseEmptyCopy, promiseEmptyKind } from '../../lib/insightReadable.js'
import { ErrorState } from './InsightBits.jsx'

function PromiseSpanBar({ setupChapter, payoffChapter, maxChapter, clues = [] }) {
  if (setupChapter == null || payoffChapter == null || maxChapter == null || maxChapter <= 0) return null
  const total = Math.max(maxChapter, payoffChapter)
  const setupPct = Math.max(0, Math.min(100, (setupChapter / total) * 100))
  const payoffPct = Math.max(0, Math.min(100, (payoffChapter / total) * 100))
  const widthPct = Math.max(1, payoffPct - setupPct)
  return (
    <div className="relative h-2 mt-1.5 mb-0.5 rounded-full bg-soft overflow-hidden">
      <div className="absolute top-0 h-full rounded-full bg-ok/60" style={{ left: `${setupPct}%`, width: `${widthPct}%` }} />
      <div className="absolute top-0 h-full w-[3px] rounded-full bg-faint" style={{ left: `${setupPct}%` }} />
      <div className="absolute top-0 h-full w-[3px] rounded-full bg-ok" style={{ left: `calc(${payoffPct}% - 3px)` }} />
      {clues.map((cl, i) => {
        const clPct = Math.max(0, Math.min(100, (cl.chapter / total) * 100))
        return (
          <div key={i} title={`第${cl.chapter}章: ${cl.note}`} className="absolute top-0 h-full w-[3px] rounded-full bg-fore/70 cursor-help" style={{ left: `calc(${clPct}% - 1px)` }} />
        )
      })}
    </div>
  )
}

function PromiseOpenBar({ setupChapter, maxChapter, clues = [] }) {
  if (setupChapter == null || maxChapter == null || maxChapter <= 0) return null
  const total = maxChapter
  const setupPct = Math.max(0, Math.min(100, (setupChapter / total) * 100))
  const widthPct = Math.max(1, 100 - setupPct)
  return (
    <div className="relative h-1.5 mt-1.5 mb-0.5 rounded-full bg-soft overflow-hidden">
      <div className="absolute top-0 h-full rounded-full bg-fore/30" style={{ left: `${setupPct}%`, width: `${widthPct}%` }} />
      <div className="absolute top-0 h-full w-[3px] rounded-full bg-fore" style={{ left: `${setupPct}%` }} />
      {clues.map((cl, i) => {
        const clPct = Math.max(0, Math.min(100, (cl.chapter / total) * 100))
        return (
          <div key={i} title={`第${cl.chapter}章: ${cl.note}`} className="absolute top-0 h-full w-[3px] rounded-full bg-fore/80 cursor-help" style={{ left: `calc(${clPct}% - 1px)` }} />
        )
      })}
    </div>
  )
}

function PromiseCard({ p, maxChapter, onJumpChapter, showNextStroke }) {
  const overdue = p.overdue
  const clues = p.clues || []
  const seedPromise = (hint) => seedChiefCodexWrite('promises', p, hint)
  const { setFocus, suppressNextMirror } = useSelection()
  const focusMe = () => setFocus({
    type: 'promise', id: p.id, label: p.text || '',
    payload: { setup_chapter: p.setup_chapter, payoff_chapter: p.payoff_chapter, status: p.status, overdue: !!p.overdue },
    origin: 'insight',
  })
  const jump = (ch, missing) => {
    if (missing || ch == null || !onJumpChapter) return
    suppressNextMirror()
    onJumpChapter(ch)
  }

  return (
    <div onClick={focusMe} title="聚焦此伏笔" data-testid="insight-promise-card"
      className={`rounded-lg p-2.5 text-f12 cursor-pointer transition-colors ${overdue ? 'bg-danger/5 hover:bg-danger/10' : 'hover:bg-soft/50'}`}>
      <div className="flex items-start gap-1.5">
        <span className={`mt-[3px] w-1.5 h-1.5 rounded-full shrink-0 ${overdue ? 'bg-danger' : p.status === 'closed' ? 'bg-ok' : 'bg-faint'}`} />
        <span className="text-ink flex-1 leading-snug">{p.text || '(无描述)'}</span>
        {overdue && <span className="text-danger text-meta font-medium shrink-0">超期</span>}
      </div>
      {p.status === 'closed' && p.payoff_chapter != null && (
        <PromiseSpanBar setupChapter={p.setup_chapter} payoffChapter={p.payoff_chapter} maxChapter={maxChapter} clues={clues} />
      )}
      {p.status !== 'closed' && p.setup_chapter != null && (
        <PromiseOpenBar setupChapter={p.setup_chapter} maxChapter={maxChapter} clues={clues} />
      )}
      <div className="text-faint text-meta mt-1 pl-3 flex flex-wrap gap-x-2">
        {p.setup_chapter != null && (
          p.setup_missing ? (
            <span className="text-danger" data-testid="insight-setup-missing">埋:第{p.setup_chapter}章 · 原章已删</span>
          ) : (
            <button type="button" className="hover:text-brand cursor-pointer underline-offset-2 hover:underline transition-colors"
              onClick={(e) => { e.stopPropagation(); jump(p.setup_chapter, false) }}>
              埋:第{p.setup_chapter}章
            </button>
          )
        )}
        {p.payoff_chapter != null && (
          <>
            <ArrowRight size={10} className="self-center text-faint" />
            <button type="button" className="text-ok hover:text-ok/70 cursor-pointer underline-offset-2 hover:underline transition-colors"
              onClick={(e) => { e.stopPropagation(); jump(p.payoff_chapter) }}>
              收:第{p.payoff_chapter}章{p.span != null ? ` · 跨${p.span}章` : ''}
            </button>
          </>
        )}
        {p.payoff_chapter == null && p.chapters_open != null && <span>开口{p.chapters_open}章</span>}
      </div>
      {clues.length > 0 && (
        <div className="pl-3 mt-1.5 space-y-0.5">
          {clues.map((cl, i) => (
            <div key={i} className="flex items-start gap-1 text-meta text-faint">
              <button type="button" className="hover:text-brand underline-offset-2 hover:underline shrink-0 cursor-pointer"
                onClick={(e) => { e.stopPropagation(); jump(cl.chapter) }} title={`跳到第${cl.chapter}章`}>
                ▲第{cl.chapter}章
              </button>
              <span className="flex-1 leading-snug">{cl.note}</span>
            </div>
          ))}
        </div>
      )}
      <div className="pl-3 mt-1.5 flex flex-wrap items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
        {showNextStroke && (
          <button type="button" data-testid="insight-next-stroke"
            onClick={() => seedInsightNextStroke(p, { kind: 'promise', chapter: p.setup_chapter })}
            className="text-meta px-2 py-0.5 rounded border border-line text-ink hover:border-brand cursor-pointer">
            针对这条体检写下一笔
          </button>
        )}
        <button type="button"
          onClick={() => seedPromise('请为此伏笔添加/维护草蛇灰线线索,提交写入提案。')}
          className="text-meta text-faint hover:text-fore transition-colors cursor-pointer">
          让主编维护线索
        </button>
        {p.status !== 'closed' && p.kind !== 'red_herring' && (
          <>
            <button type="button"
              onClick={() => seedPromise('请回收/兑现此伏笔并提交写入提案(含 payoff 章)。')}
              className="text-meta px-2 py-0.5 rounded border border-ok/40 text-ok hover:bg-ok/10 transition-colors cursor-pointer">
              让主编回收
            </button>
            <button type="button"
              onClick={() => seedPromise('请将此伏笔标为障眼法(弃置),提交写入提案。')}
              className="text-meta px-2 py-0.5 rounded border border-line text-faint hover:bg-soft hover:text-ink transition-colors cursor-pointer">
              让主编标障眼法
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function LedgerColumn({ icon: Icon, label, tone, rows, maxChapter, onJumpChapter, empty, showNextStroke }) {
  const c = { fore: 'text-fore', ok: 'text-ok', faint: 'text-faint' }[tone]
  return (
    <div className="min-w-0">
      <div className={`flex items-center gap-1.5 text-meta font-semibold uppercase tracking-wider mb-3 ${c}`}>
        <Icon size={14} />{label} <span className="text-faint font-normal normal-case tracking-normal">({rows.length})</span>
      </div>
      <div className="space-y-2">
        {rows.length === 0 ? <div className="text-faint text-f12">{empty || '—'}</div>
          : rows.map((p) => (
            <PromiseCard
              key={p.id} p={p}
              maxChapter={maxChapter}
              onJumpChapter={onJumpChapter}
              showNextStroke={showNextStroke}
            />
          ))}
      </div>
    </div>
  )
}

export function usePromiseLedger() {
  const [led, setLed] = useState(null)
  const [ledErr, setLedErr] = useState(null)
  const [ledKey, setLedKey] = useState(0)
  const refresh = () => setLedKey((k) => k + 1)
  useEffect(() => {
    api.promisesLedger().then((r) => { setLed(r); setLedErr(null) })
      .catch((e) => { setLed(null); setLedErr(e?.body?.detail || e?.message || '伏笔台账加载失败') })
  }, [ledKey])
  useEffect(() => {
    const onLive = (e) => {
      if (liveTouchesTable(e?.detail, ['promise', 'foreshadow', 'chapter', 'daily_progress'])) {
        setLedKey((k) => k + 1)
      }
    }
    window.addEventListener('s3-live', onLive)
    return () => window.removeEventListener('s3-live', onLive)
  }, [])
  return { led, ledErr, refresh }
}

export function OpenPromiseStrip({ led, ledErr, onJumpChapter }) {
  const kind = promiseEmptyKind({ led, ledErr })
  const copy = promiseEmptyCopy(kind)
  const open = led?.open || []
  return (
    <div className="mb-5" data-testid="insight-open-promises">
      <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">未收的账</div>
      {kind && kind !== 'loading' ? (
        <div data-testid="insight-open-empty">
          <div className="text-f13 text-ink">{copy.title}</div>
          <div className="text-meta text-faint mt-0.5">{copy.body}</div>
        </div>
      ) : (
        <div className="space-y-2">
          {open.slice(0, 6).map((p) => (
            <PromiseCard key={p.id} p={p} maxChapter={led?.max_chapter} onJumpChapter={onJumpChapter} showNextStroke />
          ))}
        </div>
      )}
    </div>
  )
}

export function PromiseLedger({ led, ledErr, onJumpChapter, onRetry }) {
  if (ledErr) return (
    <div className="mb-6 pb-5 border-b border-line/60">
      <ErrorState message={ledErr || '伏笔台账加载失败'} onRetry={onRetry} />
    </div>
  )
  if (!led) return null
  const a = led.audit || {}
  const pws = (a.payoff_without_setup || []).length + (a.closed_without_setup || []).length
  const balanced = a.balanced
  const openEmpty = promiseEmptyCopy('no_open').title
  return (
    <div className="mb-6 pb-5 border-b border-line/60">
      <div className="flex items-center flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-2"><Bookmark size={16} className="text-fore" /><h2 className="type-section text-ink">伏笔台账</h2></div>
        <span className="text-meta text-faint">阈值 {led.threshold} 章 · 现在第 {led.max_chapter} 章</span>
        <div className="ml-auto flex items-center gap-2 text-meta">
          <span className={`inline-flex items-center gap-1 ${balanced ? 'text-ok' : 'text-danger'}`}>{balanced ? '✓ 已平衡' : <><AlertTriangle size={11} />未平衡</>}</span>
          <span className="text-faint">超期 {a.overdue_count ?? 0} · 闭无开 {pws} · 契诃夫 {a.never_paid ?? 0} 把枪没响</span>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <LedgerColumn icon={Target} label="已埋未收" tone="fore" rows={led.open || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} empty={openEmpty} showNextStroke />
        <LedgerColumn icon={CheckCircle2} label="已回收" tone="ok" rows={led.closed || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} />
        <LedgerColumn icon={EyeOff} label="障眼法" tone="faint" rows={led.red_herring || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} />
      </div>
      {pws > 0 && (
        <div className="mt-3 text-meta text-danger">
          <AlertTriangle size={11} className="inline align-[-1px] mr-0.5" />闭无开(回收早于埋设,疑似凭空 payoff):
          {[...(a.payoff_without_setup || []), ...(a.closed_without_setup || [])]
            .map((x) => `「${x.text}」(埋${x.setup_chapter ?? '?'}→收${x.payoff_chapter})`).join('、')}
        </div>
      )}
    </div>
  )
}
