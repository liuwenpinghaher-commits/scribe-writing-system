import { useEffect, useState } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { Library } from './Library'
import { WriteLayout } from './WriteLayout'

// 顶层编排:AppRail(字标/书切换/主题)+ (作品库 | 写作台)。借鉴 scribe2 App。
export default function App() {
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)   // 当前作品 {slug,title};null=作品库
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('s3-theme', theme)
  }, [theme])

  const reload = async () => setWorks(await api.works())
  useEffect(() => { reload() }, [])

  return (
    <div className="h-full flex flex-col bg-canvas">
      <AppRail current={cur} onOpenLibrary={() => setCur(null)} theme={theme} onTheme={setTheme} />
      <div className="flex-1 min-h-0">
        {cur
          ? <WriteLayout key={cur.slug} work={cur.slug} />
          : <Library works={works} reload={reload} onSelect={setCur} />}
      </div>
    </div>
  )
}
