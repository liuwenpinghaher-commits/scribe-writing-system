import { lazy, Suspense, useEffect, useState, useCallback } from 'react'
import { api, clearApiToken } from './api'
import { AppRail } from './AppRail'
import { CommandPalette } from './CommandPalette'
import { ToastHost } from './ui/Toast'
import { Login } from './Login'

const ACTIVE_WORK_STORAGE_KEY = 's3-active-work'
const Library = lazy(() => import('./Library').then((mod) => ({ default: mod.Library })))
const BinderLayout = lazy(() => import('./BinderLayout').then((mod) => ({ default: mod.BinderLayout })))

function readActiveWorkSlug() {
  try { return localStorage.getItem(ACTIVE_WORK_STORAGE_KEY) || '' } catch { return '' }
}

function writeActiveWorkSlug(slug) {
  try {
    if (slug) localStorage.setItem(ACTIVE_WORK_STORAGE_KEY, slug)
    else localStorage.removeItem(ACTIVE_WORK_STORAGE_KEY)
  } catch { /* localStorage 不可用时维持本次会话，不伪造恢复成功 */ }
}

// 顶层编排:AppRail + (作品库 | Binder)。
// 鉴权门:后端 SCRIBE3_API_TOKEN 非空时，无/错 token → 401 → 登录页；空 token 本地放行。
export default function App() {
  const [auth, setAuth] = useState('checking') // checking | ok | need_login
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')
  const [cmdOpen, setCmdOpen] = useState(false)
  const [sel, setSel] = useState({ mode: 'node', node: null })

  const forceLogin = useCallback(() => {
    clearApiToken()
    setAuth('need_login')
    setWorks([])
    setCur(null)
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('s3-theme', theme)
  }, [theme])

  useEffect(() => {
    const h = (e) => { if (e.detail?.key === 's3-theme') setTheme(localStorage.getItem('s3-theme') || 'light') }
    window.addEventListener('s3-pref-changed', h)
    return () => window.removeEventListener('s3-pref-changed', h)
  }, [])

  useEffect(() => {
    const h = () => forceLogin()
    window.addEventListener('s3-auth-required', h)
    return () => window.removeEventListener('s3-auth-required', h)
  }, [forceLogin])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const nextWorks = await api.works()
        if (cancelled) return
        setWorks(nextWorks)
        setCur((current) => {
          if (current) return nextWorks.find((work) => work.slug === current.slug) || null
          const savedSlug = readActiveWorkSlug()
          const restored = nextWorks.find((work) => work.slug === savedSlug) || null
          if (!restored && savedSlug) writeActiveWorkSlug('')
          return restored
        })
        setAuth('ok')
      } catch (e) {
        if (cancelled) return
        if (e?.status === 401) forceLogin()
        else setAuth('ok')
      }
    })()
    return () => { cancelled = true }
  }, [forceLogin])

  useEffect(() => {
    const h = (e) => {
      if (!((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) return
      e.preventDefault()
      if (e.shiftKey) { setCmdOpen(true); return }
      if (cur) {
        try { window.dispatchEvent(new CustomEvent('s3-open-capability', { detail: { capability: 'search', focus: true } })) } catch { /* */ }
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

  const onLoginSuccess = async () => {
    setAuth('checking')
    try {
      const nextWorks = await api.works()
      setWorks(nextWorks)
      setCur((current) => {
        if (current) return nextWorks.find((work) => work.slug === current.slug) || null
        const savedSlug = readActiveWorkSlug()
        const restored = nextWorks.find((work) => work.slug === savedSlug) || null
        if (!restored && savedSlug) writeActiveWorkSlug('')
        return restored
      })
      setAuth('ok')
    } catch (e) {
      if (e?.status === 401) forceLogin()
      else setAuth('ok')
    }
  }

  if (auth === 'checking') {
    return (
      <div className="h-full grid place-items-center bg-canvas text-f13 text-faint/60">
        连接中…
      </div>
    )
  }

  if (auth === 'need_login') {
    return <Login onSuccess={onLoginSuccess} />
  }

  const open = (w) => { api.setWork(w.slug); writeActiveWorkSlug(w.slug); setCur(w); setSel({ mode: 'node', node: null }) }
  const openLibrary = () => { writeActiveWorkSlug(''); setCur(null) }
  const onView = (viewKey) => setSel({ mode: 'view', viewKey })
  const handleJumpChapter = (ch) => setSel({ mode: 'node', node: { id: `ch:${ch}`, type: 'chapter', ref: ch, label: `${ch}` } })
  const activeView = sel.mode === 'view' ? sel.viewKey : null

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
        <div className="flex-1 min-h-0">
          <Suspense fallback={<div className="h-full grid place-items-center text-f13 text-faint/60">加载工作区…</div>}>
            {body}
          </Suspense>
        </div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} works={works} cur={cur}
          onView={onView} onSelectWork={open} onLibrary={() => setCur(null)} />
      </div>
      <ToastHost />
    </>
  )
}
