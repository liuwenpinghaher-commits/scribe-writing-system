import { useEffect, useState } from 'react'
import { BookText, FileText, Bookmark, Users, Shield, Swords, Flame, ArrowRight, Activity, MapPin, AlertTriangle } from 'lucide-react'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'

// 书级概览:汇总规模 / 设定 / 伏笔 / 弱章,作为进入一本书后的「门厅」。
// 复用 /quality + /setting-completeness + /promises/ledger,不新增后端。
function Stat({ icon: Icon, label, value, sub, tone = 'ink', onClick }) {
  const c = { ink: 'text-ink', brand: 'text-brand', fore: 'text-fore', danger: 'text-danger', ok: 'text-ok' }[tone]
  const inner = (
    <>
      <div className="flex items-center gap-1.5 text-faint text-meta uppercase tracking-wider mb-1.5"><Icon size={13} />{label}</div>
      <div className={`text-2xl font-semibold tnum ${c}`}>{value}</div>
      {sub && <div className="text-meta text-faint mt-0.5">{sub}</div>}
    </>
  )
  // 可点的 Stat 用真正的 button(键盘可达);仅展示时保持 div。
  if (onClick) {
    return (
      <button onClick={onClick}
        className="w-full text-left rounded-xl border border-line bg-surface p-4 cursor-pointer hover:border-brand/30 transition-colors">
        {inner}
      </button>
    )
  }
  return <div className="rounded-xl border border-line bg-surface p-4">{inner}</div>
}

export function OverviewView({ onJumpChapter, onOpenView }) {
  const [q, setQ] = useState(null)
  const [comp, setComp] = useState(null)
  const [led, setLed] = useState(null)

  useEffect(() => {
    api.quality().then(setQ).catch(() => setQ(null))
    api.get('/setting-completeness').then(setComp).catch(() => setComp(null))
    api.promisesLedger().then(setLed).catch(() => setLed(null))
  }, [])

  if (!q) return <div className="p-8 text-faint">加载概览…</div>

  const chs = q.chapters || []
  const totalWords = q.total_words || 0
  const chCount = chs.length
  const qcTotal = chs.reduce((s, c) => s + (c.qc_issues || 0) + (c.causal || 0), 0)
  const weak = [...chs].filter((c) => (c.qc_issues || 0) + (c.causal || 0) > 0)
    .sort((a, b) => (b.qc_issues + b.causal) - (a.qc_issues + a.causal)).slice(0, 6)
  const fs = q.foreshadow || {}
  const audit = led?.audit || {}

  return (
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-5xl mx-auto px-8 py-8">
        <div className="flex items-center gap-2 mb-6">
          <BookText size={18} className="text-brand" />
          <h1 className="text-f22 font-semibold prose-serif text-ink">概览</h1>
        </div>

        {/* 规模 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <Stat icon={FileText} label="规模" value={totalWords.toLocaleString()} sub={`${chCount} 章`} tone="brand" />
          <Stat icon={Bookmark} label="伏笔" value={fs.open ?? 0} sub={`未回收 · 已收 ${fs.closed ?? 0}`} tone="fore"
            onClick={() => onOpenView?.('insight')} />
          <Stat icon={Activity} label="质检问题" value={qcTotal} sub="QC + 因果" tone={qcTotal ? 'danger' : 'ok'}
            onClick={() => onOpenView?.('insight')} />
          <Stat icon={Bookmark} label="伏笔超期" value={fs.overdue ?? 0} sub="埋下 >3 章未回收" tone={fs.overdue ? 'danger' : 'ok'} />
        </div>

        {/* 设定统计 */}
        {comp && (
          <div className="rounded-xl border border-line bg-surface p-4 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="text-f12 font-semibold text-ink">设定库</div>
              {comp.completeness_score != null && (
                <span className="text-meta text-faint">完整度 {comp.completeness_score}/100</span>
              )}
            </div>
            <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                ['角色', comp.total_chars, Users],
                ['世界规则', comp.total_rules, Shield],
                ['势力', comp.total_factions, Swords],
                ['地点', comp.total_places, MapPin],
                ['事实/命题', comp.total_facts, BookText],
              ].map(([label, count, Icon]) => (
                <div key={label} className="rounded-lg border border-line bg-canvas p-2.5">
                  <div className="flex items-center gap-1.5 text-meta text-faint mb-1"><Icon size={12} />{label}</div>
                  <div className="text-f18 font-semibold text-ink tnum">{count ?? 0}</div>
                </div>
              ))}
            </div>
            {comp.missing_dimensions?.length > 0 && (
              <div className="mt-3 text-f12 text-danger">缺失维度:{comp.missing_dimensions.join('、')}</div>
            )}
          </div>
        )}

        {/* 伏笔平衡速览 */}
        {led && (
          <div className="rounded-xl border border-line bg-surface p-4 mb-6">
            <div className="flex items-center flex-wrap gap-2 mb-2">
              <Bookmark size={15} className="text-fore" />
              <div className="text-f13 font-semibold text-ink">伏笔平衡</div>
              <span className={`text-meta inline-flex items-center gap-1 ${audit.balanced ? 'text-ok' : 'text-danger'}`}>
                {audit.balanced ? '✓ 已平衡' : <><AlertTriangle size={11} />未平衡</>}
              </span>
              <button onClick={() => onOpenView?.('insight')}
                className="ml-auto inline-flex items-center gap-1 text-f12 text-brand hover:underline cursor-pointer">
                打开伏笔台账 <ArrowRight size={12} />
              </button>
            </div>
            <div className="text-f12 text-faint">
              已埋未收 {(led.open || []).length} · 已回收 {(led.closed || []).length} · 障眼法 {(led.red_herring || []).length}
              · 超期 {audit.overdue_count ?? 0} · 契诃夫 {audit.never_paid ?? 0} 把枪没响
            </div>
          </div>
        )}

        {/* 弱章诊断 */}
        <div className="rounded-xl border border-line bg-surface p-4">
          <div className="text-f12 font-semibold text-ink mb-2">最需关注的章</div>
          {weak.length === 0 ? (
            <div className="text-f13 text-ok">✓ 各章质检干净</div>
          ) : weak.map((c) => (
            <button key={c.seq} onClick={() => onJumpChapter?.(c.seq)}
              className="w-full flex items-center gap-2 py-1.5 border-b border-line/50 last:border-0 text-f13 text-left hover:bg-soft/40 rounded px-1 -mx-1 transition-colors cursor-pointer">
              <span className="text-ink flex-1 truncate">{chapterLabel(c.seq, c.title)}</span>
              {c.qc_issues > 0 && <span className="text-danger text-f12">QC {c.qc_issues}</span>}
              {c.causal > 0 && <span className="text-fore text-f12">因果 {c.causal}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
