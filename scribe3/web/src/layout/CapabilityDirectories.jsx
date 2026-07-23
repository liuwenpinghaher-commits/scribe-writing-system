import { DirectoryHeader } from './DirectoryHeader'
import { DirectoryRow, DirectorySectionLabel, DIR_SHELL } from './DirectoryRow'
import { capabilityConfig } from './capabilityTree'

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

export function CapabilityDirectory({ capability, seq, onSelectItem }) {
  const cfg = capabilityConfig(capability)
  if (!cfg) return null
  return (
    <div className={DIR_SHELL}>
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
