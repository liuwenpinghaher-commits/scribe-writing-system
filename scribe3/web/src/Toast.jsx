import { createContext, useContext, useState, useCallback } from 'react'

const Ctx = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [confirmer, setConfirmer] = useState(null)

  const toast = useCallback((msg, kind = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, msg, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200)
  }, [])

  const confirm = useCallback((text) => new Promise((resolve) => {
    setConfirmer({ text, resolve })
  }), [])

  return (
    <Ctx.Provider value={{ toast, confirm }}>
      {children}
      <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} role="status"
            className="rounded-lg border border-line bg-surface px-4 py-2.5 text-[13px] text-ink shadow-md">
            {t.msg}
          </div>
        ))}
      </div>
      {confirmer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onMouseDown={(e) => { if (e.target === e.currentTarget) { confirmer.resolve(false); setConfirmer(null) } }}>
          <div role="dialog" aria-modal="true"
            className="rounded-2xl border border-line bg-surface p-5 w-[min(92vw,440px)]">
            <p className="text-ink text-[14px] mb-4">{confirmer.text}</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => { confirmer.resolve(false); setConfirmer(null) }}
                className="h-8 px-3 rounded-lg border border-line text-[13px] text-faint">取消</button>
              <button onClick={() => { confirmer.resolve(true); setConfirmer(null) }}
                className="h-8 px-3 rounded-lg border border-brand/50 text-[13px] text-ink bg-brand/10">确认</button>
            </div>
          </div>
        </div>
      )}
    </Ctx.Provider>
  )
}

export const useToast = () => useContext(Ctx)?.toast
export const useConfirm = () => useContext(Ctx)?.confirm
