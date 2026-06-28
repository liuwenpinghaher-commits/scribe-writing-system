import { useEffect, useState } from 'react'
import { Activity, FileText, Bookmark, ShieldAlert, Target, CheckCircle2, EyeOff } from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'

function Metric({ icon: Icon, label, value, sub, tone = 'brand' }) {
  const c = { brand: 'text-brand', fore: 'text-fore', danger: 'text-danger', ok: 'text-ok' }[tone]
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className="flex items-center gap-1.5 text-faint text-[11px] uppercase tracking-wider mb-1.5"><Icon size={13} />{label}</div>
      <div className={`text-2xl font-semibold tnum ${c}`}>{value}</div>
      {sub && <div className="text-[11px] text-faint mt-0.5">{sub}</div>}
    </div>
  )
}

// 单条伏笔卡片。overdue 红边高亮;payoff 章显示;裸 int 章号经 chapterLabel 友好化。
function PromiseCard({ p }) {
  const overdue = p.overdue
  return (
    <div className={`rounded-lg border p-2.5 text-[12px] ${overdue ? 'border-danger/60 bg-danger/5' : 'border-line bg-canvas'}`}>
      <div className="flex items-start gap-1.5">
        <span className={`mt-[3px] w-1.5 h-1.5 rounded-full shrink-0 ${overdue ? 'bg-danger' : p.status === 'closed' ? 'bg-ok' : 'bg-faint'}`} />
        <span className="text-ink flex-1 leading-snug">{p.text || '(无描述)'}</span>
        {overdue && <span className="text-danger text-[10px] font-medium shrink-0">超期</span>}
      </div>
      <div className="text-faint text-[11px] mt-1 pl-3 flex flex-wrap gap-x-2">
        <span>埋:{chapterLabel(p.setup_chapter)}</span>
        {p.payoff_chapter != null && <span className="text-ok">收:{chapterLabel(p.payoff_chapter)}{p.span != null ? ` · 跨度${p.span}章` : ''}</span>}
        {p.payoff_chapter == null && p.chapters_open != null && <span>开口{p.chapters_open}章</span>}
      </div>
    </div>
  )
}

function LedgerColumn({ icon: Icon, label, tone, rows }) {
  const c = { fore: 'text-fore', ok: 'text-ok', faint: 'text-faint' }[tone]
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className={`flex items-center gap-1.5 text-[12px] font-semibold mb-3 ${c}`}>
        <Icon size={14} />{label} <span className="text-faint font-normal">({rows.length})</span>
      </div>
      <div className="space-y-2">
        {rows.length === 0 ? <div className="text-faint text-[12px]">—</div>
          : rows.map((p) => <PromiseCard key={p.id} p={p} />)}
      </div>
    </div>
  )
}

function PromiseLedger() {
  const [led, setLed] = useState(null)
  useEffect(() => { api.promisesLedger().then(setLed).catch(() => setLed(null)) }, [])
  if (!led) return null
  const a = led.audit || {}
  const pws = (a.payoff_without_setup || []).length + (a.closed_without_setup || []).length
  const balanced = a.balanced
  return (
    <div className="rounded-xl border border-line bg-surface p-4 mb-6">
      <div className="flex items-center flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-2"><Bookmark size={16} className="text-fore" /><h2 className="text-[15px] font-semibold text-ink">伏笔台账</h2></div>
        <span className="text-[11px] text-faint">阈值 {led.threshold} 章 · 现在第 {led.max_chapter} 章</span>
        <div className="ml-auto flex items-center gap-2 text-[11px]">
          <span className={balanced ? 'text-ok' : 'text-danger'}>{balanced ? '✓ 已平衡' : '⚠ 未平衡'}</span>
          <span className="text-faint">超期 {a.overdue_count ?? 0} · 闭无开 {pws} · 契诃夫 {a.never_paid ?? 0} 把枪没响</span>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <LedgerColumn icon={Target} label="已埋未收" tone="fore" rows={led.open || []} />
        <LedgerColumn icon={CheckCircle2} label="已回收" tone="ok" rows={led.closed || []} />
        <LedgerColumn icon={EyeOff} label="障眼法" tone="faint" rows={led.red_herring || []} />
      </div>
      {pws > 0 && (
        <div className="mt-3 text-[11px] text-danger">
          ⚠ 闭无开(回收早于埋设,疑似凭空 payoff):
          {[...(a.payoff_without_setup || []), ...(a.closed_without_setup || [])]
            .map((x) => `「${x.text}」(埋${x.setup_chapter ?? '?'}→收${x.payoff_chapter})`).join('、')}
        </div>
      )}
    </div>
  )
}

export function InsightView() {
  const [q, setQ] = useState(null)
  useEffect(() => { api.quality().then(setQ) }, [])
  if (!q) return <div className="p-8 text-faint">加载中…</div>

  const chs = q.chapters || []
  const weak = [...chs].filter((c) => c.qc_issues > 0 || c.causal > 0).sort((a, b) => (b.qc_issues + b.causal) - (a.qc_issues + a.causal))
  const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-ink)' }

  return (
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-5xl mx-auto px-8 py-8">
        <div className="flex items-center gap-2 mb-6"><Activity size={18} className="text-brand" /><h1 className="text-[22px] font-semibold prose-serif text-ink">质量仪表盘</h1></div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <Metric icon={FileText} label="规模" value={q.total_words?.toLocaleString() || 0} sub={`${chs.length} 章 · 目标 10 万字`} />
          <Metric icon={Bookmark} label="伏笔" value={q.foreshadow?.open ?? 0} sub={`未回收 · 已收 ${q.foreshadow?.closed ?? 0}`} tone="fore" />
          <Metric icon={ShieldAlert} label="伏笔超期" value={q.foreshadow?.overdue ?? 0} sub="埋下 >3 章未回收" tone={q.foreshadow?.overdue ? 'danger' : 'ok'} />
          <Metric icon={Activity} label="质检问题" value={chs.reduce((s, c) => s + c.qc_issues + c.causal, 0)} sub="确定性 QC + 因果" tone="danger" />
        </div>

        <PromiseLedger />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-6">
          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="text-[12px] font-semibold text-ink mb-3">各章字数</div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chs} margin={{ left: -18, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="seq" tick={{ fontSize: 11, fill: 'var(--color-faint)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-faint)' }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="word_count" name="字数" stroke="var(--color-brand)" fill="var(--color-brand)" fillOpacity={0.15} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="text-[12px] font-semibold text-ink mb-3">各章质检问题(QC + 因果)</div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chs} margin={{ left: -18, right: 8, top: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="seq" tick={{ fontSize: 11, fill: 'var(--color-faint)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-faint)' }} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="qc_issues" name="确定性QC" stackId="a" fill="var(--color-danger)" radius={[3, 3, 0, 0]} />
                <Bar dataKey="causal" name="因果违规" stackId="a" fill="var(--color-fore)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-surface p-4">
          <div className="text-[12px] font-semibold text-ink mb-2">弱章诊断(问题最多的章)</div>
          {weak.length === 0 ? <div className="text-[13px] text-ok">✓ 各章质检干净</div>
            : weak.slice(0, 8).map((c) => (
              <div key={c.seq} className="flex items-center gap-2 py-1.5 border-b border-line/50 last:border-0 text-[13px]">
                <span className="text-ink flex-1 truncate">{chapterLabel(c.seq, c.title)}</span>
                {c.qc_issues > 0 && <span className="text-danger text-[12px]">QC {c.qc_issues}</span>}
                {c.causal > 0 && <span className="text-fore text-[12px]">因果 {c.causal}</span>}
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
