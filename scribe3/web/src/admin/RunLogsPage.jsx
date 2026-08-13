/**
 * 管理台 · 写路径日志（独立页）。
 * 一次写 / 存 / 宣称 = 一张卡；对照该跑没跑，不回传提示词。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'

const inputCls = 'px-2.5 py-1.5 rounded-md border border-line bg-surface text-f13 outline-none focus:ring-2 focus:ring-brand'
const btnCls = 'px-2.5 py-1.5 rounded-md text-f12 border border-line hover:bg-soft cursor-pointer'
const btnPrimary = 'px-2.5 py-1.5 rounded-md text-f12 bg-brand text-white hover:opacity-90 cursor-pointer'

const KIND_LABEL = { write: '写', save: '存', claim: '宣称' }
const ACTUAL_LABEL = {
  present: '有',
  empty: '空',
  absent: '无',
  dropped: '裁光',
  failed: '失败',
}
const FLAG_LABEL = {
  contract_slogan: '合同空喊',
  recall_secret_leak: '召回漏密',
  window_lie: '窗宽不实',
  empty_required: '该进却空',
}
const NAME_LABEL = {
  prefix: '身份前缀',
  secret_guard: '密语守卫',
  focalizer: '限知视角',
  structure_diversity: '结构多样性',
  narrative_contract: '场面合同',
  story_ember: '上章余烬',
  story_recall: '世界此刻',
  story_causal: '前因后果',
  event_drive: '事件驱动',
  event_drive_hook: '事件钩',
  drama_contract: '戏剧合同',
  drama_vacuum: '戏剧真空',
  outline: '大纲',
  envelope: '信封',
  codex: '正典',
  seed_words: '种子词',
  craft: '工艺',
  phase_role: '阶段角色',
  avoid: '避忌',
  revelation_discipline: '揭示纪律',
  sincerity: '诚意',
  purpose: '本章目的',
  volume_intro: '卷首',
  brief_must: '必须发生',
  pressure_drive: '压力驱动',
  author_prefs: '作者偏好',
  voice_anchor: '声口锚',
  reference_craft: '参考工艺',
  storyline_polish: '故事线打磨',
  discourse_soft: '话语讲法',
  story_move: '招式',
  deduction_final: '终稿推演',
  material_recall: '素材召回',
  final_reminder: '收束提醒',
  scene_truth_proj: '场面真相',
  request_constraint: '本轮约束',
  identity: '身份',
  write_protocol: '写协议',
  revision: '改稿',
  continue_snapshot: '续写快照',
  tool_scope: '工具范围',
  craft_skills_index: '技法索引',
  benchmark_advisory: '标杆提示',
  craft_gate: '工艺门',
  persist_chapter: '落库',
}

function fmtWhen(v) {
  if (v == null || v === '') return '—'
  if (typeof v === 'object') {
    v = v.datetime || v.dt || v.value || ''
  }
  if (typeof v === 'number') {
    const ms = v > 1e12 ? v : v * 1000
    const d = new Date(ms)
    return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString()
  }
  const s = String(v)
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
}

function Err({ e }) {
  if (!e) return null
  const msg = e?.body?.detail || e?.message || String(e)
  return (
    <div className="text-f12 text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-md px-3 py-2 mb-3">
      {msg}
    </div>
  )
}

function verdictChip(v) {
  const red = v === 'red'
  return (
    <span className={`px-1.5 py-0.5 rounded text-f12 ${
      red ? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300' : 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
    }`}>
      {red ? '该进未进' : '对照齐全'}
    </span>
  )
}

function rowQuality(row) {
  const q = row?.quality || {}
  const bits = []
  if (q.slogan) bits.push('合同空喊')
  if (q.title_only) bits.push('只剩标题')
  if (q.trimmed) bits.push('被腰斩')
  if (q.reveal_only) bits.push('仅揭示')
  const reason = row?.actual_reason
  if (reason && reason !== row.actual && !bits.includes(reason)) bits.push(reason)
  return bits.join(' · ') || '—'
}

export function RunLogsPage({ defaultWork = '' }) {
  const [works, setWorks] = useState([])
  const [work, setWork] = useState(defaultWork || '')
  const [kind, setKind] = useState('')
  const [verdict, setVerdict] = useState('')
  const [chapter, setChapter] = useState('')
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [sel, setSel] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [onlyRed, setOnlyRed] = useState(true)

  useEffect(() => {
    let cancelled = false
    const apply = (rows) => {
      if (cancelled) return
      setWorks(rows)
      setWork((cur) => {
        if (cur) return cur
        if (defaultWork) return defaultWork
        const g = typeof api.getWork === 'function' ? api.getWork() : ''
        if (g && rows.some((w) => w.slug === g)) return g
        return rows[0]?.slug || ''
      })
    }
    api.adminWorks({ archived: 'active', limit: 200 })
      .then((r) => apply(r.items || []))
      .catch(() => {
        api.works()
          .then((rows) => apply(Array.isArray(rows) ? rows : []))
          .catch((e) => { if (!cancelled) setError(e) })
      })
    return () => { cancelled = true }
  }, [defaultWork])

  useEffect(() => {
    if (defaultWork) setWork(defaultWork)
  }, [defaultWork])

  const loadList = useCallback(async () => {
    if (!work) {
      setItems([])
      setCount(0)
      return
    }
    setBusy(true)
    setError(null)
    try {
      const q = { limit: 50 }
      if (kind) q.kind = kind
      if (verdict) q.verdict = verdict
      if (chapter !== '' && Number.isFinite(Number(chapter))) q.chapter = Number(chapter)
      const r = await api.runCards(q, work)
      setItems(r.items || [])
      setCount(r.count ?? (r.items || []).length)
    } catch (e) {
      setError(e)
      setItems([])
    } finally {
      setBusy(false)
    }
  }, [work, kind, verdict, chapter])

  useEffect(() => { loadList() }, [loadList])

  const openCard = async (runId) => {
    if (!work || !runId) return
    setBusy(true)
    setError(null)
    try {
      const card = await api.runCard(runId, work)
      setSel(card)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const rows = useMemo(() => {
    const all = Array.isArray(sel?.rows) ? sel.rows : []
    return onlyRed ? all.filter((r) => r.verdict === 'red') : all
  }, [sel, onlyRed])

  return (
    <div className="space-y-3" data-testid="run-logs-page">
      <div>
        <div className="text-f14 font-semibold">写路径日志</div>
        <div className="text-f12 text-faint mt-0.5">
          一次写、存、宣称一张卡。看「该跑什么 / 跑没跑 / 跑得好不好」。不是账号审计，也不展示提示词。
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-end">
        <label className="block text-f12">
          <span className="text-faint mb-1 block">书</span>
          <select
            className={inputCls}
            data-testid="run-logs-work"
            value={work}
            onChange={(e) => { setSel(null); setWork(e.target.value) }}
          >
            <option value="">选择书籍</option>
            {works.map((w) => (
              <option key={w.slug} value={w.slug}>{w.title || w.slug}</option>
            ))}
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">类型</span>
          <select className={inputCls} value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">全部</option>
            <option value="write">写</option>
            <option value="save">存</option>
            <option value="claim">宣称</option>
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">对照</span>
          <select className={inputCls} value={verdict} onChange={(e) => setVerdict(e.target.value)}>
            <option value="">全部</option>
            <option value="red">该进未进</option>
            <option value="green">对照齐全</option>
          </select>
        </label>
        <label className="block text-f12">
          <span className="text-faint mb-1 block">章</span>
          <input
            className={`${inputCls} w-20`}
            value={chapter}
            onChange={(e) => setChapter(e.target.value.replace(/[^\d]/g, ''))}
            placeholder="全部"
            inputMode="numeric"
          />
        </label>
        <button type="button" className={btnCls} onClick={loadList} disabled={busy || !work}>
          {busy ? '加载中…' : '刷新'}
        </button>
      </div>

      <Err e={error} />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-4 items-start">
        <div className="rounded-lg border border-line overflow-hidden bg-surface">
          <table className="w-full text-f12">
            <thead className="bg-soft/80 text-faint text-left">
              <tr>
                <th className="px-3 py-2 font-medium">时间</th>
                <th className="px-3 py-2 font-medium">章</th>
                <th className="px-3 py-2 font-medium">类型</th>
                <th className="px-3 py-2 font-medium">对照</th>
                <th className="px-3 py-2 font-medium">红 / 绿</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr
                  key={it.run_id}
                  data-testid="run-logs-row"
                  className={`border-t border-line cursor-pointer hover:bg-soft/50 ${
                    sel?.run_id === it.run_id ? 'bg-soft/70' : ''
                  }`}
                  onClick={() => openCard(it.run_id)}
                >
                  <td className="px-3 py-2 text-faint whitespace-nowrap">{fmtWhen(it.created_at)}</td>
                  <td className="px-3 py-2">{it.chapter ?? '—'}</td>
                  <td className="px-3 py-2">{KIND_LABEL[it.kind] || it.kind || '—'}</td>
                  <td className="px-3 py-2">{verdictChip(it.verdict)}</td>
                  <td className="px-3 py-2 tnum">
                    {it.summary?.red ?? 0} / {it.summary?.green ?? 0}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-8 text-center text-faint">
                    {work ? '这本书还没有写 / 存 / 宣称记录。去写作台走一轮后再回来。' : '请先选一本书。'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="px-3 py-1.5 text-f12 text-faint border-t border-line">
            本页 {count} 条{busy ? ' · 加载中' : ''}
          </div>
        </div>

        <div className="rounded-lg border border-line bg-surface p-3 min-h-[240px]" data-testid="run-logs-detail">
          {!sel ? (
            <div className="text-f12 text-faint py-10 text-center">点左侧一条，看这一次该跑没跑</div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {verdictChip(sel.verdict)}
                <span className="text-f13 font-medium">
                  第 {sel.chapter ?? '—'} 章 · {KIND_LABEL[sel.kind] || sel.kind}
                </span>
                {sel.prompt_hard_profile && (
                  <span className="text-f12 text-faint">{sel.prompt_hard_profile}</span>
                )}
                {sel.assemble_ok === false && (
                  <span className="text-f12 text-red-600">组装未完成</span>
                )}
              </div>
              <div className="text-f12 text-faint space-y-0.5">
                <div>时间 {fmtWhen(sel.created_at)}</div>
                <div>卡号 {sel.run_id || '—'}</div>
                <div>请求 {sel.request_id || '—'}</div>
                {sel.outcome_status && <div>模型 {sel.outcome_status}</div>}
              </div>
              {Array.isArray(sel.quality_flags) && sel.quality_flags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {sel.quality_flags.map((f) => (
                    <span key={f} className="px-1.5 py-0.5 rounded bg-soft text-f12">
                      {FLAG_LABEL[f] || f}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className={onlyRed ? btnPrimary : btnCls}
                  onClick={() => setOnlyRed(true)}
                >
                  只看红行
                </button>
                <button
                  type="button"
                  className={!onlyRed ? btnPrimary : btnCls}
                  onClick={() => setOnlyRed(false)}
                >
                  全部步骤
                </button>
                <span className="text-f12 text-faint">
                  {(sel.rows || []).filter((r) => r.verdict === 'red').length} 红 / {(sel.rows || []).length} 步
                </span>
              </div>
              <div className="rounded-md border border-line overflow-auto max-h-[28rem]">
                <table className="w-full text-f12">
                  <thead className="bg-soft/80 text-faint text-left sticky top-0">
                    <tr>
                      <th className="px-2 py-1.5 font-medium">步骤</th>
                      <th className="px-2 py-1.5 font-medium">该跑</th>
                      <th className="px-2 py-1.5 font-medium">实际</th>
                      <th className="px-2 py-1.5 font-medium">字数</th>
                      <th className="px-2 py-1.5 font-medium">质量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.name} className="border-t border-line align-top">
                        <td className="px-2 py-1.5">
                          <div>{NAME_LABEL[r.name] || r.name}</div>
                          <div className="text-faint">{r.name}{r.tier ? ` · ${r.tier}` : ''}</div>
                        </td>
                        <td className="px-2 py-1.5">{r.expected ? '要有' : '不该有'}</td>
                        <td className="px-2 py-1.5">
                          <span className={r.verdict === 'red' ? 'text-red-600' : ''}>
                            {ACTUAL_LABEL[r.actual] || r.actual || '—'}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 tnum">{r.chars ?? 0}</td>
                        <td className="px-2 py-1.5 text-faint max-w-[14rem]">{rowQuality(r)}</td>
                      </tr>
                    ))}
                    {rows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-2 py-6 text-center text-faint">
                          {onlyRed ? '这一次没有红行。' : '没有步骤。'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RunLogsPage
