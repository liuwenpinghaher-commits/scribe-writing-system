import { useState } from 'react'
import { Btn, Input } from './ui'
import { getApiToken, setApiToken, clearApiToken, probeAuth } from './api'

/**
 * 登录页：收集 SCRIBE3_API_TOKEN 并写入 localStorage。
 * 空 token + 后端未设 token → 本地放行；有 token 时探针 /works。
 */
export function Login({ onSuccess }) {
  const [token, setToken] = useState(() => getApiToken())
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    setBusy(true)
    const t = token.trim()
    try {
      setApiToken(t)
      const ok = await probeAuth()
      if (!ok) {
        clearApiToken()
        setErr('令牌无效或已过期')
        return
      }
      onSuccess?.()
    } catch (ex) {
      clearApiToken()
      setErr(ex?.message || '网络错误，请检查后端是否可达')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h-full grid place-items-center bg-canvas p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-[var(--radius-pane)] bg-surface [box-shadow:var(--shadow-panel)] p-6 space-y-4"
      >
        <div>
          <h1 className="type-page text-ink">Scribe3</h1>
          <p className="type-helper text-faint mt-1.5 leading-relaxed">
            输入 API Token 进入写作台。本地未配置{' '}
            <code className="text-meta">SCRIBE3_API_TOKEN</code>
            {' '}时可留空直接进入。
          </p>
        </div>
        <Input
          type="password"
          variant="bordered"
          size="md"
          autoFocus
          autoComplete="current-password"
          placeholder="API Token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          disabled={busy}
        />
        {err ? <div className="type-helper text-danger" role="alert">{err}</div> : null}
        <Btn type="submit" variant="primary" size="md" className="w-full" disabled={busy}>
          {busy ? '验证中…' : '进入'}
        </Btn>
      </form>
    </div>
  )
}
