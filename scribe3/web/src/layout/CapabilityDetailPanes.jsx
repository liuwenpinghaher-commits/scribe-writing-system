import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { DeduceStage } from '../DeduceStage'
import { SearchDetail } from '../capabilities/search/SearchDetail'
import { IssueDetail } from '../capabilities/issues/IssueDetail'
import { capabilityConfig, capabilityGroup, formatScope } from './capabilityTree'
import { filterPromiseRows, filterMotifRows, MOTIF_VIEW_KEYS, normMotifId } from './capabilityItems'
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
          <h2 className="type-section text-ink">{title}</h2>
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
  // Task 10:数量/关联/动作只认 live payload,配置只出结构文案。
  //   · count:业务数量必须是真实数据;没有就不渲染(旧版拿 rows.length 顶替成"N项")。
  //   · related:旧配置里的静态关联对是假数据,已删;payload 没给就整段不渲染。
  //   · actions:必须带真实 onClick handler 才渲染成按钮(旧版三颗写死按钮点了没有任何效果)。
  const liveCount = node?.payload?.count
  const related = Array.isArray(node?.payload?.related) ? node.payload.related : []
  const actions = (Array.isArray(node?.payload?.actions) ? node.payload.actions : [])
    .filter((a) => a && a.label && typeof a.onClick === 'function')
  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[58rem] space-y-4">
        <div>
          <div className="mb-2 text-f12 text-faint">
            {cfg?.title || '能力'} / <span className="text-ink">{title}</span>
          </div>
          <h2 className="type-section text-ink">{title}</h2>
          <div className="mt-1 text-f13 text-faint">
            {formatScope(group?.scope || node?.payload?.scope || '当前分类', seq)}{liveCount != null ? ` · ${liveCount}项` : ''}
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

        {related.length > 0 && (
          <section className="rounded-lg border border-line bg-surface p-4">
            <div className="mb-3 text-f12 font-medium text-faint">关联范围</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {related.map(([label, value]) => (
                <div key={`${label}:${value}`} className="rounded-md border border-line bg-canvas px-3 py-2">
                  <div className="text-f12 font-semibold text-ink">{label}</div>
                  <div className="mt-0.5 text-meta text-faint">{value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map((action, i) => (
              <button
                key={action.label}
                type="button"
                onClick={action.onClick}
                className={i === 0
                  ? 'h-8 rounded-md bg-brand px-3 text-f12 text-brandfg'
                  : 'h-8 rounded-md border border-line bg-surface px-3 text-f12 text-ink'}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const PROMISE_TL_KIND = {
  plant: '埋设', clue: '线索', touch: '触及', closed: '兑现', abandoned: '弃置',
}

export function PromiseDetailPane({ node, work }) {
  const [ledger, setLedger] = useState(undefined)
  const [timeline, setTimeline] = useState(undefined)
  useEffect(() => {
    let alive = true
    setLedger(undefined)
    api.promisesLedger(work)
      .then((r) => { if (alive) setLedger(r && typeof r === 'object' ? r : {}) })
      .catch(() => { if (alive) setLedger(null) })
    return () => { alive = false }
  }, [node?.id, work])

  // 选中单条 promise 节点时拉时间线
  const singleId = (node?.type === 'promise' || node?.payload?.type === 'promise')
    ? (node?.ref || node?.id || node?.payload?.id)
    : (typeof node?.ref === 'string' && !['open', 'done', 'overdue', 'payoff', 'setup'].includes(node.ref)
      ? node.ref : null)
  useEffect(() => {
    if (!singleId || typeof singleId !== 'string') {
      setTimeline(undefined)
      return
    }
    // strip promise: prefix if present
    const pid = singleId.includes(':') ? singleId.split(':').pop() : singleId
    let alive = true
    setTimeline(undefined)
    api.promiseTimeline(pid)
      .then((t) => { if (alive) setTimeline(t && typeof t === 'object' ? t : null) })
      .catch(() => { if (alive) setTimeline(null) })
    return () => { alive = false }
  }, [singleId, work])

  const seq = node?.ref?.seq ?? node?.meta?.seq
  // 列表已在栏2；栏3 仅在单条 / 无单条时的引导
  const isBucket = typeof node?.ref === 'string'
    && ['open', 'done', 'overdue', 'payoff', 'setup', 'abandoned'].includes(node.ref)
  const rows = useMemo(() => {
    if (!ledger || ledger === null || !isBucket) return []
    return filterPromiseRows(ledger, node?.ref, seq)
  }, [ledger, node?.ref, seq, isBucket])

  const events = Array.isArray(timeline?.events) ? timeline.events : []
  const single = !!singleId

  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="type-section text-ink">{single ? (node?.label || '伏笔详情') : '伏笔'}</h2>
        </div>
        {!single && (
          <section className="rounded-lg border border-line bg-surface p-4" data-testid="promise-pick-hint">
            <p className="text-f13 leading-7 text-faint">
              请在<strong className="text-ink font-medium">左侧目录</strong>点具体伏笔条目查看详情与时间线；
              分类只用于组织列表，不再在详情栏重复列台账。
            </p>
            {isBucket && ledger && rows.length > 0 && (
              <p className="mt-2 text-meta text-faint">本组共 {rows.length} 条（详见左栏）。</p>
            )}
          </section>
        )}
        {timeline && events.length > 0 && (
          <section className="rounded-lg border border-line bg-surface p-4" data-testid="promise-detail-timeline">
            <div className="mb-3 text-f14 font-semibold text-ink">
              时间线 · {(timeline.promise?.text || node?.label || '').slice(0, 40)}
            </div>
            <div className="space-y-1.5">
              {events.map((e, i) => (
                <div key={`${e.kind}-${e.chapter}-${i}`}
                  className="flex items-start gap-2 text-f13 text-ink"
                  data-testid="promise-timeline-event"
                  data-kind={e.kind}
                >
                  <span className="text-meta text-faint shrink-0">第{e.chapter ?? '?'}章</span>
                  <span className="text-meta text-brand shrink-0">{PROMISE_TL_KIND[e.kind] || e.kind}</span>
                  <span className="flex-1 min-w-0 text-faint">{e.evidence || ''}</span>
                </div>
              ))}
            </div>
          </section>
        )}
        {single && ledger === undefined && (
          <div className="text-f13 text-faint">加载伏笔…</div>
        )}
        {single && ledger === null && (
          <div role="alert" className="text-f13 text-danger">伏笔加载失败。</div>
        )}
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

const HEAT_LABEL = { hot: '过热', cold: '该回声', neutral: '平稳' }

export function MotifDetailPane({ node, work }) {
  const [state, setState] = useState(undefined)
  const [timeline, setTimeline] = useState(undefined)
  const seq = node?.ref?.seq ?? node?.meta?.seq
  const scheduleSeq = seq != null ? Number(seq) + 1 : 1
  useEffect(() => {
    let alive = true
    setState(undefined)
    Promise.all([
      api.motifs(work).catch(() => null),
      seq != null ? api.motifInstances(seq, work).catch(() => null) : Promise.resolve([]),
      api.motifSchedule(scheduleSeq, work).catch(() => null),
    ]).then(([motifs, instances, schedule]) => {
      if (!alive) return
      if (motifs === null || instances === null) setState(null)
      else {
        setState({
          motifs: Array.isArray(motifs) ? motifs : [],
          instances: Array.isArray(instances) ? instances : [],
          schedule: schedule && typeof schedule === 'object' ? schedule : null,
        })
      }
    })
    return () => { alive = false }
  }, [node?.id, seq, work, scheduleSeq])

  const singleRef = (() => {
    const ref = typeof node?.ref === 'object' && node?.ref != null
      ? (node.ref.view || node.ref.group)
      : node?.ref
    if (ref != null && ref !== '' && !MOTIF_VIEW_KEYS.has(ref)) return normMotifId(ref)
    return null
  })()
  useEffect(() => {
    if (!singleRef) { setTimeline(undefined); return }
    let alive = true
    setTimeline(undefined)
    api.motifTimeline(singleRef, work)
      .then((t) => { if (alive) setTimeline(Array.isArray(t) ? t : null) })
      .catch(() => { if (alive) setTimeline(null) })
    return () => { alive = false }
  }, [singleRef, work])

  const rows = useMemo(() => {
    if (!state || state === null || singleRef) return []
    const ref = typeof node?.ref === 'object' && node?.ref != null
      ? (node.ref.view || node.ref.group)
      : node?.ref
    return filterMotifRows(state, ref, seq)
  }, [node?.ref, state, singleRef, seq])

  const events = Array.isArray(timeline) ? timeline : []
  const row = singleRef && state && state !== null
    ? (filterMotifRows(state, singleRef, seq)[0] || null)
    : null

  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="type-section text-ink">{singleRef ? (node?.label || row?.name || '母题详情') : '母题'}</h2>
        </div>
        {!singleRef && (
          <section className="rounded-lg border border-line bg-surface p-4" data-testid="motif-pick-hint">
            <p className="text-f13 leading-7 text-faint">
              请在<strong className="text-ink font-medium">左侧目录</strong>点具体母题条目查看详情与触及时间线。
            </p>
            {rows.length > 0 && (
              <p className="mt-2 text-meta text-faint">本组共 {rows.length} 条（详见左栏）。</p>
            )}
          </section>
        )}
        {singleRef && events.length > 0 && (
          <section className="rounded-lg border border-line bg-surface p-4" data-testid="motif-timeline">
            <div className="mb-3 text-f14 font-semibold text-ink">触及时间线</div>
            <div className="space-y-1.5">
              {events.map((e, i) => (
                <div key={`${e.chapter}-${i}`} className="flex items-start gap-2 text-f13 text-ink" data-testid="motif-timeline-event">
                  <span className="text-meta text-faint shrink-0">第{e.chapter ?? '?'}章</span>
                  <span className="flex-1 min-w-0 text-faint">{e.evidence || ''}</span>
                </div>
              ))}
            </div>
          </section>
        )}
        {singleRef && row && (
          <section className="rounded-lg border border-line bg-surface p-4" data-testid="motif-detail-card">
            <div className="flex items-center gap-2">
              <div className="text-f14 font-semibold text-ink">{row.name || row.id}</div>
              {row.heat && (
                <span className="text-meta text-faint" data-testid="motif-heat">{HEAT_LABEL[row.heat] || row.heat}</span>
              )}
            </div>
            {row.theme && <div className="mt-2 text-f13 text-fore">{row.theme}</div>}
            {(row.echoes || (Array.isArray(row.echo_terms) && row.echo_terms.length > 0)) && (
              <div className="mt-1 text-f12 text-faint">
                回声:{row.echoes || (row.echo_terms || []).join('/')}
              </div>
            )}
            {row.evidence && <div className="mt-1 text-f12 text-brand">证据:{row.evidence}</div>}
            {row.unfolding && <div className="mt-1 text-f12 text-faint">{row.unfolding}</div>}
            {(Number(row.hit_count || 0) > 0 || row.streak != null) && (
              <div className="mt-2 text-meta text-faint">
                全书触及 {row.hit_count || 0} 次
                {row.streak != null ? ` · 连续 ${row.streak}` : ''}
                {row.last_touch != null ? ` · 上次第${row.last_touch}章` : ''}
              </div>
            )}
          </section>
        )}
        {singleRef && state === undefined && (
          <div className="text-f13 text-faint">加载母题…</div>
        )}
        {singleRef && state === null && (
          <div role="alert" className="text-f13 text-danger">母题加载失败。</div>
        )}
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
