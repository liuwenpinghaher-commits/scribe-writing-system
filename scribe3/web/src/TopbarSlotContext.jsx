import { createContext, useCallback, useContext, useEffect, useMemo, useRef } from 'react'

const TopbarSlotContext = createContext({
  setSlot: () => {},
  clearSlot: () => {},
})

export function TopbarSlotProvider({ onSlot, children }) {
  const activeIdRef = useRef(null)

  const setSlot = useCallback((id, node) => {
    activeIdRef.current = id
    onSlot?.(node)
  }, [onSlot])

  const clearSlot = useCallback((id) => {
    if (activeIdRef.current !== id) return
    activeIdRef.current = null
    onSlot?.(null)
  }, [onSlot])

  const value = useMemo(() => ({ setSlot, clearSlot }), [setSlot, clearSlot])
  return <TopbarSlotContext.Provider value={value}>{children}</TopbarSlotContext.Provider>
}

export function useTopbarSlot(id, node) {
  const { setSlot, clearSlot } = useContext(TopbarSlotContext)
  useEffect(() => {
    if (!id || !node) return undefined
    setSlot(id, node)
    return () => clearSlot(id)
  }, [id, node, setSlot, clearSlot])
}
