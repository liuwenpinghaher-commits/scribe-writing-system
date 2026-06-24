import { useEffect, useRef } from 'react'

export function Modal({ title, onClose, children }) {
  const ref = useRef(null)
  useEffect(() => {
    const node = ref.current
    const prev = document.activeElement
    const focusables = () => node?.querySelectorAll(
      'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])')
    focusables()?.[0]?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key !== 'Tab') return
      const els = [...(focusables() || [])]; if (!els.length) return
      const first = els[0], last = els[els.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    node?.addEventListener('keydown', onKey)
    return () => { node?.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className="rounded-2xl border border-line bg-surface p-5 w-[min(92vw,440px)]">
        {title && <h2 className="text-ink text-[15px] font-semibold mb-3">{title}</h2>}
        {children}
      </div>
    </div>
  )
}
