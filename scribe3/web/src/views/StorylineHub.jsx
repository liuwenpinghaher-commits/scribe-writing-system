/**
 * 故事线中枢 — 融合弧实体 + 章进度 + 情绪 + focus 因果（SL1–SL5）
 * - 一次 /storyline/hub 拉齐 gantt + 情绪 + 实体 + overlay + refs
 * - craft_only：仅「写入生成提示」勾选的 notes 会进写路径
 * - 对标轴 uncomputed 不画假中柱
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  GitBranch, RefreshCw, Plus, Link2, BookOpen, Activity, Ruler, AlertTriangle, Trash2, Save,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, BarChart, Bar,
} from 'recharts'
import { api } from '../api'
import { Btn, Input } from '../ui.jsx'

const PHASE_LABEL = {
  outline: '大纲',
  beats: '节拍',
  deduce: '演绎',
  draft: '草稿',
  final: '正文',
}

const PHASE_BAR = {
  outline: 'bg-faint/40',
  beats: 'bg-brand/50',
  deduce: 'bg-brand/70',
  draft: 'bg-ok/50',
  final: 'bg-ok',
}

const CAUSAL_LABEL = {
  complete: '因果：完整',
  violations: '因果：有缺口',
  'no-data': '因果：尚无事件',
  gap: '因果：有缺口',
  ok: '因果：完整',
}

function phaseLabel(p) {
  return PHASE_LABEL[p] || p || '—'
}

function phaseBarClass(p) {
  return PHASE_BAR[p] || 'bg-soft'
}

function stakesLabel(hint) {
  if (hint === 'present') return '有代价'
  if (hint === 'missing') return '缺代价'
  return '—'
}

function Section({ title, icon: Icon, children, testId, action }) {
  return (
    <section
      className="rounded-lg border border-line/70 bg-surface/40 overflow-hidden"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-line/60 bg-soft/30">
        {Icon && <Icon size={15} className="text-brand shrink-0" />}
        <h3 className="text-f13 font-medium text-ink flex-1 min-w-0">{title}</h3>
        {action}
      </div>
      <div className="px-4 py-3">{children}</div>
    </section>
  )
}

function EmptyHint({ children }) {
  return <div className="text-f12 text-faint py-4 text-center">{children}</div>
}

export function StorylineHub({ work, onJumpChapter }) {
  const [gantt, setGantt] = useState(null)
  const [curve, setCurve] = useState(null)
  const [lines, setLines] = useState([])
  const [align, setAlign] = useState(null)
  const [overlay, setOverlay] = useState(null)
  const [refs, setRefs] = useState(null)
  const [focusSeq, setFocusSeq] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [linkSeq, setLinkSeq] = useState('')
  const [activeId, setActiveId] = useState('')
  const [editNotes, setEditNotes] = useState('')
  const [editKind, setEditKind] = useState('main')
  const [editCraftOnly, setEditCraftOnly] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setErr('')
    const w = work || undefined
    const hubP = typeof api.storylineHub === 'function'
      ? api.storylineHub(w)
      : Promise.reject(new Error('no hub'))

    hubP
      .then((pack) => {
        if (pack?.gantt) setGantt(pack.gantt)
        if (pack?.emotion) setCurve(pack.emotion)
        setLines(pack?.storylines || [])
        setAlign(pack?.align || pack?.emotion?.craft_align || null)
        setOverlay(pack?.overlay || null)
        setRefs(pack?.refs || null)
        if (pack?.focus_seq != null) setFocusSeq(pack.focus_seq)
      })
      .catch(async (ex) => {
        try {
          const [g, e, l] = await Promise.all([
            api.storylineGantt(w).catch(() => null),
            api.storylineEmotion(w).catch(() => null),
            (api.storylineLines ? api.storylineLines(w) : Promise.resolve({ storylines: [] })).catch(() => ({ storylines: [] })),
          ])
          if (g) setGantt(g)
          if (e) setCurve(e)
          setLines(l?.storylines || [])
          setAlign(e?.craft_align || null)
          if (!g && !e) setErr(ex?.message || '加载失败')
          else setErr('')
        } catch (e2) {
          setErr(ex?.message || e2?.message || '加载失败')
        }
      })
      .finally(() => setLoading(false))
  }, [work])

  useEffect(() => { load() }, [load])

  const active = useMemo(
    () => lines.find((sl) => sl.id === activeId) || null,
    [lines, activeId],
  )

  useEffect(() => {
    if (!active) {
      setEditNotes('')
      setEditKind('main')
      setEditCraftOnly(true)
      return
    }
    setEditNotes(active.notes || '')
    setEditKind(active.arc_kind || 'main')
    setEditCraftOnly(active.craft_only !== false)
  }, [active])

  const rows = useMemo(() => {
    if (overlay?.rows?.length) return overlay.rows
    return gantt?.rows || []
  }, [overlay, gantt])

  const maxSeq = useMemo(
    () => Math.max(1, ...rows.map((r) => Number(r.seq) || 0), 1),
    [rows],
  )

  const chartData = useMemo(() => {
    const pts = curve?.points || []
    return pts.map((p) => ({
      seq: p.seq,
      emotion: typeof p.emotion === 'number' ? p.emotion : ((p.tension || 0.5) - 0.5) * 10,
      label: p.label,
    }))
  }, [curve])

  const idealOverlay = useMemo(() => {
    const ideal = align?.ideal_resampled || []
    if (!ideal.length || !chartData.length) return []
    return chartData.map((d, i) => ({
      seq: d.seq,
      emotion: d.emotion,
      ideal: ideal[Math.min(i, ideal.length - 1)] ?? 0,
    }))
  }, [align, chartData])

  const dimBars = useMemo(() => {
    const dims = align?.core_dimensions || []
    return dims
      .filter((d) => {
        const src = d.source || ''
        if (src === 'uncomputed' || src === 'neutral_placeholder') return false
        if (d.score == null || Number.isNaN(Number(d.score))) return false
        return true
      })
      .map((d) => ({
        key: d.key,
        label: d.label || d.key,
        score: Number(d.score),
      }))
  }, [align])

  const uncomputedDims = useMemo(() => {
    const dims = align?.core_dimensions || []
    return dims.filter((d) => {
      const src = d.source || ''
      return src === 'uncomputed' || src === 'neutral_placeholder' || d.score == null
    })
  }, [align])

  const onCreate = async () => {
    setBusy(true)
    try {
      if (typeof api.storylineCreate === 'function') {
        await api.storylineCreate({
          title: title || '新故事线',
          craft_only: true,
        }, work)
      } else {
        await api.post('/storyline/lines', { title: title || '新故事线', craft_only: true, work }, work)
      }
      setTitle('')
      load()
    } catch (ex) {
      setErr(ex?.message || '创建失败')
    } finally {
      setBusy(false)
    }
  }

  const onLink = async () => {
    if (!activeId || !linkSeq) return
    setBusy(true)
    try {
      if (typeof api.storylineLink === 'function') {
        await api.storylineLink(activeId, { seq: Number(linkSeq) }, work)
      } else {
        await api.post(`/storyline/lines/${activeId}/link`, { seq: Number(linkSeq), work }, work)
      }
      setLinkSeq('')
      load()
    } catch (ex) {
      setErr(ex?.message || '关联失败')
    } finally {
      setBusy(false)
    }
  }

  const onSaveMeta = async () => {
    if (!activeId) return
    setBusy(true)
    try {
      if (typeof api.storylinePatch === 'function') {
        await api.storylinePatch(activeId, {
          notes: editNotes,
          arc_kind: editKind,
          craft_only: !!editCraftOnly,
        }, work)
      } else {
        await api.patch(`/storyline/lines/${activeId}`, {
          notes: editNotes,
          arc_kind: editKind,
          craft_only: !!editCraftOnly,
        }, work)
      }
      load()
    } catch (ex) {
      setErr(ex?.message || '保存失败')
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async () => {
    if (!activeId) return
    if (!window.confirm('确定删除这条故事线？')) return
    setBusy(true)
    try {
      if (typeof api.storylineDelete === 'function') {
        await api.storylineDelete(activeId, work)
      } else {
        await api.deleteObject?.('storyline', activeId)
      }
      setActiveId('')
      load()
    } catch (ex) {
      setErr(ex?.message || '删除失败')
    } finally {
      setBusy(false)
    }
  }

  if (loading && !gantt && !curve) {
    return (
      <div className="h-full grid place-items-center text-f13 text-faint" data-testid="storyline-loading">
        <div className="flex items-center gap-2">
          <RefreshCw size={16} className="animate-spin opacity-60" />
          加载故事线…
        </div>
      </div>
    )
  }

  if (err && !gantt && !curve && !lines.length) {
    return (
      <div className="h-full grid place-items-center text-f13" data-testid="storyline-error">
        <div className="text-center space-y-2 max-w-sm px-4">
          <AlertTriangle size={20} className="mx-auto text-warn" />
          <div className="text-danger">{err}</div>
          <Btn size="sm" onClick={load}>重试</Btn>
        </div>
      </div>
    )
  }

  const chartRows = idealOverlay.length ? idealOverlay : chartData
  const causalState = refs?.causal?.state
  const causalText = CAUSAL_LABEL[causalState] || '因果：—'

  return (
    <div className="h-full min-h-0 overflow-y-auto bg-canvas" data-testid="storyline-hub">
      <div className="max-w-5xl mx-auto px-5 py-5 md:px-7 md:py-6 space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <GitBranch size={18} className="text-brand shrink-0" />
          <h1 className="type-page prose-serif text-ink">故事线</h1>
          <span className="text-meta text-faint rounded bg-soft px-1.5 py-0.5">参考 · 不是打分</span>
          <div className="ml-auto flex items-center gap-2">
            <Btn
              size="sm"
              variant="ghost"
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-1"
              data-testid="storyline-refresh"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              刷新
            </Btn>
          </div>
        </div>
        <p className="text-f12 text-faint -mt-2">
          跨章弧意图登记 + 章进度 / 情绪起伏（参考）。不替代大纲、伏笔或因果校验。
        </p>
        {refs && (
          <div
            className="flex flex-wrap gap-3 text-f12 text-ink rounded-md border border-line/50 bg-soft/20 px-3 py-2"
            data-testid="storyline-refs"
          >
            <span>焦点章：{focusSeq ?? '—'}</span>
            <span data-testid="storyline-causal-state">{causalText}
              {refs.causal?.count ? `（${refs.causal.count}）` : ''}
            </span>
            <span>未收线伏笔（本章）：{refs.open_promise_count ?? 0}</span>
          </div>
        )}
        {err && (
          <div
            role="alert"
            className="rounded-md border border-warn/40 bg-warn/5 px-3 py-2 text-f12 text-ink"
            data-testid="storyline-err"
          >
            {err}
          </div>
        )}

        <Section title="故事线实体" icon={BookOpen} testId="storyline-entities">
          <div className="flex gap-2 mb-3 flex-wrap">
            <Input
              size="sm"
              className="flex-1 min-w-[10rem]"
              placeholder="新故事线标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              data-testid="storyline-title-input"
            />
            <Btn size="sm" onClick={onCreate} disabled={busy} className="inline-flex items-center gap-1" data-testid="storyline-create">
              <Plus size={14} /> 创建
            </Btn>
          </div>
          <ul className="text-f13 space-y-0.5 max-h-48 overflow-y-auto">
            {lines.map((sl) => {
              const on = activeId === sl.id
              return (
                <li key={sl.id}>
                  <button
                    type="button"
                    className={`w-full text-left rounded-md px-2.5 py-1.5 transition-colors cursor-pointer ${
                      on ? 'bg-brand/10 text-ink ring-1 ring-brand/30' : 'hover:bg-soft/70 text-ink'
                    }`}
                    onClick={() => setActiveId(sl.id)}
                    data-testid={`storyline-item-${sl.id}`}
                  >
                    <span className="font-medium">{sl.title}</span>
                    <span className="text-faint ml-2 text-f12">{sl.arc_kind || '弧'}</span>
                    <span className="text-faint ml-2 text-f12">
                      章:{(sl.chapter_seqs || []).join(', ') || '—'}
                    </span>
                    {sl.craft_only === false && (
                      <span className="ml-2 text-meta text-warn">不进生成</span>
                    )}
                    {sl.persisted && (
                      <span className="ml-2 text-meta text-ok">已存库</span>
                    )}
                  </button>
                </li>
              )
            })}
            {!lines.length && !loading && (
              <li><EmptyHint>暂无故事线 · 上方输入标题后创建</EmptyHint></li>
            )}
          </ul>
          <div className="flex gap-2 mt-3 flex-wrap items-center border-t border-line/50 pt-3">
            <Input
              size="sm"
              className="w-24"
              placeholder="章号"
              value={linkSeq}
              onChange={(e) => setLinkSeq(e.target.value)}
              data-testid="storyline-link-seq"
            />
            <Btn
              size="sm"
              variant="ghost"
              onClick={onLink}
              disabled={!activeId || busy}
              className="inline-flex items-center gap-1"
              data-testid="storyline-link"
            >
              <Link2 size={14} /> 关联到选中线
            </Btn>
            {!activeId && (
              <span className="text-meta text-faint">先点选一条故事线</span>
            )}
          </div>
          {activeId && (
            <div className="mt-3 space-y-2 border-t border-line/50 pt-3" data-testid="storyline-edit-panel">
              <label className="block text-f12 text-faint">
                弧类型
                <Input
                  size="sm"
                  className="mt-1 w-full"
                  value={editKind}
                  onChange={(e) => setEditKind(e.target.value)}
                  data-testid="storyline-arc-kind"
                />
              </label>
              <label className="block text-f12 text-faint">
                弧说明（notes）
                <textarea
                  className="mt-1 w-full min-h-[4rem] rounded-md border border-line bg-canvas px-2 py-1.5 text-f13 text-ink"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  data-testid="storyline-notes"
                  placeholder="写弧意图；默认可进生成提示（见下方勾选）"
                />
              </label>
              <label className="flex items-center gap-2 text-f12 text-ink cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!editCraftOnly}
                  onChange={(e) => setEditCraftOnly(e.target.checked)}
                  data-testid="storyline-craft-only"
                />
                写入生成提示（仅勾选时 notes 会进写作提示）
              </label>
              <div className="flex flex-wrap gap-2">
                <Btn
                  size="sm"
                  onClick={onSaveMeta}
                  disabled={busy}
                  className="inline-flex items-center gap-1"
                  data-testid="storyline-save-meta"
                >
                  <Save size={14} /> 保存
                </Btn>
                <Btn
                  size="sm"
                  variant="ghost"
                  onClick={onDelete}
                  disabled={busy}
                  className="inline-flex items-center gap-1 text-danger"
                  data-testid="storyline-delete"
                >
                  <Trash2 size={14} /> 删除
                </Btn>
              </div>
            </div>
          )}
        </Section>

        <Section title="章进度（轻量进度条）" icon={Activity} testId="storyline-gantt">
          <div className="space-y-1.5">
            {rows.map((r) => {
              const wPct = Math.max(8, Math.round((Number(r.seq) / maxSeq) * 100))
              const arcs = r.arcs || []
              return (
                <div
                  key={r.seq}
                  className="grid grid-cols-[2.5rem_1fr_auto] gap-2 items-center text-f12"
                >
                  <button
                    type="button"
                    className="text-brand tabular-nums text-left hover:underline cursor-pointer"
                    onClick={() => onJumpChapter?.(r.seq)}
                    title={`打开第 ${r.seq} 章`}
                  >
                    #{r.seq}
                  </button>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="truncate text-ink text-f13">{r.title}</span>
                      <span className="shrink-0 text-meta text-faint">{phaseLabel(r.phase)}</span>
                      {arcs.slice(0, 2).map((a) => (
                        <span key={a.id || a.title} className="text-meta text-brand/80 truncate max-w-[8rem]">
                          · {a.title}
                        </span>
                      ))}
                    </div>
                    <div className="h-1.5 rounded-full bg-soft overflow-hidden">
                      <div
                        className={`h-full rounded-full ${phaseBarClass(r.phase)}`}
                        style={{ width: `${wPct}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-meta text-faint shrink-0">
                    {stakesLabel(r.stakes_hint)}
                  </span>
                </div>
              )
            })}
            {!rows.length && !loading && <EmptyHint>暂无章节 · 在手稿中建章后出现于此</EmptyHint>}
          </div>
        </Section>

        <Section title="情绪起伏（-5…+5 · 参考）" icon={Activity} testId="emotion-chart">
          {chartRows.length > 0 ? (
            <div className="h-56 w-full min-h-[12rem]" data-testid="emotion-recharts">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" opacity={0.6} />
                  <XAxis dataKey="seq" tick={{ fontSize: 11, fill: 'var(--color-faint)' }} />
                  <YAxis domain={[-5, 5]} tick={{ fontSize: 11, fill: 'var(--color-faint)' }} width={32} />
                  <ReferenceLine y={0} stroke="var(--color-faint)" strokeOpacity={0.5} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-line)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="emotion"
                    stroke="var(--color-brand)"
                    name="情绪"
                    dot={{ r: 3 }}
                    strokeWidth={2}
                  />
                  {idealOverlay.length > 0 && (
                    <Line
                      type="monotone"
                      dataKey="ideal"
                      stroke="var(--color-fore, #f59e0b)"
                      name="理想"
                      strokeDasharray="4 4"
                      dot={false}
                      strokeWidth={1.5}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyHint>暂无情绪点 · 有章节梗概或正文后生成</EmptyHint>
          )}
          {curve?.disclaimer && (
            <p className="text-meta text-faint mt-2">{curve.disclaimer}</p>
          )}
        </Section>

        <Section title="节奏对标（参考）" icon={Ruler} testId="craft-align">
          {align ? (
            <div className="text-f13 space-y-2">
              <div className="flex flex-wrap gap-3 text-f12">
                <span>
                  与起承转合的距离：
                  <span className="tabular-nums text-ink font-medium">{align.dtw_distance ?? '—'}</span>
                </span>
                <span>
                  相似度：
                  <span className="tabular-nums text-ink font-medium">{align.similarity ?? '—'}</span>
                </span>
              </div>
              <div className="text-meta text-faint">仅作改节奏自比，不是文学分</div>
              {dimBars.length > 0 && (
                <div className="h-40 w-full" data-testid="dimension-bars">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dimBars} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" opacity={0.5} />
                      <XAxis dataKey="key" hide />
                      <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: 'var(--color-faint)' }} width={28} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--color-surface)',
                          border: '1px solid var(--color-line)',
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="score" fill="var(--color-brand)" name="实测轴" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              {uncomputedDims.length > 0 && (
                <p className="text-meta text-faint" data-testid="storyline-uncomputed-dims">
                  未测维度：{uncomputedDims.map((d) => d.label || d.key).join('、')}
                </p>
              )}
            </div>
          ) : (
            <EmptyHint>暂无对标数据</EmptyHint>
          )}
        </Section>
      </div>
    </div>
  )
}

export default StorylineHub
