import { cn } from './lib/utils'

// 竖轨 tab 的常显短名:图标下方显示 2-3 字中文,不再靠 hover 才认得出。
// caps 里的 label 可能带 " · "(如「帧/意图」「演绎 · 角色限知」),取首段并压到短名。
const SHORT = {
  tree: '项目树', frame: '帧', deduce: '演绎', promise: '伏笔', motif: '母题', review: '校验',
  chief: '主编', versions: '存档',
}
function shortLabel(c) {
  return SHORT[c.key] || (c.label || '').split(/\s*·\s*|\//)[0].trim() || c.key
}

function RailBtn({ cap, label, badge, on, onClick }) {
  const Icon = cap.icon
  return (
    <button onClick={onClick} aria-label={cap.label} aria-pressed={on} title={cap.label}
      className={cn('group relative w-full flex flex-col items-center gap-0.5 py-1.5 rounded-lg transition-colors cursor-pointer',
        on ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink')}>
      <span className="relative inline-flex items-center justify-center">
        {Icon && <Icon size={18} />}
        {!!badge && badge > 0 && (
          <span className="absolute -top-1.5 -right-2 min-w-[15px] h-[15px] px-1 rounded-full bg-brand text-brandfg text-meta font-bold leading-[15px] text-center tnum">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
        {/* Task 8 · badge 未知态:数据拉取失败时不能静默成"无 badge"(读起来像 0 待办)——
            显式渲「?」并挂可访问名(cap.badgeUnknown 即 aria-label 文案),如实告知状态未知。 */}
        {!(badge > 0) && cap.badgeUnknown && (
          <span aria-label={cap.badgeUnknown} title={cap.badgeUnknown}
            className="absolute -top-1.5 -right-2 min-w-[15px] h-[15px] px-1 rounded-full bg-soft text-faint ring-1 ring-line text-meta font-bold leading-[15px] text-center">
            ?
          </span>
        )}
      </span>
      <span className="text-meta leading-none whitespace-nowrap">{label}</span>
    </button>
  )
}

// 竖轨入口分组(Task 3):左轨按「内容/工艺/检查」三组呈现,组间以分隔线区隔,
// 且每组挂 role="group"+aria-label,让辅助技术能识别这是三类不同职责的入口。
const GROUPS = [
  { key: 'content', label: '内容' },
  { key: 'craft', label: '工艺' },
  { key: 'inspect', label: '检查' },
]

// 右轨作用域分组(Task 8):右栏能力按"作用于什么"分——当前对象(随选中变)/
// 章节(选中章才有意义)/全局(常驻,与选中无关)。与左轨 GROUPS 平行但常量独立:
// 两轨分组维度不同(左=职责,右=作用域),字段也分开用 scope,互不串扰。
const RIGHT_GROUPS = [
  { key: 'object', label: '当前对象' },
  { key: 'chapter', label: '章节' },
  { key: 'global', label: '全局' },
]

export function Rail({ side, caps, active, onActive }) {
  const btn = (cap) => (
    <RailBtn key={cap.key} cap={cap} label={shortLabel(cap)} badge={cap.badge}
      on={active === cap.key} onClick={() => onActive(active === cap.key ? '' : cap.key)} />
  )
  // 右轨(Task 8):按 scope 三组渲染(当前对象/章节/全局),组挂 role="group"+aria-label
  // 供辅助技术识别;与左轨同一兜底纪律:未标 scope 的能力照旧补渲在末尾,绝不因分组丢入口。
  // (与左轨的分组循环刻意保持两份:左轨是 T3 定稿,共用抽象就得改它——零触碰优先于去重。)
  if (side === 'right') {
    const unscoped = caps.filter((c) => !RIGHT_GROUPS.some((g) => g.key === c.scope))
    return (
      <div className="w-[56px] shrink-0 bg-surface flex flex-col px-1 py-2 gap-2 border-l border-line">
        {RIGHT_GROUPS.map((group) => {
          const items = caps.filter((c) => c.scope === group.key)
          if (items.length === 0) return null
          return (
            <div key={group.key} role="group" aria-label={group.label}
              className="flex flex-col gap-1 border-b border-line pb-2 last:border-0 last:pb-0">
              {items.map(btn)}
            </div>
          )
        })}
        {unscoped.length > 0 && (
          <div className="flex flex-col gap-1">{unscoped.map(btn)}</div>
        )}
      </div>
    )
  }
  // 左轨:按组渲染。空组不出框(旧三栏 LeftDock 的非拆分入口也全部落进三组,不会空);
  // 兜底:万一有未归组的能力(未来新增/漏标),照旧扁平补渲在末尾,绝不因分组而丢入口。
  const ungrouped = caps.filter((c) => !GROUPS.some((g) => g.key === c.group))
  return (
    <div className="w-[56px] shrink-0 bg-surface flex flex-col px-1 py-2 gap-2 border-r border-line">
      {GROUPS.map((group) => {
        const items = caps.filter((c) => c.group === group.key)
        if (items.length === 0) return null
        return (
          <div key={group.key} role="group" aria-label={group.label}
            className="flex flex-col gap-1 border-b border-line pb-2 last:border-0 last:pb-0">
            {items.map(btn)}
          </div>
        )
      })}
      {ungrouped.length > 0 && (
        <div className="flex flex-col gap-1">{ungrouped.map(btn)}</div>
      )}
    </div>
  )
}

/** Shell:仅承载中区书稿(topbar/左右栏已上移到 BinderLayout 的 LeftDock/RightDock)。 */
export function Shell({ center }) {
  return (
    <div className="h-full flex flex-col bg-canvas">
      <main className="flex-1 min-w-[480px] overflow-hidden flex flex-col">{center}</main>
    </div>
  )
}
