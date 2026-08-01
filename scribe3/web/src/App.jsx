import { useEffect, useState } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { Library } from './Library'
import { BinderLayout } from './BinderLayout'
import { CommandPalette } from './CommandPalette'
import { ToastHost } from './ui/Toast'

const ACTIVE_WORK_STORAGE_KEY = 's3-active-work'

function readActiveWorkSlug() {
  try { return localStorage.getItem(ACTIVE_WORK_STORAGE_KEY) || '' } catch { return '' }
}

function writeActiveWorkSlug(slug) {
  try {
    if (slug) localStorage.setItem(ACTIVE_WORK_STORAGE_KEY, slug)
    else localStorage.removeItem(ACTIVE_WORK_STORAGE_KEY)
  } catch { /* localStorage 不可用时维持本次会话，不伪造恢复成功 */ }
}

// 顶层编排:AppRail(字标/书切换/横切视图tab/主题)+ (作品库 | 混合 Binder 项目树)。
// F-06:5 平行 Rail 视图 → 左侧统一项目树(BinderLayout)+ 横切走顶栏 tab。
export default function App() {
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)   // 当前作品 {slug,title};null=作品库
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')
  const [cmdOpen, setCmdOpen] = useState(false)
  // 单一真相源:选中节点 / 横切视图。{mode:'node', node} | {mode:'view', viewKey}
  const [sel, setSel] = useState({ mode: 'node', node: null })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('s3-theme', theme)
  }, [theme])

  // 设置中心「个人偏好」切主题走 localStorage 直写(非 setTheme),不经这个 state——
  // 监听 s3-pref-changed 把外部写入同步回 state,主题才能热切(否则要刷新才生效)。
  useEffect(() => {
    const h = (e) => { if (e.detail?.key === 's3-theme') setTheme(localStorage.getItem('s3-theme') || 'light') }
    window.addEventListener('s3-pref-changed', h)
    return () => window.removeEventListener('s3-pref-changed', h)
  }, [])

  // 全局键盘层(App 层 window keydown,仓内既有惯例落点;Task 10 Step 4 + 双审收尾):
  //   · ⌘K   作品内 → 与顶栏搜索派发同一 s3-open-capability{search, focus:true},统一触发
  //          左侧搜索工作区并聚焦其唯一搜索框(不另开第二个搜索面,不复制结果 store);
  //          作品库 → 命令面板(此时无 cur,面板只出「作品/作品库」组,不出「视图」组)。
  //   · ⇧⌘K 命令面板 —— 复活"键盘跳视图/切书"power-path。作品内(cur 存在)时命令面板的
  //          「视图」组(CommandPalette 里 {cur && …})才可达,补上被 ⌘K 让位后失去的键盘入口。
  useEffect(() => {
    const h = (e) => {
      if (!((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) return
      e.preventDefault()
      if (e.shiftKey) { setCmdOpen(true); return }
      if (cur) {
        try { window.dispatchEvent(new CustomEvent('s3-open-capability', { detail: { capability: 'search', focus: true } })) } catch { /* 非浏览器环境静默 */ }
      } else {
        setCmdOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [cur])

  useEffect(() => { if (cur) api.setWork(cur.slug) }, [cur])

  const reload = async () => {
    const nextWorks = await api.works()
    setWorks(nextWorks)
    setCur((current) => {
      if (current) return nextWorks.find((work) => work.slug === current.slug) || null
      const savedSlug = readActiveWorkSlug()
      const restored = nextWorks.find((work) => work.slug === savedSlug) || null
      if (!restored && savedSlug) writeActiveWorkSlug('')
      return restored
    })
    return nextWorks
  }
  useEffect(() => { reload() }, [])

  const open = (w) => { api.setWork(w.slug); writeActiveWorkSlug(w.slug); setCur(w); setSel({ mode: 'node', node: null }) }
  const openLibrary = () => { writeActiveWorkSlug(''); setCur(null) }

  // 顶栏横切 tab:切到对应横切视图(中间栏换成图谱/时间线/仪表盘…)
  const onView = (viewKey) => setSel({ mode: 'view', viewKey })

  // 时间线点事件卡跳章:中间栏切回写作台对应章
  const handleJumpChapter = (ch) => setSel({ mode: 'node', node: { id: `ch:${ch}`, type: 'chapter', ref: ch, label: `${ch}` } })

  // 当前高亮的顶栏 tab(横切态才高亮;节点态不亮)
  const activeView = sel.mode === 'view' ? sel.viewKey : null
  // 阶段3:flag 下沉到 BinderLayout 内部(四区壳/三栏壳共享同一套 state/Provider),App 层不再分流
  let body
  if (!cur) {
    body = <Library works={works} reload={reload} onSelect={open} />
  } else {
    body = <BinderLayout key={cur.slug} work={cur.slug} sel={sel} onSel={setSel} onJumpChapter={handleJumpChapter} />
  }

  return (
    <>
      <div className="h-full flex flex-col bg-canvas">
        <AppRail current={cur} view={activeView} onView={onView} onOpenLibrary={openLibrary}
          theme={theme} onTheme={setTheme} />
        <div className="flex-1 min-h-0">{body}</div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} works={works} cur={cur}
          onView={onView} onSelectWork={open} onLibrary={() => setCur(null)} />
      </div>
      <ToastHost />
    </>
  )
}
