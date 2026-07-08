import { Sun, Moon, BookOpen, ChevronDown, Network, Activity, Clock } from 'lucide-react'

// F-06:write/codex 不再是顶栏 tab(已变成左侧项目树两支)。
// 顶栏只留「横切视图」入口:概览/图谱/时间线/仪表盘 → 点击切中间栏 view mode。
export const VIEWS = [
  { key: 'atlas', label: '图谱', icon: Network },
  { key: 'timeline', label: '时间线', icon: Clock },
  { key: 'insight', label: '仪表盘', icon: Activity },
]

// 应用级顶栏:字标 + 作品切换(回作品库)+ 章内阶段 tab + 横切视图 tab + 主题。
// view:当前选中的横切 viewKey(null/无 = 在项目树/写作态,不高亮任何 tab)。
export function AppRail({ current, view, onView, onOpenLibrary, theme, onTheme, showViews = true, extra = null }) {
  return (
    <header className="h-12 shrink-0 flex items-center border-b border-line bg-surface px-3 gap-3">
      <span className="font-semibold tracking-wide text-brand text-sm select-none">SCRIBE3</span>
      <button onClick={onOpenLibrary} title="切换 / 选择作品"
        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-f13 max-w-[200px] text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand">
        <BookOpen size={14} className="shrink-0" />
        <span className="truncate">{current ? current.title : '选择作品'}</span>
        <ChevronDown size={11} className="shrink-0 opacity-50" />
      </button>

      {current && extra && (
        <div className="min-w-0 flex items-center" data-testid="topbar-work-tabs">{extra}</div>
      )}

      {current && showViews && (
        <>
          <div className="w-px h-5 bg-line shrink-0" data-testid="topbar-view-separator" />
          <nav className="flex items-center gap-1" data-testid="topbar-global-views">
            {VIEWS.map(({ key, label, icon: Icon }) => {
              const on = view === key
              return (
                <button key={key} onClick={() => onView(key)} aria-current={on ? 'page' : undefined}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-f13 transition-colors relative shrink-0 cursor-pointer ${on ? 'text-brand font-medium after:absolute after:-bottom-[7px] after:left-1 after:right-1 after:h-0.5 after:bg-brand after:rounded-full' : 'text-faint hover:text-ink hover:bg-soft'}`}>
                  <Icon size={14} /><span className="hidden sm:inline">{label}</span>
                </button>
              )
            })}
          </nav>
        </>
      )}

      <div className="ml-auto flex items-center gap-1" data-testid="topbar-theme">
        <button onClick={() => onTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? '切换浅色' : '切换深色'} aria-label="切换深浅色"
          className="w-8 h-8 rounded-lg text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer">
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  )
}
