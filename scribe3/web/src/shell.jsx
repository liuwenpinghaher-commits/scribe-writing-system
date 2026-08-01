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
      className={cn('group relative w-full flex flex-col items-center gap-0.5 py-1.5 rounded-md transition-colors cursor-pointer',
        on ? 'bg-brand/10 text-brand' : 'text-faint hover:bg-soft hover:text-ink')}>
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

function GroupedRailSections({ groups, caps, renderButton }) {
  const known = new Set(groups.map((group) => group.key))
  const ungrouped = caps.filter((cap) => !known.has(cap.group || cap.scope))
  return (
    <>
      {groups.map((group) => {
        const items = caps.filter((cap) => (cap.group || cap.scope) === group.key)
        if (items.length === 0) return null
        return (
          <div key={group.key} role="group" aria-label={group.label}
            className="flex flex-col gap-0.5 border-b border-line/50 pb-2.5 last:border-0 last:pb-0">
            {items.map(renderButton)}
          </div>
        )
      })}
      {ungrouped.length > 0 && <div className="flex flex-col gap-0.5">{ungrouped.map(renderButton)}</div>}
    </>
  )
}

export function Rail({
  side,
  caps,
  active,
  onActive,
  secondaryCaps = [],
  secondaryActive,
  onSecondaryClick,
}) {
  const primaryButton = (cap) => (
    <RailBtn key={cap.key} cap={cap} label={shortLabel(cap)} badge={cap.badge}
      on={active === cap.key} onClick={() => onActive(active === cap.key ? '' : cap.key)} />
  )
  const secondaryButton = (cap) => (
    <RailBtn key={cap.key} cap={cap} label={shortLabel(cap)} badge={cap.badge}
      on={secondaryActive === cap.key} onClick={() => onSecondaryClick?.(cap.key)} />
  )

  return (
    <div data-testid="unified-entry-rail"
      className="w-[56px] h-full min-h-0 shrink-0 bg-surface flex flex-col border-r border-line/60">
      <div data-testid="primary-rail-scroll" className="flex-1 min-h-0 overflow-y-auto px-1 py-2.5 flex flex-col gap-2.5">
        <GroupedRailSections groups={GROUPS} caps={caps} renderButton={primaryButton} />
      </div>
      {secondaryCaps.length > 0 && (
        <div data-testid="collaboration-rail"
          className="shrink-0 max-h-[48%] overflow-y-auto border-t border-line/60 px-1 py-2 flex flex-col gap-2.5">
          <GroupedRailSections groups={RIGHT_GROUPS} caps={secondaryCaps} renderButton={secondaryButton} />
        </div>
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
