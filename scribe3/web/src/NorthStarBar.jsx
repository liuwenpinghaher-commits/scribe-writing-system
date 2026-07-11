import { useEffect, useState } from 'react'
import { Compass, ChevronDown, Check } from 'lucide-react'
import { api } from './api'
import { useToast } from './ui/Toast.jsx'
import { Btn, Textarea } from './ui.jsx'

const FIELDS = [['reader_feeling', '读者感受'], ['emotional_arc', '情感弧'], ['red_lines', '红线']]

// 顶栏北极星条:作品意图常驻,点开可编辑。喂主编当写作纲领。
export function NorthStarBar() {
  const toast = useToast()
  const [intent, setIntent] = useState({ reader_feeling: '', emotional_arc: '', red_lines: '' })
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState(false)
  useEffect(() => { api.intent().then(setIntent).catch(() => {}) }, [])

  const summary = FIELDS.map(([k]) => intent[k]).filter(Boolean).join(' · ') || '未设作品意图(点此填北极星)'
  const set = (k, v) => { setIntent((i) => ({ ...i, [k]: v })); setSaved(false) }

  return (
    <div className="border-b border-line bg-surface">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center gap-2 px-4 h-9 cursor-pointer hover:bg-soft/40 transition-colors border-l-2 border-brand">
        <Compass size={14} className="text-brand shrink-0" />
        <span className="text-f12 text-faint shrink-0">北极星</span>
        <span className="text-f12 text-ink truncate">{summary}</span>
        <ChevronDown size={13} className={`ml-auto shrink-0 text-faint transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 py-3 grid sm:grid-cols-3 gap-2.5 bg-canvas/50">
          {FIELDS.map(([k, label]) => (
            <div key={k}>
              <label className="block text-meta text-faint mb-1">{label}</label>
              <Textarea value={intent[k] || ''} onChange={(e) => set(k, e.target.value)} rows={2} className="px-2.5 py-1.5" />
            </div>
          ))}
          <div className="sm:col-span-3 flex justify-end">
            <Btn variant="primary" size="sm" onClick={async () => {
              try { await api.putIntent(intent); setSaved(true) }
              catch (e) { toast(e?.body?.detail || '意图保存失败,请重试', { tone: 'danger' }) }  // 失败不置 saved
            }}>
              <Check size={13} />{saved ? '已存' : '保存意图'}
            </Btn>
          </div>
        </div>
      )}
    </div>
  )
}
