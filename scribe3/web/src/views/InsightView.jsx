import { Fragment, useEffect, useRef, useState } from 'react'
import { Activity, FileText, Bookmark, ShieldAlert, Target, CheckCircle2, EyeOff, Pencil, Flame, Trophy, TrendingUp, ArrowRight } from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'

// ── 通用 Metric 卡 ──────────────────────────────────────────────────────────
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

// ── 伏笔相关 ────────────────────────────────────────────────────────────────

// setup→payoff 连线(已回收专用)
function PromiseSpanBar({ setupChapter, payoffChapter, maxChapter }) {
  if (setupChapter == null || payoffChapter == null || maxChapter == null || maxChapter <= 0) return null
  const total = Math.max(maxChapter, payoffChapter)
  const setupPct = Math.max(0, Math.min(100, (setupChapter / total) * 100))
  const payoffPct = Math.max(0, Math.min(100, (payoffChapter / total) * 100))
  const widthPct = Math.max(1, payoffPct - setupPct)
  return (
    <div className="relative h-2 mt-1.5 mb-0.5 rounded-full bg-soft overflow-hidden">
      <div
        className="absolute top-0 h-full rounded-full bg-ok/60"
        style={{ left: `${setupPct}%`, width: `${widthPct}%` }}
      />
      <div className="absolute top-0 h-full w-[3px] rounded-full bg-faint" style={{ left: `${setupPct}%` }} />
      <div className="absolute top-0 h-full w-[3px] rounded-full bg-ok" style={{ left: `calc(${payoffPct}% - 3px)` }} />
    </div>
  )
}

function PromiseCard({ p, maxChapter, onJumpChapter, onRefresh }) {
  const overdue = p.overdue
  const [advancing, setAdvancing] = useState(false)
  const [payoffInput, setPayoffInput] = useState('')
  const [showAdvance, setShowAdvance] = useState(false)
  const [busy, setBusy] = useState(false)

  const doAdvance = async () => {
    const ch = parseInt(payoffInput, 10)
    if (!ch || ch < 1) return
    setBusy(true)
    try {
      await api.advancePromise(p.id, ch)
      setShowAdvance(false)
      setPayoffInput('')
      onRefresh?.()
    } catch (e) {
      alert(e?.body?.detail || e?.message || '回收失败')
    } finally {
      setBusy(false)
    }
  }

  const doMarkHerring = async () => {
    setBusy(true)
    try {
      await api.markHerring(p.id)
      onRefresh?.()
    } catch (e) {
      alert(e?.body?.detail || e?.message || '标记失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={`rounded-lg border p-2.5 text-[12px] ${overdue ? 'border-danger/60 bg-danger/5' : 'border-line bg-canvas'}`}>
      <div className="flex items-start gap-1.5">
        <span className={`mt-[3px] w-1.5 h-1.5 rounded-full shrink-0 ${overdue ? 'bg-danger' : p.status === 'closed' ? 'bg-ok' : 'bg-faint'}`} />
        <span className="text-ink flex-1 leading-snug">{p.text || '(无描述)'}</span>
        {overdue && <span className="text-danger text-[10px] font-medium shrink-0">超期</span>}
      </div>
      {/* setup→payoff 连线(已回收) */}
      {p.status === 'closed' && p.payoff_chapter != null && (
        <PromiseSpanBar setupChapter={p.setup_chapter} payoffChapter={p.payoff_chapter} maxChapter={maxChapter} />
      )}
      <div className="text-faint text-[11px] mt-1 pl-3 flex flex-wrap gap-x-2">
        {/* 点章号跳写作台 */}
        {p.setup_chapter != null && (
          <button
            className="hover:text-brand cursor-pointer underline-offset-2 hover:underline transition-colors"
            onClick={() => onJumpChapter?.(p.setup_chapter)}
          >
            埋:第{p.setup_chapter}章
          </button>
        )}
        {p.payoff_chapter != null && (
          <>
            <ArrowRight size={10} className="self-center text-faint" />
            <button
              className="text-ok hover:text-ok/70 cursor-pointer underline-offset-2 hover:underline transition-colors"
              onClick={() => onJumpChapter?.(p.payoff_chapter)}
            >
              收:第{p.payoff_chapter}章{p.span != null ? ` · 跨${p.span}章` : ''}
            </button>
          </>
        )}
        {p.payoff_chapter == null && p.chapters_open != null && <span>开口{p.chapters_open}章</span>}
      </div>
      {/* 操作按钮(open/red_herring 显示) */}
      {p.status !== 'closed' && p.kind !== 'red_herring' && (
        <div className="pl-3 mt-1.5 flex flex-wrap items-center gap-1.5">
          {!showAdvance ? (
            <button
              onClick={() => setShowAdvance(true)}
              className="text-[10px] px-2 py-0.5 rounded border border-ok/40 text-ok hover:bg-ok/10 transition-colors"
            >
              标记回收
            </button>
          ) : (
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-faint">收于第</span>
              <input
                type="number" min={1} value={payoffInput}
                onChange={(e) => setPayoffInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doAdvance()}
                className="w-12 h-5 rounded border border-line bg-surface px-1 text-[11px] text-ink outline-none focus:border-ok"
                placeholder="章"
                autoFocus
              />
              <span className="text-[10px] text-faint">章</span>
              <button onClick={doAdvance} disabled={busy}
                className="text-[10px] px-2 py-0.5 rounded bg-ok text-white hover:opacity-80 disabled:opacity-50 transition-opacity">
                {busy ? '…' : '确认'}
              </button>
              <button onClick={() => { setShowAdvance(false); setPayoffInput('') }}
                className="text-[10px] px-2 py-0.5 rounded border border-line text-faint hover:bg-soft transition-colors">
                取消
              </button>
            </div>
          )}
          <button
            onClick={doMarkHerring} disabled={busy}
            className="text-[10px] px-2 py-0.5 rounded border border-line text-faint hover:bg-soft hover:text-ink transition-colors disabled:opacity-50"
          >
            标为障眼法
          </button>
        </div>
      )}
    </div>
  )
}

function LedgerColumn({ icon: Icon, label, tone, rows, maxChapter, onJumpChapter, onRefresh }) {
  const c = { fore: 'text-fore', ok: 'text-ok', faint: 'text-faint' }[tone]
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <div className={`flex items-center gap-1.5 text-[12px] font-semibold mb-3 ${c}`}>
        <Icon size={14} />{label} <span className="text-faint font-normal">({rows.length})</span>
      </div>
      <div className="space-y-2">
        {rows.length === 0 ? <div className="text-faint text-[12px]">—</div>
          : rows.map((p) => (
            <PromiseCard
              key={p.id} p={p}
              maxChapter={maxChapter}
              onJumpChapter={onJumpChapter}
              onRefresh={onRefresh}
            />
          ))}
      </div>
    </div>
  )
}

function PromiseLedger({ onJumpChapter }) {
  const [led, setLed] = useState(null)
  const [ledKey, setLedKey] = useState(0)
  const refresh = () => setLedKey((k) => k + 1)
  useEffect(() => { api.promisesLedger().then(setLed).catch(() => setLed(null)) }, [ledKey])
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
        <LedgerColumn icon={Target} label="已埋未收" tone="fore" rows={led.open || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} onRefresh={refresh} />
        <LedgerColumn icon={CheckCircle2} label="已回收" tone="ok" rows={led.closed || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} onRefresh={refresh} />
        <LedgerColumn icon={EyeOff} label="障眼法" tone="faint" rows={led.red_herring || []}
          maxChapter={led.max_chapter} onJumpChapter={onJumpChapter} onRefresh={refresh} />
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

// ── 编辑目标 Modal ───────────────────────────────────────────────────────────
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
      const body = { ...(intent || {}) }
      if (totalGoal !== '' && totalGoal !== null) body.total_word_goal = Number(totalGoal)
      if (dailyGoal !== '' && dailyGoal !== null) body.daily_word_goal = Number(dailyGoal)
      await api.putIntent(body)
      onSaved()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-surface border border-line rounded-2xl p-6 w-80 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="text-[15px] font-semibold text-ink mb-4">编辑写作目标</div>
        <div className="space-y-3">
          <div>
            <label className="text-[11px] text-faint uppercase tracking-wider block mb-1">整稿目标(字)</label>
            <input ref={inputRef} type="number" min={0} value={totalGoal} onChange={(e) => setTotalGoal(e.target.value)}
              placeholder="例: 100000"
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-[14px] text-ink outline-none focus:border-brand" />
          </div>
          <div>
            <label className="text-[11px] text-faint uppercase tracking-wider block mb-1">每日目标(字,可空)</label>
            <input type="number" min={0} value={dailyGoal} onChange={(e) => setDailyGoal(e.target.value)}
              placeholder="例: 2000(可不填)"
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-[14px] text-ink outline-none focus:border-brand" />
          </div>
        </div>
        <div className="flex gap-2 mt-5 justify-end">
          <button onClick={onClose} className="px-4 py-1.5 rounded-lg text-[13px] text-faint hover:bg-soft transition-colors">取消</button>
          <button onClick={save} disabled={saving}
            className="px-4 py-1.5 rounded-lg text-[13px] bg-brand text-white hover:opacity-90 transition-opacity disabled:opacity-50">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── 码字进度面板 ─────────────────────────────────────────────────────────────
function ProgressPanel({ onGoalEdit }) {
  const [prog, setProg] = useState(null)
  useEffect(() => { api.progress().then(setProg).catch(() => setProg(null)) }, [])

  const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-ink)' }

  if (!prog) return (
    <div className="rounded-xl border border-line bg-surface p-4 mb-6">
      <div className="text-[12px] text-faint">进度数据加载中…</div>
    </div>
  )

  const totalGoal = prog.total_word_goal ?? 100000
  const dailyGoal = prog.daily_word_goal ?? null
  const totalWords = prog.total_words ?? 0
  const todayWords = prog.today_words ?? 0
  const totalPct = Math.min(100, Math.round((totalWords / totalGoal) * 100))
  const dailyPct = dailyGoal ? Math.min(120, Math.round((todayWords / dailyGoal) * 100)) : null
  const dailyMet = dailyGoal ? todayWords >= dailyGoal : null

  // 整稿进度条颜色:< 50% 品牌蓝,< 100% 黛绿,>= 100% 金
  const totalBarColor = totalPct >= 100 ? '#f59e0b' : totalPct >= 50 ? '#16a34a' : 'var(--color-brand)'
  const dailyBarColor = dailyMet ? '#16a34a' : 'var(--color-brand)'

  const daily = prog.daily || []

  return (
    <div className="rounded-xl border border-line bg-surface p-5 mb-6">
      {/* 标题行 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp size={15} className="text-brand" />
          <span className="text-[14px] font-semibold text-ink">码字进度</span>
        </div>
        <button onClick={onGoalEdit}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer">
          <Pencil size={11} />编辑目标
        </button>
      </div>

      {/* 荣誉位:今日 + streak */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="rounded-lg bg-canvas border border-line p-3 text-center">
          <div className="text-[11px] text-faint mb-0.5">今日码字</div>
          <div className={`text-[22px] font-semibold tnum ${dailyMet ? 'text-ok' : 'text-ink'}`}>
            +{todayWords.toLocaleString()}
          </div>
          {dailyGoal && (
            <div className={`text-[10px] mt-0.5 ${dailyMet ? 'text-ok' : 'text-faint'}`}>
              {dailyMet ? '✓ 今日达标' : `目标 ${dailyGoal.toLocaleString()}`}
            </div>
          )}
        </div>
        <div className="rounded-lg bg-canvas border border-line p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-[11px] text-faint mb-0.5">
            <Flame size={11} />当前连胜
          </div>
          <div className="text-[22px] font-semibold tnum text-fore">{prog.current_streak}</div>
          <div className="text-[10px] text-faint mt-0.5">天</div>
        </div>
        <div className="rounded-lg bg-canvas border border-line p-3 text-center">
          <div className="flex items-center justify-center gap-1 text-[11px] text-faint mb-0.5">
            <Trophy size={11} />最长连胜
          </div>
          <div className="text-[22px] font-semibold tnum text-fore">{prog.longest_streak}</div>
          <div className="text-[10px] text-faint mt-0.5">天</div>
        </div>
      </div>

      {/* 整稿进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5 text-[12px]">
          <span className="text-faint">整稿进度</span>
          <span className="tnum text-ink font-medium">{totalWords.toLocaleString()} / {totalGoal.toLocaleString()} 字 · {totalPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-soft overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: Math.min(100, totalPct) + '%', background: totalBarColor }} />
        </div>
        {totalPct >= 100 && <div className="text-[10px] text-[#f59e0b] mt-1">整稿目标达成！</div>}
      </div>

      {/* 每日目标进度条(设了才显示) */}
      {dailyGoal && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5 text-[12px]">
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

      {/* 图表:每日字数 + 累计曲线 */}
      {daily.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-2">
          <div>
            <div className="text-[11px] text-faint mb-2">每日字数</div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={daily} margin={{ left: -20, right: 4, top: 2 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--color-faint)' }}
                  tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: 'var(--color-faint)' }} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v.toLocaleString() + ' 字', '当日']} />
                {dailyGoal && <ReferenceLine y={dailyGoal} stroke="#16a34a" strokeDasharray="3 3" strokeWidth={1} />}
                <Bar dataKey="words" name="字数" radius={[3, 3, 0, 0]} fill="var(--color-brand)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div>
            <div className="text-[11px] text-faint mb-2">累计推进</div>
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart data={daily} margin={{ left: -20, right: 4, top: 2 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                <XAxis dataKey="date" tick={{ fontSize: 9, fill: 'var(--color-faint)' }}
                  tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fontSize: 9, fill: 'var(--color-faint)' }} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v.toLocaleString() + ' 字', '累计']} />
                {totalGoal && <ReferenceLine y={totalGoal} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1} />}
                <Area type="monotone" dataKey="cumulative" name="累计" stroke="var(--color-brand)"
                  fill="var(--color-brand)" fillOpacity={0.15} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* GitHub 风码字热力图 */}
      <WordHeatmap heatmap={prog.heatmap || []} dailyGoal={dailyGoal} />
    </div>
  )
}

// ── GitHub 风码字热力图 ──────────────────────────────────────────────────────
// 近 ~91 天(13 周),每格一天,按列(周)× 行(星期几)排列
// 5 档色阶:0 / <0.5× / <1× / ≥1× / >1.2× 每日目标(无目标按 >0 / >500 / >1000 分档)
function WordHeatmap({ heatmap, dailyGoal }) {
  // 把 heatmap 数组转 Map<date, words>
  const wordMap = {}
  for (const { date, words } of heatmap) {
    wordMap[date] = words ?? 0
  }

  // 生成近 91 天(13 周 × 7 天)的日历格
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const WEEKS = 13
  const DAYS = WEEKS * 7
  // 从最早那个周日开始(让今天落在最后一列最后一格)
  const todayDow = today.getDay() // 0=周日
  // 往回数到最近的周日(或今天本身)
  const startDay = new Date(today)
  startDay.setDate(today.getDate() - (DAYS - 1))

  // 生成 [cols][rows] 结构:col=周索引(0..12),row=星期几(0=周日..6=周六)
  const cols = Array.from({ length: WEEKS }, (_, wi) =>
    Array.from({ length: 7 }, (_, di) => {
      const d = new Date(startDay)
      d.setDate(startDay.getDate() + wi * 7 + di)
      const dateStr = d.toISOString().slice(0, 10)
      const words = wordMap[dateStr] ?? null // null=未来/无数据
      const isFuture = d > today
      return { dateStr, words, isFuture, dow: di }
    })
  )

  // 色阶计算
  const cellColor = (words, isFuture) => {
    if (isFuture || words === null) return 'var(--color-soft)'
    if (words <= 0) return 'var(--color-soft)'
    if (dailyGoal) {
      if (words >= dailyGoal * 1.2) return '#15803d'   // 超额:深绿
      if (words >= dailyGoal) return '#22c55e'          // 达标:绿
      if (words >= dailyGoal * 0.5) return '#86efac'   // 过半:浅绿
      return '#bbf7d0'                                   // 有写但不足一半:很浅绿
    } else {
      // 无目标:按字数绝对值分档
      if (words >= 2000) return '#15803d'
      if (words >= 1000) return '#22c55e'
      if (words >= 300) return '#86efac'
      return '#bbf7d0'
    }
  }

  const DOW_LABELS = ['日', '', '二', '', '四', '', '六']
  // 月份标签:每列取该列第一天(周日)的月,遇到月首才显示
  const monthLabels = cols.map((col) => {
    const d = new Date(col[0].dateStr)
    // 若该周内有月份切换,显示月名
    const firstDate = d.getDate()
    if (firstDate <= 7) return d.toLocaleDateString('zh-CN', { month: 'short' })
    return ''
  })

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] text-faint">码字热力图 · 近 {WEEKS} 周</div>
        <div className="flex items-center gap-1.5 text-[10px] text-faint">
          <span>少</span>
          {['var(--color-soft)', '#bbf7d0', '#86efac', '#22c55e', '#15803d'].map((c, i) => (
            <div key={i} className="w-3 h-3 rounded-sm" style={{ background: c }} />
          ))}
          <span>多</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: `16px repeat(${WEEKS}, 12px)`, gap: '2px', alignItems: 'start' }}>
          {/* 月份标签行 */}
          <div />
          {monthLabels.map((label, wi) => (
            <div key={wi} style={{ fontSize: 9, color: 'var(--color-faint)', lineHeight: '12px', textAlign: 'center' }}>
              {label}
            </div>
          ))}
          {/* 7 行(星期几) */}
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
                  <div
                    key={`${wi}-${dow}`}
                    title={tip}
                    style={{
                      width: 12, height: 12,
                      borderRadius: 2,
                      background: bg,
                    }}
                  />
                )
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── 主视图 ───────────────────────────────────────────────────────────────────
export function InsightView({ onJumpChapter }) {
  const [q, setQ] = useState(null)
  const [intent, setIntent] = useState(null)
  const [goalOpen, setGoalOpen] = useState(false)
  const [progressKey, setProgressKey] = useState(0)

  useEffect(() => { api.quality().then(setQ) }, [])
  useEffect(() => { api.intent().then(setIntent).catch(() => setIntent({})) }, [])

  if (!q) return <div className="p-8 text-faint">加载中…</div>

  const chs = q.chapters || []
  const weak = [...chs].filter((c) => c.qc_issues > 0 || c.causal > 0).sort((a, b) => (b.qc_issues + b.causal) - (a.qc_issues + a.causal))
  const tooltipStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-line)', borderRadius: 8, fontSize: 12, color: 'var(--color-ink)' }
  const totalGoal = intent?.total_word_goal ?? 100000

  return (
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-5xl mx-auto px-8 py-8">
        <div className="flex items-center gap-2 mb-6"><Activity size={18} className="text-brand" /><h1 className="text-[22px] font-semibold prose-serif text-ink">质量仪表盘</h1></div>

        <GoalDialog
          open={goalOpen}
          intent={intent}
          onClose={() => setGoalOpen(false)}
          onSaved={() => {
            api.intent().then(setIntent)
            setProgressKey((k) => k + 1)
          }}
        />

        <ProgressPanel key={progressKey} onGoalEdit={() => setGoalOpen(true)} />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <Metric icon={FileText} label="规模" value={q.total_words?.toLocaleString() || 0}
            sub={`${chs.length} 章 · 目标 ${totalGoal.toLocaleString()} 字`} />
          <Metric icon={Bookmark} label="伏笔" value={q.foreshadow?.open ?? 0} sub={`未回收 · 已收 ${q.foreshadow?.closed ?? 0}`} tone="fore" />
          <Metric icon={ShieldAlert} label="伏笔超期" value={q.foreshadow?.overdue ?? 0} sub="埋下 >3 章未回收" tone={q.foreshadow?.overdue ? 'danger' : 'ok'} />
          <Metric icon={Activity} label="质检问题" value={chs.reduce((s, c) => s + c.qc_issues + c.causal, 0)} sub="确定性 QC + 因果" tone="danger" />
        </div>

        <PromiseLedger onJumpChapter={onJumpChapter} />

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
