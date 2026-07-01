import { useEffect, useState } from 'react'
import { cn } from './lib/utils'

// 宽度持久化(借鉴 scribe2 WorkspaceShell)
function useNumPref(key, def) {
  const [v, setV] = useState(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : Number(s) || def } catch { return def }
  })
  useEffect(() => { try { localStorage.setItem(key, String(v)) } catch { /* */ } }, [key, v])
  return [v, setV]
}

function RailBtn({ icon: Icon, label, badge, on, onClick, side }) {
  return (
    <button onClick={onClick} aria-label={label} aria-pressed={on}
      className={cn('group relative w-9 h-9 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer',
        on ? 'bg-soft text-brand ring-1 ring-line' : 'text-faint hover:bg-soft hover:text-ink')}>
      <Icon size={18} />
      {!!badge && badge > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-brand text-brandfg text-[9px] font-bold leading-4 text-center tnum">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
      <span className={cn('pointer-events-none absolute top-1/2 -translate-y-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-[11px] text-canvas opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50',
        side === 'left' ? 'left-full ml-2' : 'right-full mr-2')}>
        {label}
      </span>
    </button>
  )
}

function Resizer({ onDown }) {
  return <div onMouseDown={onDown}
    className="w-px shrink-0 bg-line hover:bg-brand/50 cursor-col-resize relative z-10 transition-colors"
    style={{ marginInline: '-1px', width: 3 }} />
}

export function Rail({ side, caps, active, onActive }) {
  return (
    <div className={cn('w-12 shrink-0 bg-surface flex flex-col items-center py-2 gap-1',
      side === 'left' ? 'border-r' : 'border-l', 'border-line')}>
      {caps.map((c) => (
        <RailBtn key={c.key} icon={c.icon} label={c.label} badge={c.badge} side={side}
          on={active === c.key} onClick={() => onActive(active === c.key ? '' : c.key)} />
      ))}
    </div>
  )
}

/** WorkspaceShell:[左轨][左面板][中区 自适应][右面板][右轨],面板可拖拽改宽、可折叠。 */
export function Shell({ topbar, left, center, right }) {
  const [lw, setLw] = useNumPref('s3.lw', 250)
  const [rw, setRw] = useNumPref('s3.rw', 332)
  const lCap = left?.caps.find((c) => c.key === left.active)
  const rCap = right?.caps.find((c) => c.key === right.active)

  const startResize = (which) => (e) => {
    e.preventDefault()
    const x0 = e.clientX, w0 = which === 'l' ? lw : rw
    const move = (ev) => {
      const w = Math.max(190, Math.min(620, which === 'l' ? w0 + (ev.clientX - x0) : w0 - (ev.clientX - x0)))
      ;(which === 'l' ? setLw : setRw)(w)
    }
    const up = () => {
      document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up)
      document.body.style.cursor = ''; document.body.style.userSelect = ''
    }
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up)
    document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'
  }

  return (
    <div className="h-full flex flex-col bg-canvas">
      {topbar}
      <div className="flex-1 min-h-0 flex">
        {lCap && (
          <>
            <div className="shrink-0 bg-surface border-r border-line flex flex-col min-h-0" style={{ width: lw }}>
              {/* 带文字标签的 tab 条(常显,高亮当前)——设计要求"左面板 tabs",不能只有窄图标轨 */}
              <div className="shrink-0 flex items-center gap-0.5 px-1.5 pt-2 pb-1 border-b border-line overflow-x-auto">
                {left.caps.map((c) => (
                  <button key={c.key} onClick={() => left.onActive(c.key)}
                    className={cn('shrink-0 px-2 h-6 rounded-md text-[11.5px] whitespace-nowrap transition-colors cursor-pointer inline-flex items-center gap-1',
                      left.active === c.key ? 'bg-brand text-brandfg font-medium' : 'text-faint hover:bg-soft hover:text-ink')}>
                    {c.icon && <c.icon size={12} />}{c.label.split(' · ')[0]}
                    {!!c.badge && c.badge > 0 && <span className="text-[9px] tnum opacity-80">{c.badge}</span>}
                  </button>
                ))}
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3">{lCap.render()}</div>
            </div>
            <Resizer onDown={startResize('l')} />
          </>
        )}
        <main className="flex-1 min-w-[480px] overflow-hidden flex flex-col">{center}</main>
        {rCap && (
          <>
            <Resizer onDown={startResize('r')} />
            <div className="shrink-0 bg-surface border-l border-line flex flex-col min-h-0" style={{ width: rw }}>
              <div className="flex items-center h-9 shrink-0 px-3 border-b border-line">
                <span className="text-[11px] font-semibold uppercase tracking-[.08em] text-faint">{rCap.label}</span>
              </div>
              <div className={rCap.bare ? 'flex-1 min-h-0' : 'flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3'}>{rCap.render()}</div>
            </div>
          </>
        )}
        {right && <Rail side="right" {...right} />}
      </div>
    </div>
  )
}
