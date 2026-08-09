/**
 * 实体卡「状态与演变」+「谁知道」最小面板（PR-5 · 依赖 PR-4 读契约）。
 * 数据：GET /facts?entity=&include_closed=true&chapter=&with_knowers=1
 * 禁止 api.graph({ focus }) 拼装 knowers（极性错误）。
 */
import { useEffect, useMemo, useState } from 'react'
import { History, Users, Lock, Plus } from 'lucide-react'
import { api } from '../api'
import { SectionTitle, Empty, Btn } from '../ui'
import { seedChiefTruthSupersede } from '../lib/chiefSeed.js'

const HIDE_BUCKETS = new Set(['bridge', 'ingest_noise'])

function isOpenAt(row, chapter) {
  const ch = Number(chapter) || 0
  const vf = Number(row?.valid_from ?? 0)
  if (vf > ch) return false
  if (row?.valid_to == null || row?.valid_to === '') return true
  return Number(row.valid_to) > ch
}

function groupByAttribute(rows) {
  const m = new Map()
  for (const r of rows || []) {
    const a = r.attribute || '—'
    if (!m.has(a)) m.set(a, [])
    m.get(a).push(r)
  }
  for (const list of m.values()) {
    list.sort((a, b) => Number(a.valid_from || 0) - Number(b.valid_from || 0))
  }
  return m
}

export function EntityTruthPanel({
  entityId,
  entityLabel,
  chapter = 99999,
  detailType = 'chars',
}) {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')
  const [showEngine, setShowEngine] = useState(false)

  useEffect(() => {
    if (!entityId) {
      setRows([])
      return
    }
    let cancelled = false
    setErr('')
    setRows(null)
    api.listEntityTruths(entityId, {
      includeClosed: true,
      chapter,
      withKnowers: true,
      revealSecret: false,
    })
      .then((list) => {
        if (!cancelled) setRows(Array.isArray(list) ? list : [])
      })
      .catch((e) => {
        if (!cancelled) {
          setRows([])
          setErr(e?.body?.detail || e?.message || '加载世界真相失败')
        }
      })
    return () => { cancelled = true }
  }, [entityId, chapter])

  const visible = useMemo(() => {
    const all = rows || []
    if (showEngine) return all
    return all.filter((r) => !HIDE_BUCKETS.has(r.bucket))
  }, [rows, showEngine])

  const groups = useMemo(() => groupByAttribute(visible), [visible])

  const seedSupersede = (attr = '状态') => {
    seedChiefTruthSupersede({
      entityId,
      entityLabel,
      attribute: attr,
      valueHint: '（请填写新状态）',
      sinceChapter: '当前章',
    })
  }

  // SCRIBE3_TRUTH_UI=legacy_tree 时可不挂载（设计 PR-5）；前端可读 window 注入或 env 占位
  try {
    if (typeof window !== 'undefined' && window.__S3_TRUTH_UI === 'legacy_tree') {
      return null
    }
  } catch { /* */ }

  if (!entityId) return null

  return (
    <div
      id="entity-truth-panel"
      data-testid="entity-truth-panel"
      data-panel="truth"
      className="mt-6 pt-4 border-t border-line"
    >
      <SectionTitle
        icon={History}
        right={(
          <span className="inline-flex items-center gap-2">
            <button
              type="button"
              className="text-meta text-faint hover:text-ink cursor-pointer"
              onClick={() => setShowEngine((v) => !v)}
            >
              {showEngine ? '隐藏引擎行' : '显示引擎行'}
            </button>
            <Btn
              size="sm"
              variant="ghost"
              onClick={() => seedSupersede('状态')}
            >
              <Plus size={12} />
              让主编演变
            </Btn>
          </span>
        )}
      >
        状态与演变
      </SectionTitle>

      <p className="text-meta text-faint mb-3 leading-relaxed">
        关于本实体的时态真相（含已 supersede 的历史段）。日常改状态请走主编；势力档案镜像不会默认出现在此。
      </p>

      {err && (
        <div className="text-f12 text-danger mb-2">{err}</div>
      )}
      {rows === null && (
        <div className="text-f12 text-faint/60 py-2">真相加载中…</div>
      )}
      {rows && visible.length === 0 && (
        <Empty>
          尚无关于本实体的世界真相条目。人设档案字段在上方；时态状态由命题承载，可让主编登记演变。
        </Empty>
      )}

      {rows && visible.length > 0 && (
        <div className="space-y-4">
          {[...groups.entries()].map(([attr, segs]) => {
            const openSegs = segs.filter((s) => isOpenAt(s, chapter))
            const closedSegs = segs.filter((s) => !isOpenAt(s, chapter))
            return (
              <div key={attr} className="rounded-lg border border-line/60 bg-surface/40 px-3 py-2">
                <div className="text-f12 font-medium text-ink mb-1.5 flex items-center gap-2">
                  <span>{attr}</span>
                  {openSegs[0]?.is_secret && (
                    <Lock size={12} className="text-faint" title="私密" />
                  )}
                  <span className="text-meta text-faint font-normal">
                    {openSegs.length ? '当前' : '仅历史'}
                    {closedSegs.length ? ` · 历史 ${closedSegs.length}` : ''}
                  </span>
                </div>
                <ul className="space-y-2">
                  {[...openSegs, ...closedSegs].map((seg) => {
                    const open = isOpenAt(seg, chapter)
                    const knowers = open ? (seg.knowers || []) : []
                    return (
                      <li
                        key={seg.id || `${attr}-${seg.valid_from}-${seg.valid_to}`}
                        className={`text-f12 leading-relaxed ${open ? 'text-ink' : 'text-faint'}`}
                      >
                        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                          <span className={open ? 'font-medium' : ''}>
                            {seg.is_secret && !seg.value
                              ? '（私密）'
                              : (seg.value ?? '—')}
                          </span>
                          <span className="text-meta text-faint tnum">
                            第{seg.valid_from ?? '?'}章
                            {seg.valid_to != null ? `–${seg.valid_to}` : '–'}
                            {open ? ' · 仍生效' : ' · 已关闭'}
                          </span>
                          {seg.bucket && seg.bucket !== 'author' && seg.bucket !== 'state' && (
                            <span className="text-meta text-faint/70">{seg.bucket}</span>
                          )}
                        </div>
                        {open && (
                          <div className="mt-1 flex items-start gap-1.5 text-meta text-faint">
                            <Users size={12} className="shrink-0 mt-0.5 opacity-70" />
                            <span>
                              谁知道：
                              {knowers.length
                                ? knowers.map((k) => k.name || k.id).filter(Boolean).join('、')
                                : '（尚无角色知情边）'}
                              {seg.reader_knows ? (knowers.length ? '；读者已知' : '读者已知') : ''}
                            </span>
                          </div>
                        )}
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
