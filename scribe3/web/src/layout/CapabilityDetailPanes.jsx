import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { DeduceStage } from '../DeduceStage'
import { SearchDetail } from '../capabilities/search/SearchDetail'
import { IssueDetail } from '../capabilities/issues/IssueDetail'
import { capabilityConfig, capabilityGroup, formatScope } from './capabilityTree'
import { useDeduceSel } from '../deduceContext'

const COPY = {
  recall_result: {
    title: '召回详情',
    body: '这里展示语义召回命中理由、上下文和跳转目标。搜索框与结果列表固定留在栏2。',
  },
  review_issue: {
    title: '校验详情',
    body: '这里展示校验命中的上下文、解释、定位和修复建议。命中列表固定留在栏2。',
  },
}

function CapabilityDetail({ node, title, body }) {
  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="text-f20 font-semibold text-ink">{title}</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-2 text-f14 font-semibold text-ink">{node?.label || title}</div>
          <p className="text-f13 leading-7 text-faint">{body}</p>
        </section>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-2 text-f14 font-semibold text-ink">钻取关系</div>
          <p className="text-f13 leading-7 text-faint">
            栏1选择能力,栏2选择目录或命中项,栏3展示当前详情。栏2不被详情替换,右栏只更新主编上下文。
          </p>
        </section>
      </div>
    </div>
  )
}

export function CapabilityGroupDetailPane({ node }) {
  const cfg = capabilityConfig(node?.capability)
  const group = capabilityGroup(node?.capability, node?.ref?.group)
  const title = group?.label || node?.label || '分类总览'
  const seq = node?.ref?.seq ?? node?.meta?.seq
  const actions = group?.actions || node?.payload?.actions || ['查看全部命中正文', '校验本章泄露', '问主编怎么改']
  const related = group?.related || node?.payload?.related || []
  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[58rem] space-y-4">
        <div>
          <div className="mb-2 text-f12 text-faint">
            {cfg?.title || '能力'} / <span className="text-ink">{title}</span>
          </div>
          <h2 className="text-f22 font-semibold text-ink">{title}</h2>
          <div className="mt-1 text-f13 text-faint">
            {formatScope(group?.scope || node?.payload?.scope || '当前分类', seq)} · {node?.meta?.count ?? group?.rows?.length ?? 0}项
          </div>
        </div>

        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-2 text-f12 font-medium text-faint">分类含义</div>
          <p className="text-f14 leading-7 text-ink">{group?.meaning || node?.payload?.meaning || '先选择分类总览,再进入具体条目详情。'}</p>
        </section>

        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-2 text-f12 font-medium text-faint">写作约束</div>
          <p className="border-l-2 border-brand bg-canvas px-3 py-2 text-f13 leading-7 text-ink">
            {group?.constraint || node?.payload?.constraint || '分类用于控制本章写作边界,避免目录和详情脱节。'}
          </p>
        </section>

        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-3 text-f12 font-medium text-faint">关联范围</div>
          {related.length === 0 ? (
            <div className="text-f13 text-faint">暂无关联项。</div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {related.map(([label, value]) => (
                <div key={`${label}:${value}`} className="rounded-md border border-line bg-canvas px-3 py-2">
                  <div className="text-f12 font-semibold text-ink">{label}</div>
                  <div className="mt-0.5 text-f11 text-faint">{value}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="flex flex-wrap gap-2">
          <button type="button" className="h-8 rounded-md bg-brand px-3 text-f12 text-brandfg">{actions[0]}</button>
          <button type="button" className="h-8 rounded-md border border-line bg-surface px-3 text-f12 text-ink">{actions[1]}</button>
          <button type="button" className="h-8 rounded-md border border-line bg-transparent px-3 text-f12 text-faint">{actions[2]}</button>
        </div>
      </div>
    </div>
  )
}

export function PromiseDetailPane({ node, work }) {
  const [ledger, setLedger] = useState(undefined)
  useEffect(() => {
    let alive = true
    setLedger(undefined)
    api.promisesLedger(work)
      .then((r) => { if (alive) setLedger(r && typeof r === 'object' ? r : {}) })
      .catch(() => { if (alive) setLedger(null) })
    return () => { alive = false }
  }, [node?.id, work])

  const seq = node?.ref?.seq ?? node?.meta?.seq
  const rows = useMemo(() => {
    if (!ledger || ledger === null) return []
    const open = Array.isArray(ledger.open) ? ledger.open : []
    const closed = Array.isArray(ledger.closed) ? ledger.closed : []
    const herring = Array.isArray(ledger.red_herring) ? ledger.red_herring : []
    const ref = node?.ref
    if (ref === 'payoff' && seq != null) return [...open, ...closed].filter((p) => p.payoff_chapter === seq)
    if (ref === 'setup' && seq != null) return [...open, ...closed].filter((p) => p.setup_chapter === seq)
    if (ref === 'overdue') return open.filter((p) => p.overdue || p.window?.state === 'overdue')
    if (ref === 'open') return open
    if (ref === 'done') return closed
    return [...open, ...closed, ...herring]
  }, [ledger, node?.ref, seq])

  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="text-f20 font-semibold text-ink">伏笔详情</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-3 text-f14 font-semibold text-ink">{node?.label || '伏笔台账'}</div>
          {ledger === undefined ? <div className="text-f13 text-faint">加载伏笔台账…</div>
            : ledger === null ? <div role="alert" className="text-f13 text-danger">伏笔台账加载失败。</div>
            : rows.length === 0 ? <div className="text-f13 text-faint">当前分组暂无伏笔。</div>
            : (
              <div className="space-y-2">
                {rows.map((p) => (
                  <div key={p.id || p.text} className="rounded-md border border-line bg-canvas px-3 py-2">
                    <div className="text-f13 font-medium text-ink">{p.text || p.title || p.id}</div>
                    <div className="mt-1 flex flex-wrap gap-2 text-f11 text-faint">
                      {p.setup_chapter != null && <span>埋:第 {p.setup_chapter} 章</span>}
                      {p.payoff_chapter != null && <span>收:第 {p.payoff_chapter} 章</span>}
                      {p.status && <span>状态:{p.status}</span>}
                      {(p.overdue || p.window?.state === 'overdue') && <span className="text-danger">超期</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
        </section>
      </div>
    </div>
  )
}

export function DeduceDetailPane({ node, work }) {
  const seq = node?.ref?.seq ?? node?.meta?.seq
  const { selected, setSelected } = useDeduceSel()
  const [meta, setMeta] = useState({ chars: [], deductions: [] })
  useEffect(() => {
    if (seq == null) {
      setMeta({ chars: [], deductions: [] })
      return
    }
    let alive = true
    Promise.all([
      api.chapter(seq, work).catch(() => ({})),
      api.entities().catch(() => []),
    ]).then(([ch, entities]) => {
      if (!alive) return
      setMeta({
        title: ch?.title || '',
        synopsis: ch?.synopsis || '',
        beats: ch?.beats || [],
        focalizer: ch?.focalizer || '',
        scene_truth: ch?.scene_truth || '',
        deductions: ch?.deductions || [],
        involved_characters: ch?.involved_characters || [],
        chars: (entities || []).filter((e) => e.kind === 'character'),
      })
    })
    return () => { alive = false }
  }, [seq, work])

  useEffect(() => {
    const view = node?.ref?.view
    if (!view) return
    if (view === 'truth') {
      if (selected !== 'truth') setSelected('truth')
      return
    }
    const candidate = meta.focalizer || meta.involved_characters?.[0] || meta.deductions?.[0]?.character_id || ''
    if (candidate && selected !== candidate) setSelected(candidate)
  }, [node?.ref?.view, meta.focalizer, meta.involved_characters, meta.deductions, selected, setSelected])

  return <DeduceStage key={node?.id} seq={seq} meta={meta} work={work} />
}

export function MotifDetailPane({ node, work }) {
  const [state, setState] = useState(undefined)
  const seq = node?.ref?.seq ?? node?.meta?.seq
  useEffect(() => {
    let alive = true
    setState(undefined)
    Promise.all([
      api.motifs(work).catch(() => null),
      seq != null ? api.motifInstances(seq, work).catch(() => null) : Promise.resolve([]),
    ]).then(([motifs, instances]) => {
      if (!alive) return
      if (motifs === null || instances === null) setState(null)
      else setState({ motifs: Array.isArray(motifs) ? motifs : [], instances: Array.isArray(instances) ? instances : [] })
    })
    return () => { alive = false }
  }, [node?.id, seq, work])

  const rows = useMemo(() => {
    if (!state || state === null) return []
    const evById = new Map(state.instances.map((i) => [i.motif_id, i.evidence]))
    const ref = node?.ref
    if (ref === 'chapter') return state.motifs.filter((m) => evById.has(m.id)).map((m) => ({ ...m, evidence: evById.get(m.id) }))
    if (ref === 'thin') return state.motifs.filter((m) => !m.theme && !m.unfolding)
    return state.motifs.map((m) => ({ ...m, evidence: evById.get(m.id) }))
  }, [node?.ref, state])

  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="text-f20 font-semibold text-ink">母题详情</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-3 text-f14 font-semibold text-ink">{node?.label || '母题台账'}</div>
          {state === undefined ? <div className="text-f13 text-faint">加载母题…</div>
            : state === null ? <div role="alert" className="text-f13 text-danger">母题加载失败。</div>
            : rows.length === 0 ? <div className="text-f13 text-faint">当前分组暂无母题。</div>
            : (
              <div className="space-y-2">
                {rows.map((m) => (
                  <div key={m.id || m.name} className="rounded-md border border-line bg-canvas px-3 py-2">
                    <div className="text-f13 font-medium text-ink">{m.name || m.id}</div>
                    {m.theme && <div className="mt-1 text-f12 text-fore">{m.theme}</div>}
                    {m.evidence && <div className="mt-1 text-f12 text-brand">证据:<span>{m.evidence}</span></div>}
                    {m.unfolding && <div className="mt-1 text-f12 text-faint">{m.unfolding}</div>}
                  </div>
                ))}
              </div>
            )}
        </section>
      </div>
    </div>
  )
}

export function RecallResultDetail({ node, onOpenTarget }) {
  return <SearchDetail node={node} onOpenTarget={onOpenTarget} />
}

export function ReviewIssueDetail({ node, onLocate, onRecheck }) {
  return <IssueDetail node={node} onLocate={onLocate} onRecheck={onRecheck} />
}
