import { useCallback, useEffect, useState } from 'react'

function readPref(storageKey, initialValue) {
  try {
    const stored = localStorage.getItem(storageKey)
    return stored == null ? initialValue : stored
  } catch {
    return initialValue
  }
}

export function useWorkScopedPref(work, key, initialValue) {
  const safeWork = work || 'main'
  const storageKey = `s3.${safeWork}.${key}`
  const [state, setState] = useState(() => ({
    key: storageKey,
    value: readPref(storageKey, initialValue),
  }))

  const value = state.key === storageKey ? state.value : readPref(storageKey, initialValue)

  useEffect(() => {
    if (state.key !== storageKey) {
      setState({ key: storageKey, value: readPref(storageKey, initialValue) })
    }
  }, [initialValue, state.key, storageKey])

  useEffect(() => {
    try { localStorage.setItem(storageKey, value) } catch { /* localStorage unavailable */ }
  }, [storageKey, value])

  const setValue = useCallback((next) => {
    setState((prev) => ({
      key: storageKey,
      value: typeof next === 'function' ? next(prev.key === storageKey ? prev.value : readPref(storageKey, initialValue)) : next,
    }))
  }, [initialValue, storageKey])

  return [value, setValue]
}
