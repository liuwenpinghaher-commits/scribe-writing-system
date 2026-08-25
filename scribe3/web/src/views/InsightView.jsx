import { useEffect, useRef, useState } from 'react'
import { Activity, FileText, Bookmark, ShieldAlert, AlertTriangle } from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'
import { showToast } from '../ui/Toast'
import { scrollBehavior } from '../lib/utils'
import { safeWordGoal } from '../lib/wordGoal.js'
import { liveTouchesTable } from '../lib/liveRefresh.js'
import { Metric, ErrorState } from './insight/InsightBits.jsx'
import { WeakChapterList } from './insight/WeakChapterList.jsx'
import { OpenPromiseStrip, PromiseLedger, usePromiseLedger } from './insight/PromiseLedger.jsx'
import { ProgressPanel, GoalDialog } from './insight/ProgressPanel.jsx'
import { DiscourseBreathPanel } from './insight/DiscourseBreathPanel.jsx'

export function InsightView({ work, onJumpChapter, focus, onNavigateToObject, chapter = null }) {
  const [q, setQ] = useState(null)
  const [qErr, setQErr] = useState(null)
  const [intent, setIntent] = useState(null)
  const [goalOpen, setGoalOpen] = useState(false)
  const [progressKey, setProgressKey] = useState(0)
  const [qualityKey, setQualityKey] = useState(0)
  const [qualityRefreshing, setQualityRefreshing] = useState(false)
  const progressRef = useRef(null)
  const { led, ledErr, refresh: refreshLedger } = usePromiseLedger()

  useEffect(() => {
    let alive = true
    setQ(null)
    setQErr(null)
    api.quality()
      .then((r) => { if (alive) { setQ(r); setQErr(null) } })
      .catch((e) => { if (alive) setQErr(e?.body?.detail || e?.message || '质量仪表盘加载失败') })
    return () => { alive = false }
  }, [qualityKey])
  useEffect(() => { api.intent().then(setIntent).catch(() => setIntent({})) }, [])
  useEffect(() => {
    const onLive = (e) => {
      if (liveTouchesTable(e?.detail, ['chapter', 'promise', 'daily_progress', 'quality_snapshot'])) {
        setQualityKey((k) => k + 1)
      }
    }
    window.addEventListener('s3-live', onLive)
    return () => window.removeEventListener('s3-live', onLive)
  }, [])

  useEffect(() => {
    if (focus === 'progress' && (q || qErr)) {
      const t = setTimeout(() => progressRef.current?.scrollIntoView({ behavior: scrollBehavior(), block: 'start' }), 80)
      return () => clearTimeout(t)
    }
  }, [focus, q, qErr])

  if (!q && !qErr) return <div className="p-8 text-faint">加载中…</div>

  const chs = q?.chapters || []
  const cacheStale = (q?.cache_stale_chapters || []).length > 0
  const lastSeq = chs.length ? Number(chs[chs.length - 1].seq) || 1 : 1
  const refreshQuality = async () => {
    setQualityRefreshing(true)
    try {
      const r = await api.refreshQuality()
      showToast(r.refreshed_chapters?.length ? `已刷新 ${r.refreshed_chapters.length} 章质量缓存` : '质量缓存已是最新', { tone: 'ok' })
      setQualityKey((k) => k + 1)
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '质量缓存刷新失败', { tone: 'danger' })
    } finally {
      setQualityRefreshing(false)
    }
  }
  const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-ink)' }
  const totalGoal = safeWordGoal(intent?.total_word_goal)
  const weakPreview = [...chs].filter((c) => (c.qc_issues || 0) + (c.causal || 0) > 0)

  return (
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-5xl mx-auto px-6 py-6 md:px-8 md:py-8">
        <div className="flex items-center gap-2 mb-5">
          <Activity size={18} className="text-brand" />
          <h1 className="type-page prose-serif text-ink">仪表盘</h1>
          <span className="text-meta text-faint">质量 · 伏笔 · 码字</span>
        </div>

        {cacheStale && (
          <section role="alert" className="mb-6 rounded-lg border border-fore/25 bg-fore/5 px-4 py-3 text-f13 text-ink flex items-center gap-3">
            <AlertTriangle size={16} className="text-fore shrink-0" />
            <div className="flex-1">第 {q.cache_stale_chapters.join('、')} 章的质量缓存已过期；当前问题数不可作为验收结论。</div>
            <button type="button" onClick={refreshQuality} disabled={qualityRefreshing}
              className="shrink-0 rounded-md border border-fore/30 px-2.5 py-1 text-f12 text-fore hover:bg-fore/10 disabled:opacity-50 cursor-pointer">
              {qualityRefreshing ? '刷新中…' : '刷新质量缓存'}
            </button>
          </section>
        )}

        <section role="region" aria-label="洞察数据摘要" className="mb-6 pb-4 border-b border-line/60">
          <div className="text-f12 font-semibold text-ink mb-2">数据摘要</div>
          <div className="text-f13 text-faint leading-relaxed">
            {qErr
              ? '质量汇总暂时读不到；下面的码字和伏笔台账仍可用。质检数字不是总纲里的「写到/立到」。'
              : `全书 ${chs.length} 章,共 ${q.total_words?.toLocaleString() || 0} 字(码字目标 ${totalGoal.toLocaleString()} 字，不是总纲进度)。伏笔未回收 ${q.foreshadow?.open ?? 0} 条、已回收 ${q.foreshadow?.closed ?? 0} 条、超期 ${q.foreshadow?.overdue ?? 0} 条。${cacheStale ? '质量缓存待刷新，暂不展示问题合计与弱章结论。' : `质检问题合计 ${chs.reduce((s, c) => s + (c.qc_issues || 0) + (c.causal || 0), 0)} 项;其中 ${weakPreview.length} 章问题较多需优先关注${weakPreview.length > 0 ? `:${weakPreview.slice(0, 3).map((c) => chapterLabel(c.seq, c.title)).join('、')}${weakPreview.length > 3 ? ' 等' : ''}` : ''}。`}`}
          </div>
        </section>

        <WeakChapterList
          chapters={chs}
          qErr={qErr}
          cacheStale={cacheStale}
          currentChapter={chapter}
          onNavigateToObject={onNavigateToObject}
        />
        <OpenPromiseStrip led={led} ledErr={ledErr} onJumpChapter={onJumpChapter} />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <Metric icon={FileText} label="规模" value={qErr ? '—' : (q.total_words?.toLocaleString() || 0)}
            sub={qErr ? '质量汇总失败' : `${chs.length} 章 · 码字目标 ${totalGoal.toLocaleString()} 字`} />
          <Metric icon={Bookmark} label="伏笔" value={qErr ? '—' : (q.foreshadow?.open ?? 0)} sub={qErr ? '见下方台账' : `未回收 · 已收 ${q.foreshadow?.closed ?? 0}`} tone="fore" />
          <Metric icon={ShieldAlert} label="伏笔超期" value={qErr ? '—' : (q.foreshadow?.overdue ?? 0)} sub="埋下 >3 章未回收" tone={!qErr && q.foreshadow?.overdue ? 'danger' : 'ok'} />
          <Metric icon={Activity} label="质检问题" value={qErr ? '—' : (cacheStale ? '待刷新' : chs.reduce((s, c) => s + (c.qc_issues || 0) + (c.causal || 0), 0))} sub={qErr ? '未计入验收' : (cacheStale ? '缓存已过期' : '确定性 QC + 因果')} tone={cacheStale ? 'fore' : 'danger'} />
        </div>

        <PromiseLedger led={led} ledErr={ledErr} onJumpChapter={onJumpChapter} onRetry={refreshLedger} />

        <GoalDialog
          open={goalOpen}
          intent={intent}
          onClose={() => setGoalOpen(false)}
          onSaved={() => {
            api.intent().then(setIntent)
            setProgressKey((k) => k + 1)
          }}
        />

        <div ref={progressRef} className={focus === 'progress' ? 'scroll-mt-4 rounded-md ring-2 ring-brand/40 transition-shadow' : ''}>
          <ProgressPanel key={progressKey} onGoalEdit={() => setGoalOpen(true)} />
        </div>

        {qErr && (
          <div className="mb-5">
            <ErrorState message="质量汇总加载失败" onRetry={() => setQualityKey((k) => k + 1)} />
          </div>
        )}

        {!qErr && (
          <div className="mb-5 grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="insight-charts">
            <div>
              <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-3">各章字数</div>
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
            <div>
              <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-3">各章质检问题(QC + 因果)</div>
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
        )}

        <DiscourseBreathPanel work={work} onJumpChapter={onJumpChapter} chapter={chapter} lastSeq={lastSeq} />
      </div>
    </div>
  )
}
