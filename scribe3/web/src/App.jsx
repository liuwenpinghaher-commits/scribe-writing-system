import { lazy, Suspense, useEffect, useState, useCallback } from 'react'
import { api } from './api'
import { AppRail } from './AppRail'
import { CommandPalette } from './CommandPalette'
import { ToastHost } from './ui/Toast'
import { Login } from './Login'
import { clearApiToken } from './authFetch'
import { WorkflowCapsule, applyWorkflowContinue } from './WorkflowCapsule'

const ACTIVE_WORK_STORAGE_KEY = 's3-active-work'
const Library = lazy(() => import('./Library').then((mod) => ({ default: mod.Library })))
const BinderLayout = lazy(() => import('./BinderLayout').then((mod) => ({ default: mod.BinderLayout })))
const AdminConsole = lazy(() => import('./admin/AdminConsole').then((mod) => ({ default: mod.AdminConsole })))

function readActiveWorkSlug() {
  try { return localStorage.getItem(ACTIVE_WORK_STORAGE_KEY) || '' } catch { return '' }
}

function writeActiveWorkSlug(slug) {
  try {
    if (slug) localStorage.setItem(ACTIVE_WORK_STORAGE_KEY, slug)
    else localStorage.removeItem(ACTIVE_WORK_STORAGE_KEY)
  } catch { /* */ }
}

// L1 鉴权门: Cookie 会话（/auth/me）；401 → 登录页（用户名密码，非 API token 粘贴）。
export default function App() {
  const [auth, setAuth] = useState('checking') // checking | ok | need_login
  const [me, setMe] = useState(null) // { username, role, is_admin }
  const [works, setWorks] = useState([])
  const [cur, setCur] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('s3-theme') || 'light')
  const [cmdOpen, setCmdOpen] = useState(false)
  const [sel, setSel] = useState({ mode: 'node', node: null })

  const forceLogin = useCallback(() => {
    clearApiToken()
    setAuth('need_login')
    setMe(null)
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
        // L1: credentials via authFetch; 401 → username/password login page
        try {
          const profile = await api.authMe()
          if (!cancelled) setMe(profile)
        } catch { /* me optional if auth off */ }
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

  // Hooks 必须在所有条件 return 之前（React #310：登录前后 hooks 数量/顺序不能变）
  const handleJumpChapter = useCallback((ch) => {
    setSel({ mode: 'node', node: { id: `ch:${ch}`, type: 'chapter', ref: ch, label: `${ch}` } })
  }, [])
  const handleWorkflowContinue = useCallback((snap) => {
    applyWorkflowContinue(snap, { onSel: setSel, onJumpChapter: handleJumpChapter })
  }, [handleJumpChapter])
  const onView = useCallback((viewKey) => setSel({ mode: 'view', viewKey }), [])

  const exitAdmin = useCallback(() => {
    // 清掉 view=admin，回到作品库或当前书写作区
    setSel({ mode: 'node', node: null })
  }, [])

  const handleView = useCallback((viewKey) => {
    // 盾牌：已在管理台再点一次 = 退出
    if (viewKey === 'admin' && sel.mode === 'view' && sel.viewKey === 'admin') {
      exitAdmin()
      return
    }
    onView(viewKey)
  }, [sel, onView, exitAdmin])

  // 编排 ui_directive 的 selection：主编/WriteChat 无 setSel 直连时经 s3-selection 落地栏3
  useEffect(() => {
    const onSelEvt = (e) => {
      const d = e?.detail
      if (!d || typeof d !== 'object') return
      if (d.mode === 'view' && d.viewKey) {
        setSel({ mode: 'view', viewKey: d.viewKey })
        return
      }
      if (d.mode === 'node' || d.node) {
        const node = d.node || null
        if (node) setSel({ mode: 'node', node })
      }
    }
    window.addEventListener('s3-selection', onSelEvt)
    return () => window.removeEventListener('s3-selection', onSelEvt)
  }, [])

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

  const onLoginSuccess = async (loginBody) => {
    setAuth('checking')
    try {
      if (loginBody?.is_admin != null) {
        setMe({
          username: loginBody.username,
          role: loginBody.role,
          is_admin: loginBody.is_admin,
          display_name: loginBody.display_name,
        })
      } else {
        try { setMe(await api.authMe()) } catch { /* */ }
      }
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

  // —— 以下为非 hook 逻辑；条件 return 之后禁止再调用 use* ——
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

  const open = (w) => {
    api.setWork(w.slug)
    writeActiveWorkSlug(w.slug)
    setCur(w)
    setSel({ mode: 'node', node: null })
  }
  const openLibrary = () => {
    writeActiveWorkSlug('')
    setCur(null)
    // 从管理台点「作品」必须退出 admin，否则仍被 activeView===admin 占住整页
    setSel({ mode: 'node', node: null })
  }
  const activeView = sel.mode === 'view' ? sel.viewKey : null
  const isAdmin = !!(me?.is_admin)

  let body
  if (activeView === 'admin' && isAdmin) {
    body = <AdminConsole onExit={exitAdmin} hasWork={!!cur} />
  } else if (!cur) {
    body = <Library works={works} reload={reload} onSelect={open} />
  } else {
    body = (
      <BinderLayout
        key={cur.slug}
        work={cur.slug}
        sel={sel}
        onSel={setSel}
        onJumpChapter={handleJumpChapter}
        onWorkflowContinue={handleWorkflowContinue}
      />
    )
  }

  return (
    <>
      <div className="h-full flex flex-col bg-canvas">
        <AppRail
          current={cur}
          view={activeView}
          onView={handleView}
          onOpenLibrary={openLibrary}
          theme={theme}
          onTheme={setTheme}
          isAdmin={isAdmin}
          capsule={cur && activeView !== 'admin' ? (
            <WorkflowCapsule
              work={cur.slug}
              onOpenJourney={() => onView('journey')}
              onContinue={handleWorkflowContinue}
            />
          ) : null}
        />
        <div className="flex-1 min-h-0">
          <Suspense fallback={<div className="h-full grid place-items-center text-f13 text-faint/60">加载工作区…</div>}>
            {body}
          </Suspense>
        </div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} works={works} cur={cur}
          onView={handleView} onSelectWork={open} onLibrary={openLibrary} />
      </div>
      <ToastHost />
    </>
  )
}
