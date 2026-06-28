import { useEffect, useState } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { Library } from './Library'
import { WriteLayout } from './WriteLayout'
import { CommandPalette } from './CommandPalette'
import { CodexView } from './views/CodexView'
import { AtlasView } from './views/AtlasView'
import { InsightView } from './views/InsightView'
import { TimelineView } from './views/TimelineView'
import { ToastProvider } from './ui/Toast'

// 顶层编排:AppRail(字标/书切换/视图tab/主题)+ (作品库 | 写作台/设定库/图谱/仪表盘/时间线)。
export default function App() {
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)   // 当前作品 {slug,title};null=作品库
  const [view, setView] = useState('write')
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')
  const [cmdOpen, setCmdOpen] = useState(false)
  // 时间线跳章回调:触发写作台跳到对应章
  const [jumpChapter, setJumpChapter] = useState(null)

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

  const open = (w) => { api.setWork(w.slug); setCur(w); setView('write') }

  // 时间线点击事件卡跳对应章:切到写作台并传章号
  const handleJumpChapter = (ch) => {
    setJumpChapter(ch)
    setView('write')
  }

  let body
  if (!cur) body = <Library works={works} reload={reload} onSelect={open} />
  else if (view === 'codex') body = <CodexView key={cur.slug} />
  else if (view === 'atlas') body = <AtlasView key={cur.slug} />
  else if (view === 'insight') body = <InsightView key={cur.slug} />
  else if (view === 'timeline') body = <TimelineView key={cur.slug} onJumpChapter={handleJumpChapter} />
  else body = <WriteLayout key={cur.slug} work={cur.slug} initChapter={jumpChapter} onChapterOpen={() => setJumpChapter(null)} />

  return (
    <ToastProvider>
      <div className="h-full flex flex-col bg-canvas">
        <AppRail current={cur} view={view} onView={setView} onOpenLibrary={() => setCur(null)} theme={theme} onTheme={setTheme} />
        <div className="flex-1 min-h-0">{body}</div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} works={works} cur={cur}
          onView={setView} onSelectWork={open} onLibrary={() => setCur(null)} />
      </div>
    </ToastProvider>
  )
}
