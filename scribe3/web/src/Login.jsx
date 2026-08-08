import { useState } from 'react'
import { Btn, Input } from './ui'
import { BrandMark } from './BrandMark'
import { PRODUCT_NAME_ZH, PRODUCT_TAGLINE, PRODUCT_TITLE } from './brand'

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

/**
 * L1 登录页：用户名 + 密码 → POST /auth/login（HttpOnly Cookie 会话）。
 * 产品名：铜炉（tonglu）；遗留 SCRIBE3_API_TOKEN 见 docs/L1-AUTH-ISOLATION.md。
 */
export function Login({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    try {
      const res = await fetch(BASE + '/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      })
      if (!res.ok) {
        let detail = '用户名或密码错误'
        try {
          const body = await res.json()
          if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail
        } catch { /* */ }
        setErr(detail)
        return
      }
      let body = null
      try { body = await res.json() } catch { /* */ }
      onSuccess?.(body)
    } catch (ex) {
      setErr(ex?.message || '网络错误，请检查后端是否可达')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h-full grid place-items-center bg-canvas p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-[var(--radius-pane)] bg-surface [box-shadow:var(--shadow-panel)] px-8 py-9 space-y-5"
      >
        <div className="flex flex-col items-center text-center gap-3">
          <BrandMark size={120} glow />
          <div>
            <h1 className="type-page text-ink leading-none tracking-[0.12em]">{PRODUCT_NAME_ZH}</h1>
            <p className="type-meta text-faint mt-1.5 tracking-wide">{PRODUCT_TAGLINE}</p>
          </div>
          <p className="type-helper text-faint leading-relaxed max-w-[18rem]">
            登录 {PRODUCT_TITLE}。会话由服务器 Cookie 维护，不会在浏览器保存共享 API 密钥。
          </p>
        </div>
        <Input
          type="text"
          name="username"
          autoComplete="username"
          variant="bordered"
          size="md"
          autoFocus
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={busy}
        />
        <Input
          type="password"
          name="password"
          autoComplete="current-password"
          variant="bordered"
          size="md"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={busy}
        />
        {err ? <div className="type-helper text-danger text-center" role="alert">{err}</div> : null}
        <Btn type="submit" variant="primary" size="md" className="w-full" disabled={busy || !username.trim() || !password}>
          {busy ? '登录中…' : '登录'}
        </Btn>
      </form>
    </div>
  )
}
