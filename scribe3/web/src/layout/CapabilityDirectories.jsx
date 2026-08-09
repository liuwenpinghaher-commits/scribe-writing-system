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
  return (
    <StaticCapabilityDirectory
      capability={capability}
      seq={seq}
      onSelectItem={onSelectItem}
    />
  )
}
