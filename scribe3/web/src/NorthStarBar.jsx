import { useEffect, useState } from 'react'
import { Compass, ChevronDown, MessageSquare } from 'lucide-react'
import { api } from './api'
import { Btn } from './ui.jsx'
import { ReadOnlyText } from './ui/EditableText.jsx'

const FIELDS = [['reader_feeling', '读者感受'], ['emotional_arc', '情感弧'], ['red_lines', '红线']]

// 顶栏北极星条:作品意图常驻,只读展示。写入走主编对话审批(s3_set_intent),禁止表单直填。
export function NorthStarBar() {
  const [intent, setIntent] = useState({ reader_feeling: '', emotional_arc: '', red_lines: '' })
  const [open, setOpen] = useState(false)

  const reload = () => { api.intent().then(setIntent).catch(() => {}) }
  useEffect(() => { reload() }, [])
  // 审批落库后外部可派发刷新
  useEffect(() => {
    const h = () => reload()
    window.addEventListener('s3:intent-changed', h)
    return () => window.removeEventListener('s3:intent-changed', h)
  }, [])

  const summary = FIELDS.map(([k]) => intent[k]).filter(Boolean).join(' · ') || '未设作品意图(点开 → 让主编写入)'

  const askChiefToWrite = () => {
    const text = [
      '请登记/更新本书北极星意图并写入落库(需我审批):',
      '读者感受:压抑中见微光,雪夜仍有灯',
      '情感弧:由怯到决,灰契为代价',
      '红线:不写超自然明机制;不洗白加害;不丑化底层',
      '必须先 s3_get_intent 核实,再用 s3_set_intent 写入。未获批准不得声称已落库。',
    ].join('\n')
    try { sessionStorage.setItem('s3.chief.seed', text) } catch { /* */ }
    try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: text })) } catch { /* */ }
    setOpen(false)
  }

  return (
    <div className="border-b border-line bg-surface" data-testid="northstar-bar">
      <button type="button" onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-4 h-9 cursor-pointer hover:bg-soft/40 transition-colors border-l-2 border-brand">
        <Compass size={14} className="text-brand shrink-0" />
        <span className="text-f12 text-faint shrink-0">北极星</span>
        <span className="text-f12 text-ink truncate" data-testid="northstar-summary">{summary}</span>
        <ChevronDown size={13} className={`ml-auto shrink-0 text-faint transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 py-3 grid sm:grid-cols-3 gap-2.5 bg-canvas/50" data-testid="northstar-readonly">
          {FIELDS.map(([k, label]) => (
            <div key={k} data-testid={`northstar-field-${k}`}>
              <ReadOnlyText
                label={label}
                value={intent[k] || ''}
                emptyHint="（空 · 由主编审批写入）"
                entityLabel="北极星"
                fieldKey={k}
                emptyAskLabel="聊聊怎么写"
              />
            </div>
          ))}
          <div className="sm:col-span-3 flex flex-wrap items-center justify-between gap-2">
            <span className="text-meta text-faint">禁止表单直填 · 写入走主编工具 s3_set_intent + 审批</span>
            <Btn variant="primary" size="sm" data-testid="northstar-ask-chief" onClick={askChiefToWrite}>
              <MessageSquare size={13} />让主编写入
            </Btn>
          </div>
        </div>
      )}
    </div>
  )
}
