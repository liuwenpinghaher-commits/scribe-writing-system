import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { DirectoryHeader } from './DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './DirectoryRow'
import { capabilityConfig } from './capabilityTree'
import {
  filterPromiseRows,
  filterMotifRows,
  promiseItemNode,
  motifItemNode,
} from './capabilityItems'

function rowRef(row, seq, groupId) {
  if (typeof row.ref === 'object') return { ...row.ref, group: groupId, seq }
  return row.ref
}

function toDetailNode(row, seq, group) {
  return {
    id: row.id,
    type: row.type,
    capability: group.capability,
    ref: rowRef(row, seq, group.id),
    label: row.label,
    meta: { seq, group: group.id },
  }
}

function toGroupNode(capability, group, seq) {
  return {
    id: `${capability}:${group.id}`,
    type: 'capability_group',
    capability,
    ref: { group: group.id, seq },
    label: group.label,
    meta: { seq, tone: group.tone },
    payload: {
      meaning: group.meaning,
      constraint: group.constraint,
      scope: group.scope,
    },
  }
}

/** 演绎等：静态导航入口（非业务数据列表）。 */
function StaticCapabilityDirectory({ capability, seq, onSelectItem }) {
  const cfg = capabilityConfig(capability)
  if (!cfg) return null
  return (
    <div className={DIR_SHELL} data-testid={`capability-dir-${capability}`}>
      <DirectoryHeader title={cfg.title} />
      <div className="flex-1 min-h-0 overflow-auto px-2 py-2">
        <DirectorySectionLabel>上下文</DirectorySectionLabel>
        <div className="space-y-2">
          {cfg.groups.map((group) => (
            <section key={group.id}>
              <DirectoryRow
                title={group.label}
                meta={group.rows.length ? `${group.rows.length} 个入口` : undefined}
                onClick={() => onSelectItem?.(toGroupNode(capability, group, seq))}
                aria-label={group.label}
              />
              <div className="ml-2 border-l border-line/40 pl-1 space-y-0.5">
                {group.rows.map((row) => (
                  <DirectoryRow
                    key={row.id}
                    title={row.label}
                    meta={row.count != null ? row.count : undefined}
                    onClick={() => onSelectItem?.(toDetailNode(row, seq, { ...group, capability }))}
                    aria-label={row.label}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * 伏笔/母题：列表栏展示「分类 → 真实条目」；点条目 → 栏3 CodexDetail 详情。
 * 分类行本身不再把「条目列表」塞进详情栏。
 */
function LiveListCapabilityDirectory({ capability, seq, onSelectItem }) {
  const cfg = capabilityConfig(capability)
  const work = typeof api?.getWork === 'function' ? api.getWork() : undefined
  const [ledger, setLedger] = useState(undefined)
  const [motifState, setMotifState] = useState(undefined)
  const scheduleSeq = seq != null ? Number(seq) + 1 : 1

  useEffect(() => {
    if (capability !== 'promise') return undefined
    let alive = true
    setLedger(undefined)
    api.promisesLedger(work)
      .then((r) => { if (alive) setLedger(r && typeof r === 'object' ? r : {}) })
      .catch(() => { if (alive) setLedger(null) })
    return () => { alive = false }
  }, [capability, work])

  useEffect(() => {
    if (capability !== 'motif') return undefined
    let alive = true
    setMotifState(undefined)
    Promise.all([
      api.motifs(work).catch(() => null),
      seq != null ? api.motifInstances(seq, work).catch(() => null) : Promise.resolve([]),
      api.motifSchedule(scheduleSeq, work).catch(() => null),
    ]).then(([motifs, instances, schedule]) => {
      if (!alive) return
      if (motifs === null) setMotifState(null)
      else {
        setMotifState({
          motifs: Array.isArray(motifs) ? motifs : [],
          instances: Array.isArray(instances) ? instances : [],
          schedule: schedule && typeof schedule === 'object' ? schedule : null,
        })
      }
    })
    return () => { alive = false }
  }, [capability, work, seq, scheduleSeq])

  const groupsWithItems = useMemo(() => {
    if (!cfg) return []
    return cfg.groups.map((group) => {
      const sections = (group.rows || []).map((row) => {
        const ref = typeof row.ref === 'object' ? row.ref?.view : row.ref
        let items = []
        if (capability === 'promise' && ledger && ledger !== null) {
          items = filterPromiseRows(ledger, ref, seq).map((p) => promiseItemNode(p, seq, group.id))
        }
        if (capability === 'motif' && motifState && motifState !== null) {
          items = filterMotifRows(motifState, ref, seq).map((m) => motifItemNode(m, seq, group.id))
        }
        return { row, ref, items }
      })
      return { group, sections }
    })
  }, [cfg, capability, ledger, motifState, seq])

  if (!cfg) return null

  const loading = (capability === 'promise' && ledger === undefined)
    || (capability === 'motif' && motifState === undefined)
  const failed = (capability === 'promise' && ledger === null)
    || (capability === 'motif' && motifState === null)

  return (
    <div className={DIR_SHELL} data-testid={`capability-dir-${capability}`}>
      <DirectoryHeader
        title={cfg.title}
        status={seq != null ? (
          <span className="text-meta text-faint shrink-0">第{seq}章</span>
        ) : undefined}
      />
      <div className="flex-1 min-h-0 overflow-auto px-2 py-2">
        {loading && (
          <div className="px-1 py-2 text-meta text-faint" data-testid="capability-dir-loading">
            加载{cfg.title}列表…
          </div>
        )}
        {failed && (
          <div role="alert" className="px-1 py-2 text-meta text-danger" data-testid="capability-dir-error">
            {cfg.title}台账加载失败，请刷新。
          </div>
        )}
        {!loading && !failed && (
          <div className="space-y-3">
            {groupsWithItems.map(({ group, sections }) => (
              <section key={group.id} data-testid={`capability-group-${group.id}`}>
                <DirectorySectionLabel>{group.label}</DirectorySectionLabel>
                <div className="space-y-2">
                  {sections.map(({ row, items }) => (
                    <div key={row.id} className="space-y-0.5">
                      <div
                        className="px-2 py-1 text-meta font-medium text-faint"
                        data-testid={`capability-bucket-${row.id}`}
                      >
                        {row.label}
                        <span className="ml-1 tabular-nums text-faint/80">
                          ({items.length})
                        </span>
                      </div>
                      {items.length === 0 ? (
                        <div className="ml-2 px-2 py-0.5 text-meta text-faint/60">
                          暂无条目
                        </div>
                      ) : (
                        <div className="ml-1 border-l border-line/40 pl-1 space-y-0.5">
                          {items.map((item) => (
                            <DirectoryRow
                              key={item.id}
                              title={item.label}
                              meta={item.meta?.overdue ? '超期' : (item.meta?.status || item.meta?.heat || undefined)}
                              onClick={() => onSelectItem?.(item)}
                              aria-label={item.label}
                              data-testid={`capability-item-${item.id}`}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
        {!loading && !failed && seq == null && capability === 'promise' && (
          <div className="mt-2 px-1 text-meta text-faint leading-snug">
            未锚定章节时，「本章要收/新埋」可能为空；可先选手稿中的章，或从「仍悬/超期」看全书。
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 演绎：左栏列「场景真相」+ 本章涉及角色；点角色直开该角色限知详情。
 * 冲突/可公开等视图入口保留为次要入口。
 */
function DeduceLiveDirectory({ seq, onSelectItem }) {
  const cfg = capabilityConfig('deduce')
  const work = typeof api?.getWork === 'function' ? api.getWork() : undefined
  const [state, setState] = useState(undefined) // { involved, charsById, truthOk } | null fail

  useEffect(() => {
    if (seq == null) {
      setState({ involved: [], charsById: {}, truthOk: false, noSeq: true })
      return undefined
    }
    let alive = true
    setState(undefined)
    Promise.all([
      api.chapter(seq, work).catch(() => null),
      api.entities().catch(() => []),
    ]).then(([ch, entities]) => {
      if (!alive) return
      if (ch === null) {
        setState(null)
        return
      }
      const chars = (Array.isArray(entities) ? entities : []).filter((e) => e.kind === 'character')
      const byId = Object.fromEntries(chars.map((c) => [c.id, c]))
      const involved = Array.isArray(ch?.involved_characters) ? ch.involved_characters : []
      const deds = Array.isArray(ch?.deductions) ? ch.deductions : []
      // 有演绎稿的角色也并入列表
      for (const d of deds) {
        if (d?.character_id && !involved.includes(d.character_id)) {
          involved.push(d.character_id)
        }
      }
      setState({
        involved,
        charsById: byId,
        truthOk: !!(ch?.scene_truth || '').trim(),
        noSeq: false,
      })
    })
    return () => { alive = false }
  }, [seq, work])

  if (!cfg) return null

  const roleItems = (state && state !== null)
    ? (state.involved || []).map((cid) => {
      const c = state.charsById[cid]
      const name = c?.name || String(cid).replace(/^role:/, '')
      return {
        id: `deduce:role:${cid}`,
        type: 'deduce_view',
        capability: 'deduce',
        ref: { view: 'roles', character_id: cid, seq },
        label: name,
        meta: { seq, character_id: cid },
      }
    })
    : []

  return (
    <div className={DIR_SHELL} data-testid="capability-dir-deduce">
      <DirectoryHeader
        title={cfg.title}
        status={seq != null ? (
          <span className="text-meta text-faint shrink-0">第{seq}章</span>
        ) : undefined}
      />
      <div className="flex-1 min-h-0 overflow-auto px-2 py-2 space-y-3">
        {state === undefined && (
          <div className="px-1 py-2 text-meta text-faint">加载演绎列表…</div>
        )}
        {state === null && (
          <div role="alert" className="px-1 py-2 text-meta text-danger">章节加载失败</div>
        )}
        {state?.noSeq && (
          <div className="px-1 py-2 text-meta text-faint leading-snug">
            请先在手稿中选择章节，再管理本章场景真相与角色限知。
          </div>
        )}
        {state && state !== null && !state.noSeq && (
          <>
            <section>
              <DirectorySectionLabel>场景基础</DirectorySectionLabel>
              <DirectoryRow
                title="场景真相"
                meta={state.truthOk ? '已填' : '未填'}
                onClick={() => onSelectItem?.({
                  id: 'deduce:truth',
                  type: 'deduce_view',
                  capability: 'deduce',
                  ref: { view: 'truth', seq },
                  label: '场景真相',
                  meta: { seq },
                })}
                aria-label="场景真相"
                data-testid="deduce-item-truth"
              />
            </section>
            <section>
              <DirectorySectionLabel>角色限知</DirectorySectionLabel>
              {roleItems.length === 0 ? (
                <div className="px-2 py-1 text-meta text-faint">
                  本章尚无涉及角色。可在演绎详情中添加，或经主编写入 involved_characters。
                </div>
              ) : (
                <div className="space-y-0.5">
                  {roleItems.map((item) => (
                    <DirectoryRow
                      key={item.id}
                      title={item.label}
                      meta="限知"
                      onClick={() => onSelectItem?.(item)}
                      aria-label={item.label}
                      data-testid={`deduce-item-${item.meta.character_id}`}
                    />
                  ))}
                </div>
              )}
            </section>
            <section>
              <DirectorySectionLabel>其它视图</DirectorySectionLabel>
              <div className="space-y-0.5">
                <DirectoryRow
                  title="冲突与误判"
                  onClick={() => onSelectItem?.({
                    id: 'deduce:conflict',
                    type: 'deduce_view',
                    capability: 'deduce',
                    ref: { view: 'conflict', seq },
                    label: '冲突与误判',
                    meta: { seq },
                  })}
                  aria-label="冲突与误判"
                />
                <DirectoryRow
                  title="可公开信息"
                  onClick={() => onSelectItem?.({
                    id: 'deduce:public',
                    type: 'deduce_view',
                    capability: 'deduce',
                    ref: { view: 'public', seq },
                    label: '可公开信息',
                    meta: { seq },
                  })}
                  aria-label="可公开信息"
                />
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}

export function CapabilityDirectory({ capability, seq, onSelectItem }) {
  if (capability === 'promise' || capability === 'motif') {
    return (
      <LiveListCapabilityDirectory
        capability={capability}
        seq={seq}
        onSelectItem={onSelectItem}
      />
    )
  }
  if (capability === 'deduce') {
    return <DeduceLiveDirectory seq={seq} onSelectItem={onSelectItem} />
  }
  return (
    <StaticCapabilityDirectory
      capability={capability}
      seq={seq}
      onSelectItem={onSelectItem}
    />
  )
}
