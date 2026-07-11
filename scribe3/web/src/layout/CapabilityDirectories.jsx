import { DirectoryHeader } from './DirectoryHeader'
import { capabilityConfig } from './capabilityTree'

function rowRef(row, seq, groupId) {
  if (typeof row.ref === 'object') return { ...row.ref, group: groupId, seq }
  return row.ref
}

// Task 10:节点只携带结构信息 + seq 上下文。业务数量/动作/关联不再从配置塞进
// meta/payload(旧版曾把 demo 计数与无 handler 动作一路带到详情面板),
// 这些值将来由 API live payload 提供,没有就整段不渲染。
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
    <div className="h-full min-h-0 flex flex-col">
      {/* 只喂标题:能力目录当前没有接通的筛选/同步/范围 handler,按统一合同不渲染假控件。
          真实数量与动作待后端接线后再按 count/primaryAction/secondaryActions 传入。 */}
      <DirectoryHeader title={cfg.title} />
      <div className="flex-1 min-h-0 overflow-auto px-3 py-3">
        <div className="mb-2 flex items-center justify-between text-meta uppercase tracking-wider text-faint/60">
          <span>上下文树</span>
          <span>{cfg.groups.length}类</span>
        </div>
        <div className="space-y-3">
          {cfg.groups.map((group) => (
            <section key={group.id} className="space-y-1.5">
              <button
                type="button"
                aria-label={group.label}
                onClick={() => onSelectItem?.(toGroupNode(capability, group, seq))}
                className="w-full rounded-md border border-line bg-surface px-2.5 py-2 text-left hover:border-brand/40 hover:bg-brand/5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-f12 font-semibold text-ink">{group.label}</span>
                  <span className="shrink-0 text-meta text-faint">{group.rows.length}项</span>
                </div>
                <div className="mt-0.5 truncate text-meta text-faint">{group.meta}</div>
              </button>
              <div className="space-y-1 pl-3">
                {group.rows.map((row) => (
                  <button
                    key={row.id}
                    type="button"
                    aria-label={row.label}
                    onClick={() => onSelectItem?.(toDetailNode(row, seq, { ...group, capability }))}
                    className="w-full grid grid-cols-[1fr_auto] items-center gap-2 rounded-md border-l-2 border-line bg-transparent px-2 py-1.5 text-left text-f12 text-ink hover:border-brand hover:bg-hover"
                  >
                    <span className="truncate">{row.label}</span>
                    {/* live 数量只认 API 注入的 row.count;配置不再写 demo 计数,
                        没有真值就不渲染(绝不渲 0/占位数字顶替)。 */}
                    {row.count != null && <span className="text-meta text-faint">{row.count}</span>}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
