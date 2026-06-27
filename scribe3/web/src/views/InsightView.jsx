import { useEffect, useState } from 'react'
import { Activity, FileText, Bookmark, ShieldAlert } from 'lucide-react'
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
