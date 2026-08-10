import { Sun, Moon, BookOpen, ChevronDown, Network, Activity, Clock, Search, Settings, Compass, Shield, LogOut } from 'lucide-react'
import { PC_LAYOUT } from './layout/tokens'
import { BrandMark } from './BrandMark'

// F-06:write/codex 不再是顶栏 tab(已变成左侧项目树两支)。
// 顶栏横切视图 + 写作旅程(导演状态页)。
export const VIEWS = [
  { key: 'journey', label: '旅程', icon: Compass },
  { key: 'atlas', label: '图谱', icon: Network },
  { key: 'timeline', label: '时间线', icon: Clock },
  { key: 'insight', label: '仪表盘', icon: Activity },
]

// 全局栏搜索触发:默认打开左轨「搜索」能力(复用 useLeftDockCapabilities 已监听的
// s3-open-capability 事件),上层也可用 onSearch 覆写。Task 3:全局栏只负责触发,不自持搜索态。
// Task 10 Step 4:带 focus:true —— SearchDirectory 收到后聚焦其唯一搜索框,
// 与 ⌘K(App 层 keydown)派发同一事件,统一搜索入口,不各自持结果 store。
function triggerSearch(onSearch) {
  if (onSearch) { onSearch(); return }
  try { window.dispatchEvent(new CustomEvent('s3-open-capability', { detail: { capability: 'search', focus: true } })) } catch { /* 无窗口环境静默 */ }
}

// 应用级顶栏(Task 3:高度收敛到 PC_LAYOUT.topbar=44,职责按区域分隔):
//   作品切换 | 全局视图 | 搜索触发 | 主题 · 系统状态
// (Task 7:章阶段插槽 extra 已删——章阶段页签归 ChapterStudio 的 ObjectFrame,全局栏不再承载对象级 UI。)
// 高度取自布局 token(单一真源),不硬编码,与四栏 rail/directory 等尺寸同源。
// view:当前选中的横切 viewKey(null/无 = 在项目树/写作态,不高亮任何 tab)。
// status:系统状态区可注入的实时指示(连接/后台任务…),缺省中性,不谎报「在线」。
export function AppRail({
  current, view, onView, onOpenLibrary, theme, onTheme,
  showViews = true, onSearch, status = null, capsule = null,
  isAdmin = false, username = '', onLogout = null,
}) {
  return (
    <header data-testid="app-rail" style={{ height: PC_LAYOUT.topbar }}
      className="shrink-0 flex items-center border-b border-line/70 bg-surface px-4 gap-3">
      <BrandMark size={22} showWordmark />
      <button onClick={onOpenLibrary} title="切换 / 选择作品"
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-f13 max-w-[200px] text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand">
        <BookOpen size={14} className="shrink-0" />
        <span className="truncate">{current ? current.title : '选择作品'}</span>
        <ChevronDown size={11} className="shrink-0 opacity-50" />
      </button>

      {current && showViews && (
        <>
          <div className="w-px h-5 bg-line/80 shrink-0" data-testid="topbar-view-separator" />
          <nav className="flex items-center gap-0.5 rounded-md bg-soft/70 p-0.5" data-testid="topbar-global-views">
            {VIEWS.map(({ key, label, icon: Icon }) => {
              const on = view === key
              return (
                <button key={key} onClick={() => onView(key)} aria-current={on ? 'page' : undefined}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-f13 transition-colors shrink-0 cursor-pointer ${on ? 'bg-surface text-brand font-medium shadow-sm' : 'text-faint hover:text-ink'}`}>
                  <Icon size={14} /><span className="hidden sm:inline">{label}</span>
                </button>
              )
            })}
          </nav>
        </>
      )}

      {/* 搜索触发区:紧随全局视图的全局动作。theme 的 ml-auto 把「主题·系统状态」整体推到右缘。 */}
      {current && (
        <button data-testid="topbar-search" onClick={() => triggerSearch(onSearch)}
          title="全局搜索" aria-label="全局搜索"
          className="w-8 h-8 rounded-lg text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-brand">
          <Search size={15} />
        </button>
      )}

      {/* 写作导演进度胶囊(P0)：放在搜索与右簇之间 */}
      {current && capsule}

      {/* 主题:保留为右簇锚点(ml-auto)。设置中心入口(Task 12)紧贴主题按钮前,同属右簇。 */}
      <div className="ml-auto flex items-center gap-1" data-testid="topbar-theme">
        {isAdmin && (
          <button onClick={() => onView('admin')} aria-current={(view === 'admin' || (view === 'system')) ? 'page' : undefined}
            title={(view === 'admin' || view === 'system') ? '退出系统中心' : '管理台'}
            aria-label={view === 'admin' ? '退出管理台' : '管理台'}
            data-testid="topbar-admin"
            className={`h-7 w-7 rounded-md inline-flex items-center justify-center cursor-pointer ${
              view === 'admin' ? 'bg-soft text-brand' : 'text-faint hover:text-ink hover:bg-soft'}`}>
            <Shield size={15} />
          </button>
        )}
        <button onClick={() => onView('settings')} aria-current={(view === 'settings' || view === 'system') ? 'page' : undefined}
          title="设置" aria-label="设置"
          className={`h-7 w-7 rounded-md inline-flex items-center justify-center cursor-pointer ${
            (view === 'settings' || view === 'system') ? 'bg-soft text-brand' : 'text-faint hover:text-ink hover:bg-soft'}`}>
          <Settings size={15} />
        </button>
        <button onClick={() => onTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? '切换浅色' : '切换深色'} aria-label="切换深浅色"
          className="w-8 h-8 rounded-lg text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer">
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
        {username ? (
          <span
            className="hidden sm:inline max-w-[7rem] truncate text-f12 text-faint px-1"
            title={username}
            data-testid="topbar-username"
          >
            {username}
          </span>
        ) : null}
        {typeof onLogout === 'function' && (
          <button
            type="button"
            onClick={onLogout}
            title="退出当前账号"
            aria-label="退出当前账号"
            data-testid="topbar-logout"
            className="h-7 px-2 rounded-md text-f12 text-faint hover:text-ink hover:bg-soft inline-flex items-center gap-1 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <LogOut size={14} />
            <span className="hidden sm:inline">退出</span>
          </button>
        )}
      </div>

      {/* 系统状态区:独立成格,承载注入的实时指示;缺省中性圆点,不谎报状态。 */}
      <div data-testid="topbar-status" title="系统状态"
        className="flex items-center gap-1.5 pl-2 border-l border-line text-faint">
        {status ?? <span aria-hidden className="w-1.5 h-1.5 rounded-full bg-faint/50" />}
      </div>
    </header>
  )
}
