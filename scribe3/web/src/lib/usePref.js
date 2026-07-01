import { useEffect, useState } from 'react'

// 字符串偏好(localStorage 持久化):左右栏当前 tab 等。
export function usePref(key, def) {
  const [v, setV] = useState(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : s } catch { return def }
  })
  useEffect(() => { try { localStorage.setItem(key, v) } catch { /* */ } }, [key, v])
  return [v, setV]
}
