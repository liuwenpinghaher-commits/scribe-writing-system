import { useEffect, useState } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { Library } from './Library'
import { BinderLayout } from './BinderLayout'
import { FourPane } from './layout/FourPane'
import { CommandPalette } from './CommandPalette'
import { ToastHost } from './ui/Toast'

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

  useEffect(() => {
    const h = (e) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setCmdOpen((v) => !v) } }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  useEffect(() => { if (cur) api.setWork(cur.slug) }, [cur])

  const reload = async () => setWorks(await api.works())
  useEffect(() => { reload() }, [])

  const open = (w) => { api.setWork(w.slug); setCur(w); setSel({ mode: 'node', node: null }) }

  // 顶栏横切 tab:切到对应横切视图(中间栏换成图谱/时间线/仪表盘…)
  const onView = (viewKey) => setSel({ mode: 'view', viewKey })

  // 时间线点事件卡跳章:中间栏切回写作台对应章
  const handleJumpChapter = (ch) => setSel({ mode: 'node', node: { id: `ch:${ch}`, type: 'chapter', ref: ch, label: `${ch}` } })

  // 当前高亮的顶栏 tab(横切态才高亮;节点态不亮)
  const activeView = sel.mode === 'view' ? sel.viewKey : null

  // 阶段2:feature flag `s3.layout.v2` 分流新四区骨架 / 旧布局(localStorage 设 '1' 开启,可随时回退)
  const V2 = localStorage.getItem('s3.layout.v2') === '1'
  let body
  if (!cur) {
    body = <Library works={works} reload={reload} onSelect={open} />
  } else if (V2) {
    body = <FourPane key={cur.slug} work={cur.slug} sel={sel} onSel={setSel} />
  } else {
    body = <BinderLayout key={cur.slug} work={cur.slug} sel={sel} onSel={setSel} onJumpChapter={handleJumpChapter} />
  }

  return (
    <>
      <div className="h-full flex flex-col bg-canvas">
        <AppRail current={cur} view={activeView} onView={onView} onOpenLibrary={() => setCur(null)} theme={theme} onTheme={setTheme} />
        <div className="flex-1 min-h-0">{body}</div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} works={works} cur={cur}
          onView={onView} onSelectWork={open} onLibrary={() => setCur(null)} />
      </div>
      <ToastHost />
    </>
  )
}
