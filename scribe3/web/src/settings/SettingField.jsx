import { useState } from 'react'
import { api } from '../api'
import { ConfirmDialog } from '../ui/Dialog.jsx'

const SOURCE_LABEL = { db: '已自定义', env: 'env', default: '默认' }

export function SettingField({ item, onChanged }) {
  const [draft, setDraft] = useState(null)          // null = 未编辑
  const [confirm, setConfirm] = useState(null)      // {value} 或 {reset:true}
  const [err, setErr] = useState(null)
  const commit = async (value) => {
    try { await api.putSetting(item.key, value); setDraft(null); setErr(null); onChanged?.() }
    catch (e) { setErr(e?.body?.detail || e.message || '保存失败') }
  }
  const submit = (value) => item.danger ? setConfirm({ value }) : commit(value)
  return (
    <div className="flex items-start gap-3 border-b border-line py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-f13 text-ink">{item.label}</span>
          <span className="text-meta text-muted rounded bg-soft px-1.5">{SOURCE_LABEL[item.source] || item.source}</span>
          {item.pending_restart && <span className="text-meta rounded bg-amber-500/15 text-amber-600 px-1.5">重启后生效</span>}
          {item.effect === 'restart' && !item.pending_restart && <span className="text-meta text-faint">重启生效项</span>}
        </div>
        {item.desc && <div className="text-meta text-muted mt-0.5">{item.desc}</div>}
        {err && <div className="text-meta text-red-500 mt-0.5" role="alert">{String(err)}</div>}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {item.type === 'bool' ? (
          <button role="switch" aria-checked={item.value} aria-label={item.label}
            onClick={() => submit(!item.value)}
            className={`h-5 w-9 rounded-full transition-colors cursor-pointer ${item.value ? 'bg-brand' : 'bg-line'}`}>
            <span className={`block h-4 w-4 rounded-full bg-surface transition-transform ${item.value ? 'translate-x-4' : 'translate-x-0.5'}`} />
          </button>
        ) : item.type === 'secret' ? (
          <input type="password" placeholder={item.is_set ? '已设置(输入以更换)' : '未设置'} aria-label={item.label}
            className="w-48 rounded-md border border-line bg-surface px-2 py-1 text-f13"
            value={draft ?? ''} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => draft && submit(draft)} />
        ) : (
          <input type={item.type === 'str' ? 'text' : 'number'} step={item.type === 'float' ? '0.1' : '1'} aria-label={item.label}
            min={item.min ?? undefined} max={item.max ?? undefined}
            className="w-48 rounded-md border border-line bg-surface px-2 py-1 text-f13 tnum"
            value={draft ?? String(item.value ?? '')} onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              if (draft === null || draft === String(item.value)) return
              submit(item.type === 'int' ? parseInt(draft, 10) : item.type === 'float' ? parseFloat(draft) : draft)
            }} />
        )}
        {item.source === 'db' && (
          <button onClick={() => setConfirm({ reset: true })} aria-label={`恢复默认:${item.label}`}
            title={`恢复默认(${String(item.default)})`}
            className="text-meta text-faint hover:text-ink cursor-pointer">恢复默认</button>
        )}
      </div>
      <ConfirmDialog open={!!confirm}
        title={confirm?.reset ? `恢复默认「${item.label}」?` : `修改「${item.label}」?`}
        body={confirm?.reset ? `将回落为默认值 ${String(item.default)}` : `该项为高危设置,确认改为 ${String(confirm?.value)}`}
        danger confirmText="确认"
        onConfirm={() => { const c = confirm; setConfirm(null); c.reset ? api.resetSetting(item.key).then(onChanged) : commit(c.value) }}
        onClose={() => setConfirm(null)} />
    </div>
  )
}
