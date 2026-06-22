import { Sun, Moon, BookOpen, ChevronDown } from 'lucide-react'

// 应用级顶栏:字标 + 作品切换(点了回作品库)+ 主题。借鉴 scribe2 AppRail。
export function AppRail({ current, onOpenLibrary, theme, onTheme }) {
  return (
    <header className="h-12 shrink-0 flex items-center border-b border-line bg-surface px-3 gap-3">
      <span className="font-semibold tracking-wide text-brand text-sm select-none">SCRIBE3</span>
      <button onClick={onOpenLibrary} title="切换 / 选择作品"
        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[13px] max-w-[220px] text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand">
        <BookOpen size={14} className="shrink-0" />
        <span className="truncate">{current ? current.title : '选择作品'}</span>
        <ChevronDown size={11} className="shrink-0 opacity-50" />
      </button>
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
