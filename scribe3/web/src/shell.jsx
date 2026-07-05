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
          <span className="absolute -top-1.5 -right-2 min-w-[15px] h-[15px] px-1 rounded-full bg-brand text-brandfg text-f10 font-bold leading-[15px] text-center tnum">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </span>
      <span className="text-f10 leading-none whitespace-nowrap">{label}</span>
    </button>
  )
}

export function Rail({ side, caps, active, onActive }) {
  return (
    <div className={cn('w-[56px] shrink-0 bg-surface flex flex-col items-stretch px-1 py-2 gap-1',
      side === 'left' ? 'border-r' : 'border-l', 'border-line')}>
      {caps.map((c) => (
        <RailBtn key={c.key} cap={c} label={shortLabel(c)} badge={c.badge}
          on={active === c.key} onClick={() => onActive(active === c.key ? '' : c.key)} />
      ))}
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
