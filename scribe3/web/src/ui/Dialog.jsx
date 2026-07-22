import { useEffect, useRef, useState } from 'react'
import { Btn, Input } from '../ui.jsx'

// 统一遮罩 token(全站弹层/命令面板共用):固定深色 scrim + z-[100]。
export const OVERLAY_CLASS = 'fixed inset-0 z-[100] bg-black/40'

export function Dialog({ open, onClose, children, labelledBy }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    const node = ref.current
    const prev = document.activeElement
    // 打开时把焦点移入弹层(优先第一个可聚焦元素,否则聚焦容器本身)。
    const focusables = () => node?.querySelectorAll(
      'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')
    ;(focusables()?.[0] || node)?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') { onClose?.(); return }
      // focus-trap:Tab / Shift+Tab 在弹层内可聚焦元素间循环,不跑到背景。
      if (e.key !== 'Tab') return
      const els = [...(focusables() || [])]; if (!els.length) return
      const first = els[0], last = els[els.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className={`${OVERLAY_CLASS} grid place-items-center`} onClick={onClose}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby={labelledBy}
           onClick={(e) => e.stopPropagation()}
           className="min-w-[320px] max-w-[440px] w-[90vw] rounded-xl bg-surface border border-line shadow-[var(--shadow-card)] outline-none">
        {children}
      </div>
    </div>
  )
}

export function InputDialog({ open, title, placeholder = '', defaultValue = '', confirmText = '确认', onConfirm, onClose }) {
  const [v, setV] = useState(defaultValue)
  useEffect(() => { if (open) setV(defaultValue) }, [open, defaultValue])
  const submit = () => { onConfirm?.(v); onClose?.() }
  return (
    <Dialog open={open} onClose={onClose} labelledBy="dlg-title">
      <div className="p-4">
        <div id="dlg-title" className="text-f14 font-medium text-ink mb-3">{title}</div>
        <Input variant="bordered" autoFocus value={v} placeholder={placeholder}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }} />
        <div className="mt-4 flex justify-end gap-2">
          <Btn variant="ghost" onClick={onClose}>取消</Btn>
          <Btn variant="primary" onClick={submit}>{confirmText}</Btn>
        </div>
      </div>
    </Dialog>
  )
}

export function ConfirmDialog({ open, title, body, danger, confirmText = '确认', onConfirm, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} labelledBy="cfm-title">
      <div className="p-4">
        <div id="cfm-title" className="text-f14 font-medium text-ink mb-1.5">{title}</div>
        {body && <div className="text-f13 text-faint leading-relaxed mb-4">{body}</div>}
        <div className="mt-2 flex justify-end gap-2">
          <Btn variant="ghost" onClick={onClose}>取消</Btn>
          <Btn variant="primary" className={danger ? '!bg-danger !text-white' : ''} onClick={() => { onConfirm?.(); onClose?.() }}>{confirmText}</Btn>
        </div>
      </div>
    </Dialog>
  )
}
