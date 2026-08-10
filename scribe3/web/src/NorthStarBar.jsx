import { useEffect, useState } from 'react'
import { Compass, ChevronDown, MessageSquare } from 'lucide-react'
import { api } from './api'
import { Btn } from './ui.jsx'
import { ReadOnlyText } from './ui/EditableText.jsx'

const FIELDS = [['reader_feeling', '读者感受'], ['emotional_arc', '情感弧'], ['red_lines', '红线']]

// 顶栏作品意图条(IA KD-IA-3):只读展示 intent:main。写入走主编审批(s3_set_intent)。
// 与辅助面「评分卡」(scorecard)不是同一物——勿混称「北极星」。
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

  const filled = FIELDS.map(([k, label]) => {
    const v = (intent[k] || '').trim()
    return v ? { k, label, v } : null
  }).filter(Boolean)
  const emptyHint = '未设作品意图（点开 → 让主编写入）'

  const askChiefToWrite = () => {
    const text = [
      '请登记/更新本书作品意图并写入落库(需我审批):',
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
    <div
      className="min-w-0 w-full max-w-full border-b border-line bg-surface"
      data-testid="northstar-bar"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full min-w-0 max-w-full flex items-start gap-2 px-3 sm:px-4 py-2 min-h-9 cursor-pointer hover:bg-soft/40 transition-colors border-l-2 border-brand text-left"
        title="作品意图（intent）· 与辅助面「评分卡」不是同一物"
      >
        <Compass size={14} className="text-brand shrink-0 mt-0.5" />
        <span className="text-f12 text-faint shrink-0 whitespace-nowrap mt-0.5">作品意图</span>
        {/* 可换行、占满剩余宽度；禁止 truncate 单行截断 */}
        <span
          className="flex-1 min-w-0 text-f12 text-ink text-left whitespace-normal break-words leading-snug"
          data-testid="northstar-summary"
        >
          {filled.length ? (
            <span className="flex flex-col gap-0.5 sm:block">
              {filled.map(({ k, label, v }, i) => (
                <span key={k} className="inline sm:inline">
                  <span className="text-faint">{label}：</span>
                  <span className="break-words">{v}</span>
                  {i < filled.length - 1 && (
                    <span className="hidden sm:inline text-faint"> · </span>
                  )}
                </span>
              ))}
            </span>
          ) : (
            emptyHint
          )}
        </span>
        <ChevronDown
          size={13}
          className={`shrink-0 mt-0.5 text-faint transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div
          className="px-3 sm:px-4 py-3 grid grid-cols-1 md:grid-cols-3 gap-2.5 bg-canvas/50 min-w-0"
          data-testid="northstar-readonly"
        >
          {FIELDS.map(([k, label]) => (
            <div key={k} className="min-w-0" data-testid={`northstar-field-${k}`}>
              <ReadOnlyText
                label={label}
                value={intent[k] || ''}
                emptyHint="（空 · 由主编审批写入）"
                entityLabel="作品意图"
                fieldKey={k}
                emptyAskLabel="聊聊怎么写"
                className="min-w-0"
              />
            </div>
          ))}
          <div className="md:col-span-3 flex flex-wrap items-center justify-between gap-2 min-w-0">
            <span className="text-meta text-faint min-w-0 break-words">
              禁止表单直填 · 写入走主编 s3_set_intent + 审批 · 这不是「评分卡」
            </span>
            <Btn variant="primary" size="sm" data-testid="northstar-ask-chief" onClick={askChiefToWrite}>
              <MessageSquare size={13} />让主编写入
            </Btn>
          </div>
        </div>
      )}
    </div>
  )
}
