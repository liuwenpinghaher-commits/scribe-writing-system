import { useEffect, useState } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { Library } from './Library'
import { WriteLayout } from './WriteLayout'
import { CodexView } from './views/CodexView'
import { AtlasView } from './views/AtlasView'
import { InsightView } from './views/InsightView'

// 顶层编排:AppRail(字标/书切换/视图tab/主题)+ (作品库 | 写作台/设定库/图谱/仪表盘)。
export default function App() {
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)   // 当前作品 {slug,title};null=作品库
  const [view, setView] = useState('write')
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('s3-theme', theme)
  }, [theme])

  useEffect(() => { if (cur) api.setWork(cur.slug) }, [cur])

  const reload = async () => setWorks(await api.works())
  useEffect(() => { reload() }, [])

  const open = (w) => { api.setWork(w.slug); setCur(w); setView('write') }

  let body
  if (!cur) body = <Library works={works} reload={reload} onSelect={open} />
  else if (view === 'codex') body = <CodexView key={cur.slug} />
  else if (view === 'atlas') body = <AtlasView key={cur.slug} />
  else if (view === 'insight') body = <InsightView key={cur.slug} />
  else body = <WriteLayout key={cur.slug} work={cur.slug} />

  return (
    <div className="h-full flex flex-col bg-canvas">
      <AppRail current={cur} view={view} onView={setView} onOpenLibrary={() => setCur(null)} theme={theme} onTheme={setTheme} />
      <div className="flex-1 min-h-0">{body}</div>
    </div>
  )
}
