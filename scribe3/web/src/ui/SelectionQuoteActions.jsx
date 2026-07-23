import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { BookmarkPlus, MessagesSquare, Quote } from 'lucide-react'
import { openChiefForSelection } from '../lib/selAction.js'
import { saveSessionClipAsMaterial, seedCiteSelection } from '../lib/sessionClip.js'
import { showToast } from './Toast.jsx'

/**
 * 划选非空文本后浮窗：存 / 引入会话 / 聊
 * - 存：作者直写素材库（POST /materials），不经主编审批
 * - 引入会话：选区带标记写入主编 compose
 * - 聊：就这段与主编讨论
 */
export function SelectionQuoteActions({
  children,
  scopeLabel = '选中内容',
  className = '',
  minChars = 2,
  disabled = false,
  chapterSeq = null,
  originLabel = '选区摘录',
  'data-testid': testId = 'selection-quote-host',
}) {
  const hostRef = useRef(null)
  const [bar, setBar] = useState(null) // { left, top, text }
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (disabled) return undefined
    const clear = () => setBar(null)
    const onMouseUp = () => {
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
        if (!rect || (rect.width === 0 && rect.height === 0)) {
          rect = host.getBoundingClientRect?.() || { left: 8, top: 40, width: 140, height: 20 }
        }
        setBar({
          left: Math.min(window.innerWidth - 200, Math.max(8, rect.left + (rect.width || 0) / 2 - 90)),
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

  const closeBar = () => {
    setBar(null)
    try { window.getSelection?.()?.removeAllRanges() } catch { /* */ }
  }

  const onDiscuss = () => {
    if (!bar?.text) return
    openChiefForSelection({ intent: 'discuss', text: bar.text, scopeLabel })
    closeBar()
  }

  const onCiteToSession = () => {
    if (!bar?.text) return
    seedCiteSelection({ text: bar.text, scopeLabel })
    showToast('已引入到主编会话', { tone: 'ok' })
    closeBar()
  }

  const onSave = async () => {
    if (!bar?.text || saving) return
    setSaving(true)
    try {
      const saved = await saveSessionClipAsMaterial({
        text: bar.text,
        kind: 'snippet',
        scopeLabel,
        chapterSeq,
        originLabel,
      })
      if (saved?.id) {
        showToast(`已存入素材库「${saved.title}」`, { tone: 'ok' })
        try {
          window.dispatchEvent(new CustomEvent('s3-material-saved', { detail: saved }))
        } catch { /* */ }
      }
      closeBar()
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '存入素材失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
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
            data-testid="selection-save-material"
            disabled={saving}
            className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-f12 text-brand hover:bg-soft cursor-pointer disabled:opacity-50"
            title="立即存入素材库(片段,无需主编审批)"
            onClick={onSave}
          >
            <BookmarkPlus size={13} />{saving ? '保存中…' : '存'}
          </button>
          <button
            type="button"
            data-testid="selection-cite-session"
            className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-f12 text-brand hover:bg-soft cursor-pointer"
            title="把这段引入主编会话输入框"
            onClick={onCiteToSession}
          >
            <Quote size={13} />引入会话
          </button>
          <button
            type="button"
            data-testid="selection-discuss"
            className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-f12 text-brand hover:bg-soft cursor-pointer"
            title="就这段和主编讨论(不改稿)"
            onClick={onDiscuss}
          >
            <MessagesSquare size={13} />聊
          </button>
        </div>,
        document.body,
      )}
    </div>
  )
}
