import { useEffect, useRef, useState } from 'react'
import { Btn } from '../ui.jsx'

export function Dialog({ open, onClose, children, labelledBy }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    document.addEventListener('keydown', onKey)
    ref.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/50" onClick={onClose}>
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
        <div id="dlg-title" className="text-[14px] font-medium text-ink mb-3">{title}</div>
        <input autoFocus value={v} placeholder={placeholder}
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
          className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-[13px] text-ink outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus:border-brand" />
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
        <div id="cfm-title" className="text-[14px] font-medium text-ink mb-1.5">{title}</div>
        {body && <div className="text-[12.5px] text-faint leading-relaxed mb-4">{body}</div>}
        <div className="mt-2 flex justify-end gap-2">
          <Btn variant="ghost" onClick={onClose}>取消</Btn>
          <Btn variant="primary" className={danger ? '!bg-danger !text-white' : ''} onClick={() => { onConfirm?.(); onClose?.() }}>{confirmText}</Btn>
        </div>
      </div>
    </Dialog>
  )
}
