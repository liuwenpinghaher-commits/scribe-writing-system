import { useEffect, useState } from 'react'
import { api } from '../api'
import { SettingField } from './SettingField'
import { ConfirmDialog } from '../ui/Dialog.jsx'

const RESTART_PROFILES = ['scribe3', 'scribe3_write']

function StatusCard({ onChanged, refreshKey }) {
  const [gateways, setGateways] = useState(null)
  const [error, setError] = useState(null)

  const load = () => api.gatewayStatus().then((r) => { setGateways(r.gateways); setError(null) }).catch((e) => setError(e))
  useEffect(() => { load() }, [refreshKey])

  return (
    <div className="rounded-lg border border-line bg-surface p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-f13 font-medium text-ink">网关状态</div>
        <button className="text-meta text-brand cursor-pointer" onClick={load}>刷新</button>
      </div>
      {error && (
        <div className="text-f13 text-red-500" role="alert">
          网关状态加载失败 <button className="text-brand cursor-pointer" onClick={load}>重试</button>
        </div>
      )}
      {!error && !gateways && <div className="text-f13 text-faint">加载中…</div>}
      {!error && gateways && (
        <div className="space-y-2">
          {gateways.map((g) => (
            <div key={g.name} className="flex items-center gap-2 text-f13">
              <span className={`inline-block h-2 w-2 rounded-full ${g.online ? 'bg-green-500' : 'bg-line'}`} />
              <span className="text-ink">{g.profile}</span>
              <span className="text-meta text-muted">{g.api}</span>
              <span className={`text-meta ml-auto ${g.online ? 'text-green-600' : 'text-faint'}`}>{g.online ? '在线' : '离线'}</span>
            </div>
          ))}
        </div>
      )}
      <div className="text-meta text-faint mt-3">在线=端口有 HTTP 响应,不代表鉴权/服务正常。</div>
    </div>
  )
}

function FileEditor({ file, onSaved, onReload }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(file.content ?? '')
  const [confirm, setConfirm] = useState(false)
  const [reloadConfirm, setReloadConfirm] = useState(false)
  const [conflict, setConflict] = useState(false)
  const [savedMsg, setSavedMsg] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => { setDraft(file.content ?? '') }, [file.content, file.sha256])

  const broken = !!file.error // 后端读取失败:禁编辑禁保存,防拿空 sha256 撞写接口

  const save = async () => {
    try {
      const r = await api.putGatewayFile(file.id, draft, file.sha256)
      setSavedMsg('已保存')
      setErr(null)
      setConflict(false)
      onSaved?.(file.id, r.sha256, draft)
    } catch (e) {
      if (e.status === 409) {
        setConflict(true)
        setErr(e?.body?.detail || '文件已被外部修改,请重新加载后再编辑')
      } else {
        setErr(e?.body?.detail || e.message || '保存失败')
      }
    }
  }

  const doReload = async () => {
    const fresh = await onReload?.()
    // 重拉后即使服务器内容与本地 props 相同(useEffect 不触发),也显式回填草稿
    const nf = fresh?.find((x) => x.id === file.id)
    setDraft((nf ?? file).content ?? '')
    setConflict(false)
    setErr(null)
    setSavedMsg(null)
  }

  // 丢稿防护:草稿有未保存改动时,重拉必须先确认,不能静默覆盖
  const requestReload = () => {
    if (draft !== (file.content ?? '')) setReloadConfirm(true)
    else doReload()
  }

  const looksMasked = file.id.endsWith('.env') || file.id.endsWith('config.yaml')

  return (
    <div className="rounded-lg border border-line bg-surface mb-2 overflow-hidden">
      <button className="w-full text-left px-4 py-2.5 text-f13 text-ink hover:bg-soft cursor-pointer flex items-center justify-between"
        onClick={() => setOpen((o) => !o)}>
        <span>{file.id}</span>
        <span className={`text-meta ${broken ? 'text-red-500' : 'text-faint'}`}>
          {broken ? '读取失败' : (file.exists ? '' : '不存在')}
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4">
          {file.error && <div className="text-f13 text-red-500 mb-2" role="alert">{file.error}</div>}
          {looksMasked && !broken && (
            <div className="text-meta text-faint mb-1.5">••••为掩码密钥,保留原样保存则密钥不变</div>
          )}
          <textarea rows={16} disabled={broken}
            className="w-full rounded-md border border-line bg-soft px-2 py-1.5 text-f12 font-mono disabled:opacity-50"
            value={draft} onChange={(e) => setDraft(e.target.value)} />
          <div className="mt-2 flex items-center gap-2">
            {!broken && (
              <button className="rounded-md bg-brand text-white px-3 py-1.5 text-f13 cursor-pointer"
                onClick={() => setConfirm(true)}>保存</button>
            )}
            {conflict && (
              <button className="rounded-md border border-line px-3 py-1.5 text-f13 text-ink cursor-pointer" onClick={requestReload}>获取最新内容</button>
            )}
            {savedMsg && !err && <span className="text-meta text-green-600">{savedMsg}</span>}
          </div>
          {err && <div className="text-f13 text-red-500 mt-1.5" role="alert">{err}</div>}
        </div>
      )}
      <ConfirmDialog open={confirm}
        title={`保存「${file.id}」?`}
        body="保存前会自动备份原文件。"
        confirmText="确认"
        onConfirm={() => { setConfirm(false); save() }}
        onClose={() => setConfirm(false)} />
      <ConfirmDialog open={reloadConfirm}
        title={`获取「${file.id}」最新内容?`}
        body="这将丢弃你未保存的修改(如需保留,请先手动复制当前编辑内容)。"
        danger confirmText="确认"
        onConfirm={() => { setReloadConfirm(false); doReload() }}
        onClose={() => setReloadConfirm(false)} />
    </div>
  )
}

function FilesArea() {
  const [files, setFiles] = useState(null)
  const [error, setError] = useState(null)

  const load = () => api.gatewayFiles()
    .then((r) => { setFiles(r.files); setError(null); return r.files })
    .catch((e) => { setError(e); return null })
  useEffect(() => { load() }, [])

  const onSaved = (id, sha256, content) => {
    setFiles((fs) => fs.map((f) => (f.id === id ? { ...f, sha256, content } : f)))
  }

  return (
    <div className="mb-4">
      <div className="text-f13 font-medium text-ink mb-3">网关文件</div>
      {error && (
        <div className="text-f13 text-red-500" role="alert">
          文件列表加载失败 <button className="text-brand cursor-pointer" onClick={load}>重试</button>
        </div>
      )}
      {!error && !files && <div className="text-f13 text-faint">加载中…</div>}
      {!error && files && files.map((f) => (
        <FileEditor key={f.id} file={f} onSaved={onSaved} onReload={load} />
      ))}
    </div>
  )
}

function RestartArea({ onRestarted }) {
  const [restarting, setRestarting] = useState(null) // profile 正在重启
  const [restartConfirm, setRestartConfirm] = useState(null) // profile 待确认
  const [result, setResult] = useState(null) // {profile, online, message}

  const doRestart = async (profile) => {
    setRestarting(profile)
    setResult(null)
    try {
      const r = await api.gatewayRestart(profile)
      setResult({ profile, online: r.online, message: r.message, log: r.log })
    } catch (e) {
      setResult({ profile, online: false, message: e?.body?.detail || e.message || '重启失败' })
    } finally {
      setRestarting(null)
      onRestarted?.()
    }
  }

  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="text-f13 font-medium text-ink mb-3">网关重启</div>
      <div className="flex flex-wrap gap-2">
        {RESTART_PROFILES.map((p) => (
          <button key={p} disabled={restarting === p}
            className="rounded-md border border-line px-3 py-1.5 text-f13 text-ink hover:bg-soft cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={() => setRestartConfirm(p)}>
            {restarting === p ? '重启中…' : `重启 ${p}`}
          </button>
        ))}
      </div>
      {result && (
        <div className={`text-f13 mt-2 ${result.online ? 'text-green-600' : 'text-red-500'}`} role="alert">
          [{result.profile}] {result.message}{result.log ? `(日志: ${result.log})` : ''}
        </div>
      )}
      <ConfirmDialog open={!!restartConfirm}
        title={`重启网关「${restartConfirm}」?`}
        body="将重新拉起该 Hermes 网关进程,约需 5-30s 探活确认,期间该网关不可用。"
        danger confirmText="确认"
        onConfirm={() => { const p = restartConfirm; setRestartConfirm(null); doRestart(p) }}
        onClose={() => setRestartConfirm(null)} />
    </div>
  )
}

export function GatewaySection({ items, onChanged }) {
  const [statusKey, setStatusKey] = useState(0)
  return (
    <div data-testid="gateway-section">
      {items?.length > 0 && (
        <div className="mb-4">
          {items.map((it) => <SettingField key={it.key} item={it} onChanged={onChanged} />)}
        </div>
      )}
      <StatusCard refreshKey={statusKey} />
      <FilesArea />
      <RestartArea onRestarted={() => setStatusKey((k) => k + 1)} />
    </div>
  )
}
