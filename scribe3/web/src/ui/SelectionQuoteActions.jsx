import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { MessagesSquare, Sparkles } from 'lucide-react'
import { openChiefForSelection } from '../lib/selAction.js'

/**
 * 只读/任意文本区域：划选非空文本后浮出「聊这段 / 改这段」（与草稿气泡同语义）。
 * 不改动原内容，仅把话术送到主编。
 */
export function SelectionQuoteActions({
  children,
  scopeLabel = '选中内容',
  className = '',
  minChars = 2,
  disabled = false,
  'data-testid': testId = 'selection-quote-host',
}) {
  const hostRef = useRef(null)
  const [bar, setBar] = useState(null) // { left, top, text }

  useEffect(() => {
    if (disabled) return undefined
    const clear = () => setBar(null)
    const onMouseUp = () => {
      // 延迟一帧，等 selection 稳定
      requestAnimationFrame(() => {
        const sel = window.getSelection?.()
        if (!sel || sel.isCollapsed || sel.rangeCount < 1) { clear(); return }
        const host = hostRef.current
        if (!host) { clear(); return }
        const anchor = sel.anchorNode
        if (!anchor || !host.contains(anchor)) { clear(); return }
        const text = String(sel.toString() || '').trim()
        if (text.length < minChars) { clear(); return }
        let rect
        try { rect = sel.getRangeAt(0).getBoundingClientRect() } catch { rect = null }
        // jsdom 常给零尺寸 rect；回退宿主位置，仍允许出现工具条
        if (!rect || (rect.width === 0 && rect.height === 0)) {
          rect = host.getBoundingClientRect?.() || { left: 8, top: 40, width: 140, height: 20 }
        }
        setBar({
          left: Math.min(window.innerWidth - 160, Math.max(8, rect.left + (rect.width || 0) / 2 - 70)),
          top: Math.max(8, (rect.top || 40) - 40),
          text,
        })
      })
    }
    const onScroll = () => clear()
    const onKey = (e) => { if (e.key === 'Escape') clear() }
    document.addEventListener('mouseup', onMouseUp)
    document.addEventListener('scroll', onScroll, true)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mouseup', onMouseUp)
      document.removeEventListener('scroll', onScroll, true)
      document.removeEventListener('keydown', onKey)
    }
  }, [disabled, minChars])

  const run = (intent) => {
    if (!bar?.text) return
    openChiefForSelection({ intent, text: bar.text, scopeLabel })
    setBar(null)
    try { window.getSelection?.()?.removeAllRanges() } catch { /* */ }
  }

  return (
    <div ref={hostRef} className={className} data-testid={testId}>
      {children}
      {bar && createPortal(
        <div
          role="toolbar"
          aria-label="选区快捷动作"
          data-testid="selection-quote-bar"
          className="fixed z-[80] flex items-center gap-0.5 rounded-lg border border-line bg-surface p-1 shadow-lg"
          style={{ left: bar.left, top: bar.top }}
          onMouseDown={(e) => e.preventDefault()}
        >
          <button
            type="button"
            className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-f12 text-brand hover:bg-soft cursor-pointer"
            title="就这段和主编讨论(不改稿)"
            onClick={() => run('discuss')}
          >
            <MessagesSquare size={13} />聊这段
          </button>
          <button
            type="button"
            className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-f12 text-brand hover:bg-soft cursor-pointer"
            title="让主编改这段"
            onClick={() => run('edit')}
          >
            <Sparkles size={13} />改这段
          </button>
        </div>,
        document.body,
      )}
    </div>
  )
}
