import { createContext, useContext, useReducer, useCallback } from 'react'

export function toastReducer(state, action) {
  if (action.type === 'add') return [...state, { id: action.toast.id ?? (state.at(-1)?.id ?? 0) + 1, ...action.toast }]
  if (action.type === 'remove') return state.filter((t) => t.id !== action.id)
  return state
}

const ToastCtx = createContext(null)
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [toasts, dispatch] = useReducer(toastReducer, [])
  const toast = useCallback((msg, opts = {}) => {
    const id = Date.now() + Math.floor(Math.random() * 1000)
    dispatch({ type: 'add', toast: { id, msg, tone: opts.tone || 'ink' } })
    setTimeout(() => dispatch({ type: 'remove', id }), opts.duration ?? 4000)
  }, [])
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[120] flex flex-col items-center gap-2 pointer-events-none">
        {toasts.map((t) => (
          <div key={t.id} role="status"
               className={`pointer-events-auto rounded-lg px-3 py-2 text-[12.5px] shadow-[var(--shadow-card)] border ${t.tone === 'danger' ? 'bg-danger/10 border-danger/30 text-danger' : 'bg-ink text-canvas border-transparent'}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
