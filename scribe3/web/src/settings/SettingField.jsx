import { useState } from 'react'
import { api } from '../api'
import { ConfirmDialog } from '../ui/Dialog.jsx'
import { Input } from '../ui.jsx'
import { showToast } from '../ui/Toast.jsx'

const SOURCE_LABEL = { db: '已自定义', env: 'env', default: '默认' }

export function SettingField({ item, onChanged }) {
  const [draft, setDraft] = useState(null)          // null = 未编辑
  const [confirm, setConfirm] = useState(null)      // {value} 或 {reset:true}
  const [err, setErr] = useState(null)
  const commit = async (value) => {
    try {
      await api.putSetting(item.key, value)
      setDraft(null)
      setErr(null)
      showToast(`已保存「${item.label}」`, { tone: 'ok' })
      onChanged?.(item.key)
    } catch (e) {
      const msg = e?.body?.detail || e.message || '保存失败'
      setErr(msg)
      showToast(msg, { tone: 'danger' })
    }
  }
  const submit = (value) => item.danger ? setConfirm({ value }) : commit(value)
  // secret 项 default 为 None(未设置)时,提示不能显示字面 "null"。
  const secretUnset = item.type === 'secret' && (item.default === null || item.default === undefined)
  const defaultText = secretUnset ? '未设置' : String(item.default)
  return (
    <div className="flex items-start gap-3 border-b border-line py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-f13 text-ink">{item.label}</span>
          <span className="text-meta text-muted rounded bg-soft px-1.5">{SOURCE_LABEL[item.source] || item.source}</span>
          {item.pending_restart && <span className="text-meta rounded bg-warn/15 text-warn px-1.5">重启后生效</span>}
          {item.effect === 'restart' && !item.pending_restart && <span className="text-meta text-faint">重启生效项</span>}
        </div>
        {item.desc && <div className="text-meta text-muted mt-0.5">{item.desc}</div>}
        {err && <div className="text-meta text-danger mt-0.5" role="alert">{String(err)}</div>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {item.type === 'bool' ? (
          <button role="switch" aria-checked={item.value} aria-label={item.label}
            onClick={() => submit(!item.value)}
            className={`h-5 w-9 rounded-full transition-colors cursor-pointer ${item.value ? 'bg-brand' : 'bg-line'}`}>
            <span className={`block h-4 w-4 rounded-full bg-surface transition-transform ${item.value ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </button>
        ) : item.type === 'secret' ? (
          <Input type="password" variant="bordered" size="sm" placeholder={item.is_set ? '已设置(输入以更换)' : '未设置'} aria-label={item.label}
            autoComplete="off" className="w-48" value={draft ?? ''} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => draft && submit(draft)} />
        ) : (
          <Input type={item.type === 'str' ? 'text' : 'number'} variant="bordered" size="sm"
            step={item.type === 'float' ? '0.1' : '1'} aria-label={item.label}
            min={item.min ?? undefined} max={item.max ?? undefined}
            className="w-48 tnum" value={draft ?? String(item.value ?? '')}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              if (draft === null || draft === String(item.value)) return
              if (item.type === 'str') { submit(draft); return }
              // P2:数字本地校验,NaN 不出网(空串/非数字直接拒并提示)
              const n = item.type === 'int' ? parseInt(draft, 10) : parseFloat(draft)
              if (!Number.isFinite(n)) { setErr('请输入有效数字'); return }
              setErr(null)
              submit(n)
            }} />
        )}
        {item.source === 'db' && (
          <button onClick={() => setConfirm({ reset: true })} aria-label={`恢复默认:${item.label}`}
            title={secretUnset ? '恢复为未设置' : `恢复默认(${defaultText})`}
            className="text-meta text-faint hover:text-ink cursor-pointer">恢复默认</button>
        )}
      </div>
      <ConfirmDialog open={!!confirm}
        title={confirm?.reset ? `恢复默认「${item.label}」?` : `修改「${item.label}」?`}
        body={confirm?.reset ? (secretUnset ? '恢复为未设置' : `将回落为默认值 ${defaultText}`) : `该项为高危设置,确认改为 ${String(confirm?.value)}`}
        danger confirmText="确认"
        onConfirm={() => {
          const c = confirm; setConfirm(null)
          // P2:恢复默认失败不静默,与 commit 同款错误反馈
          c.reset
            ? api.resetSetting(item.key).then(() => {
                showToast(`已恢复「${item.label}」默认`, { tone: 'ok' })
                onChanged?.(item.key)
              }).catch((e) => {
                const msg = e?.body?.detail || e.message || '恢复失败'
                setErr(msg)
                showToast(msg, { tone: 'danger' })
              })
            : commit(c.value)
        }}
        onClose={() => setConfirm(null)} />
    </div>
  )
}
