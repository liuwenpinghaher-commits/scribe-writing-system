import { Sun, Moon, BookOpen, ChevronDown, Feather, BookText, Network, Activity, MessagesSquare } from 'lucide-react'

export const VIEWS = [
  { key: 'write', label: '写作台', icon: Feather },
  { key: 'chat', label: '主编', icon: MessagesSquare },
  { key: 'codex', label: '设定库', icon: BookText },
  { key: 'atlas', label: '图谱', icon: Network },
  { key: 'insight', label: '仪表盘', icon: Activity },
]

// 应用级顶栏:字标 + 作品切换(回作品库)+ 视图 tab + 主题。借鉴 scribe2 AppRail。
export function AppRail({ current, view, onView, onOpenLibrary, theme, onTheme }) {
  return (
    <header className="h-12 shrink-0 flex items-center border-b border-line bg-surface px-3 gap-3">
      <span className="font-semibold tracking-wide text-brand text-sm select-none">SCRIBE3</span>
      <button onClick={onOpenLibrary} title="切换 / 选择作品"
        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[13px] max-w-[200px] text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand">
        <BookOpen size={14} className="shrink-0" />
        <span className="truncate">{current ? current.title : '选择作品'}</span>
        <ChevronDown size={11} className="shrink-0 opacity-50" />
      </button>

      {current && (
        <>
          <div className="w-px h-5 bg-line shrink-0" />
          <nav className="flex items-center gap-1 min-w-0 overflow-x-auto">
            {VIEWS.map(({ key, label, icon: Icon }) => {
              const on = view === key
              return (
                <button key={key} onClick={() => onView(key)} aria-current={on ? 'page' : undefined}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[13px] transition-colors relative shrink-0 cursor-pointer ${on ? 'text-brand font-medium after:absolute after:-bottom-[7px] after:left-1 after:right-1 after:h-0.5 after:bg-brand after:rounded-full' : 'text-faint hover:text-ink hover:bg-soft'}`}>
                  <Icon size={14} /><span className="hidden sm:inline">{label}</span>
                </button>
              )
            })}
          </nav>
        </>
      )}

      <div className="ml-auto flex items-center gap-1">
        <button onClick={() => onTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? '切换浅色' : '切换深色'} aria-label="切换深浅色"
          className="w-8 h-8 rounded-lg text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer">
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  )
}
