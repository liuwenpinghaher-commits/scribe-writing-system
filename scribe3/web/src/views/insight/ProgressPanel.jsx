import { Fragment, useEffect, useRef, useState } from 'react'
import { Pencil, Flame, Trophy, TrendingUp } from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import { api } from '../../api'
import { safeWordGoal, wordGoalPct } from '../../lib/wordGoal.js'
import { liveTouchesTable } from '../../lib/liveRefresh.js'
import { ErrorState } from './InsightBits.jsx'

function GoalDialog({ open, intent, onClose, onSaved }) {
  const [totalGoal, setTotalGoal] = useState('')
  const [dailyGoal, setDailyGoal] = useState('')
  const [saving, setSaving] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setTotalGoal(intent?.total_word_goal ?? '')
      setDailyGoal(intent?.daily_word_goal ?? '')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open, intent])

  if (!open) return null

  const save = async () => {
    setSaving(true)
    try {
      const body = {}
      if (totalGoal !== '' && totalGoal !== null) body.total_word_goal = Number(totalGoal)
      if (dailyGoal !== '' && dailyGoal !== null) body.daily_word_goal = Number(dailyGoal)
      await api.putIntentGoals(body)
      onSaved()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-surface rounded-lg p-6 w-80 shadow-[var(--shadow-pop)] ring-1 ring-line/50" onClick={(e) => e.stopPropagation()}>
        <div className="type-section text-ink mb-4">编辑写作目标</div>
        <div className="space-y-3">
          <div>
            <label className="text-meta text-faint uppercase tracking-wider block mb-1">整稿目标(字)</label>
            <input ref={inputRef} type="number" min={0} value={totalGoal} onChange={(e) => setTotalGoal(e.target.value)}
              placeholder="例: 100000"
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-f14 text-ink outline-none focus:border-brand" />
          </div>
          <div>
            <label className="text-meta text-faint uppercase tracking-wider block mb-1">每日目标(字,可空)</label>
            <input type="number" min={0} value={dailyGoal} onChange={(e) => setDailyGoal(e.target.value)}
              placeholder="例: 2000(可不填)"
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-f14 text-ink outline-none focus:border-brand" />
          </div>
        </div>
        <div className="flex gap-2 mt-5 justify-end">
          <button onClick={onClose} className="px-4 py-1.5 rounded-lg text-f13 text-faint hover:bg-soft transition-colors">取消</button>
          <button onClick={save} disabled={saving}
            className="px-4 py-1.5 rounded-lg text-f13 bg-brand text-brandfg hover:opacity-90 transition-opacity disabled:opacity-50">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

function WordHeatmap({ heatmap, dailyGoal }) {
  const wordMap = {}
  for (const { date, words } of heatmap) {
    wordMap[date] = words ?? 0
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const WEEKS = 13
  const DAYS = WEEKS * 7
  const startDay = new Date(today)
  startDay.setDate(today.getDate() - (DAYS - 1))
  const cols = Array.from({ length: WEEKS }, (_, wi) =>
    Array.from({ length: 7 }, (_, di) => {
      const d = new Date(startDay)
      d.setDate(startDay.getDate() + wi * 7 + di)
      const dateStr = d.toISOString().slice(0, 10)
      const words = wordMap[dateStr] ?? null
      const isFuture = d > today
      return { dateStr, words, isFuture, dow: di }
    })
  )
  const cellColor = (words, isFuture) => {
    if (isFuture || words === null) return 'var(--color-soft)'
    if (words <= 0) return 'var(--color-soft)'
    if (dailyGoal) {
      if (words >= dailyGoal * 1.2) return 'color-mix(in srgb, var(--color-ok) 92%, transparent)'
      if (words >= dailyGoal) return 'color-mix(in srgb, var(--color-ok) 72%, transparent)'
      if (words >= dailyGoal * 0.5) return 'color-mix(in srgb, var(--color-ok) 42%, transparent)'
      return 'color-mix(in srgb, var(--color-ok) 22%, transparent)'
    }
    if (words >= 2000) return 'color-mix(in srgb, var(--color-ok) 92%, transparent)'
    if (words >= 1000) return 'color-mix(in srgb, var(--color-ok) 72%, transparent)'
    if (words >= 300) return 'color-mix(in srgb, var(--color-ok) 42%, transparent)'
    return 'color-mix(in srgb, var(--color-ok) 22%, transparent)'
  }
  const activeDays = heatmap.filter((h) => (h.words ?? 0) > 0).length
  const bestDay = heatmap.reduce((b, h) => ((h.words ?? 0) > (b?.words ?? 0) ? h : b), null)
  const DOW_LABELS = ['日', '', '二', '', '四', '', '六']
  const monthLabels = cols.map((col) => {
    const d = new Date(col[0].dateStr)
    const firstDate = d.getDate()
    if (firstDate <= 7) return d.toLocaleDateString('zh-CN', { month: 'short' })
    return ''
  })

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-meta text-faint">
          码字热力图 · 近 {WEEKS} 周
          <span className="ml-2">近 {WEEKS} 周有 {activeDays} 天码字{bestDay ? `,最高单日 ${(bestDay.words ?? 0).toLocaleString()} 字` : ''}</span>
        </div>
        <div className="flex items-center gap-1.5 text-meta text-faint">
          <span>少</span>
          {['var(--color-soft)',
            'color-mix(in srgb, var(--color-ok) 22%, transparent)',
            'color-mix(in srgb, var(--color-ok) 42%, transparent)',
            'color-mix(in srgb, var(--color-ok) 72%, transparent)',
            'color-mix(in srgb, var(--color-ok) 92%, transparent)',
          ].map((c, i) => (
            <div key={i} className="w-3 h-3 rounded-sm" style={{ background: c }} />
          ))}
          <span>多</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: `16px repeat(${WEEKS}, 12px)`, gap: '2px', alignItems: 'start' }}>
          <div />
          {monthLabels.map((label, wi) => (
            <div key={wi} style={{ fontSize: 9, color: 'var(--color-faint)', lineHeight: '12px', textAlign: 'center' }}>
              {label}
            </div>
          ))}
          {[0, 1, 2, 3, 4, 5, 6].map((dow) => (
            <Fragment key={dow}>
              <div style={{ fontSize: 9, color: 'var(--color-faint)', lineHeight: '12px', textAlign: 'right', paddingRight: 2 }}>
                {DOW_LABELS[dow]}
              </div>
              {cols.map((col, wi) => {
                const cell = col[dow]
                const bg = cellColor(cell.words, cell.isFuture)
                const tip = cell.isFuture ? '' : `${cell.dateStr}: ${(cell.words ?? 0).toLocaleString()} 字`
                return (
                  <div key={`${wi}-${dow}`} title={tip} style={{ width: 12, height: 12, borderRadius: 2, background: bg }} />
                )
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  )
}

export function ProgressPanel({ onGoalEdit }) {
  const [prog, setProg] = useState(null)
  const [err, setErr] = useState(null)
  const [win, setWin] = useState('all')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    let alive = true
    setProg(null)
    setErr(null)
    api.progress(win)
      .then((r) => { if (alive) { setProg(r); setErr(null) } })
      .catch((e) => { if (alive) { setProg(null); setErr(e?.body?.detail || e?.message || '进度数据加载失败') } })
    return () => { alive = false }
  }, [win, retryKey])

  useEffect(() => {
    const onLive = (e) => {
      if (liveTouchesTable(e?.detail, ['chapter', 'daily_progress', 'intent'])) {
        setRetryKey((k) => k + 1)
      }
    }
    window.addEventListener('s3-live', onLive)
    return () => window.removeEventListener('s3-live', onLive)
  }, [])

  const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-ink)' }

  if (err) return (
    <div className="mb-6 pb-5 border-b border-line/60">
      <ErrorState message="进度数据加载失败" onRetry={() => setRetryKey((k) => k + 1)} />
    </div>
  )

  if (!prog) return (
    <div className="mb-6 pb-5 border-b border-line/60">
      <div className="text-f12 text-faint">进度数据加载中…</div>
    </div>
  )

  const totalGoal = safeWordGoal(prog.total_word_goal)
  const dailyGoal = prog.daily_word_goal ?? null
  const totalWords = prog.total_words ?? 0
  const todayWords = prog.today_words ?? 0
  const totalPct = wordGoalPct(totalWords, totalGoal)
  const dailyPct = dailyGoal ? Math.min(120, Math.round((todayWords / dailyGoal) * 100)) : null
  const dailyMet = dailyGoal ? todayWords >= dailyGoal : null
  const totalBarColor = totalPct >= 100 ? 'var(--color-fore)' : totalPct >= 50 ? 'var(--color-ok)' : 'var(--color-brand)'
  const dailyBarColor = dailyMet ? 'var(--color-ok)' : 'var(--color-brand)'
  const daily = prog.daily || []
  const weekdayHist = prog.weekday_histogram || []
  const bestWeekday = prog.best_weekday || null
  const WIN_OPTS = [{ v: '30', label: '近30天' }, { v: '90', label: '近90天' }, { v: 'all', label: '全程' }]

  return (
    <div className="mb-6 pb-5 border-b border-line/60" data-testid="insight-progress">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp size={15} className="text-brand" />
          <span className="text-meta font-semibold uppercase tracking-wider text-faint">码字进度（工程配额）</span>
          <div className="flex gap-0.5 ml-2 bg-soft rounded-lg p-0.5">
            {WIN_OPTS.map(({ v, label }) => (
              <button key={v} onClick={() => setWin(v)}
                className={`px-2 py-0.5 rounded text-meta transition-colors ${win === v ? 'bg-surface text-ink font-medium' : 'text-faint hover:text-ink'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <button onClick={onGoalEdit}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-meta text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer">
          <Pencil size={11} />编辑目标
        </button>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="rounded-lg bg-soft/40 p-3 text-center">
          <div className="text-meta text-faint mb-0.5">今日码字</div>
          <div className={`type-section tnum ${dailyMet ? 'text-ok' : 'text-ink'}`}>+{todayWords.toLocaleString()}</div>
          {dailyGoal && (
            <div className={`text-meta mt-0.5 ${dailyMet ? 'text-ok' : 'text-faint'}`}>
              {dailyMet ? '✓ 今日达标' : `目标 ${dailyGoal.toLocaleString()}`}
            </div>
          )}
        </div>
        <div className="rounded-lg bg-soft/40 p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-meta text-faint mb-0.5"><Flame size={11} />当前连胜</div>
          <div className="type-section tnum text-fore">{prog.current_streak}</div>
          <div className="text-meta text-faint mt-0.5">天</div>
        </div>
        <div className="rounded-lg bg-soft/40 p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-meta text-faint mb-0.5"><Trophy size={11} />最长连胜</div>
          <div className="type-section tnum text-fore">{prog.longest_streak}</div>
          <div className="text-meta text-faint mt-0.5">天</div>
        </div>
      </div>
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5 text-f12">
          <span className="text-faint">码字配额</span>
          <span className="tnum text-ink font-medium">{totalWords.toLocaleString()} / {totalGoal.toLocaleString()} 字 · {totalPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-soft overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: Math.min(100, totalPct) + '%', background: totalBarColor }} />
        </div>
        {totalPct >= 100 && <div className="text-meta text-fore mt-1">整稿目标达成！</div>}
      </div>
      {dailyGoal && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5 text-f12">
            <span className="text-faint">今日进度</span>
            <span className={`tnum font-medium ${dailyMet ? 'text-ok' : 'text-ink'}`}>
              {todayWords.toLocaleString()} / {dailyGoal.toLocaleString()} 字 · {dailyPct}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-soft overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{ width: Math.min(100, dailyPct) + '%', background: dailyBarColor }} />
          </div>
        </div>
      )}
      {daily.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-2">
          <div>
            <div className="text-meta text-faint mb-2">每日字数</div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={daily} margin={{ left: -20, right: 4, top: 2 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--color-faint)' }} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: 'var(--color-faint)' }} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v.toLocaleString() + ' 字', '当日']} />
                {dailyGoal && <ReferenceLine y={dailyGoal} stroke="var(--color-ok)" strokeDasharray="3 3" strokeWidth={1} />}
                <Bar dataKey="words" name="字数" radius={[3, 3, 0, 0]} fill="var(--color-brand)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-meta text-faint">累计推进</span>
              <span className="flex items-center gap-1 text-meta text-faint">
                <span style={{ display: 'inline-block', width: 16, height: 2, background: 'var(--color-brand)', verticalAlign: 'middle' }} />实际
              </span>
              {daily.some((d) => d.ideal_cumulative != null) && (
                <span className="flex items-center gap-1 text-meta text-faint">
                  <span style={{ display: 'inline-block', width: 16, height: 2, background: 'var(--color-fore)', borderTop: '2px dashed var(--color-fore)', verticalAlign: 'middle' }} />理想
                </span>
              )}
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={daily} margin={{ left: -20, right: 4, top: 2 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--color-faint)' }} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: 'var(--color-faint)' }} />
                <Tooltip contentStyle={tooltipStyle}
                  formatter={(v, name) => [v != null ? v.toLocaleString() + ' 字' : '-', name === 'ideal_cumulative' ? '理想' : '累计']} />
                {totalGoal && <ReferenceLine y={totalGoal} stroke="var(--color-fore)" strokeDasharray="4 4" strokeWidth={1} />}
                <Area type="monotone" dataKey="cumulative" name="累计" stroke="var(--color-brand)"
                  fill="var(--color-brand)" fillOpacity={0.15} strokeWidth={2} />
                {daily.some((d) => d.ideal_cumulative != null) && (
                  <Area type="monotone" dataKey="ideal_cumulative" name="理想"
                    stroke="var(--color-fore)" strokeWidth={1.5} strokeDasharray="5 4"
                    fill="none" dot={false} activeDot={false} />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {weekdayHist.length > 0 && weekdayHist.some((d) => d.avg_words > 0) && (
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-meta text-faint">最高产星期几</span>
            {bestWeekday && <span className="text-meta text-brand font-medium">{bestWeekday}最高产</span>}
          </div>
          <ResponsiveContainer width="100%" height={90}>
            <BarChart data={weekdayHist} margin={{ left: -20, right: 4, top: 2, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 9, fill: 'var(--color-faint)' }} />
              <YAxis tick={{ fontSize: 9, fill: 'var(--color-faint)' }} allowDecimals={false} />
              <Tooltip contentStyle={tooltipStyle}
                formatter={(v, _name, props) => [v.toLocaleString() + ' 字', `平均 (${props.payload.count}天)`]} />
              <Bar dataKey="avg_words" name="平均字数" radius={[3, 3, 0, 0]} fill="var(--color-brand)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <WordHeatmap heatmap={prog.heatmap || []} dailyGoal={dailyGoal} />
    </div>
  )
}

export { GoalDialog }
