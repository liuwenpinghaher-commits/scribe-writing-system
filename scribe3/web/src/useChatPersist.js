import { useEffect, useRef } from 'react'

// 轻量对话历史持久化:按 storageKey 存/取 localStorage。
// 切 key(切章/切节点)时:先把当前对话刷回旧 key,再载入新 key 的历史。
// 仅存最近 MAX 条,避免 localStorage 膨胀;失败静默(隐私模式/超额)。
const MAX = 60
const PREFIX = 's3.chat.'

export function loadChat(storageKey) {
  if (!storageKey) return []
  try {
    const raw = localStorage.getItem(PREFIX + storageKey)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch { return [] }
}

function saveChat(storageKey, msgs) {
  if (!storageKey) return
  try {
    const slim = (msgs || []).slice(-MAX)
    if (slim.length === 0) localStorage.removeItem(PREFIX + storageKey)
    else localStorage.setItem(PREFIX + storageKey, JSON.stringify(slim))
  } catch { /* 静默 */ }
}

/**
 * useChatPersist(storageKey, msgs, setMsgs)
 *  - storageKey 变化:把旧 key 的内容落盘,再用新 key 的历史替换 msgs。
 *  - msgs 变化:防抖落盘当前 key。
 * 返回时不需要任何值;副作用即持久化。
 */
export function useChatPersist(storageKey, msgs, setMsgs) {
  const prevKeyRef = useRef(null)
  const msgsRef = useRef(msgs)
  msgsRef.current = msgs

  // key 切换:先落旧 key,再载新 key
  useEffect(() => {
    const prevKey = prevKeyRef.current
    if (prevKey && prevKey !== storageKey) saveChat(prevKey, msgsRef.current)
    if (prevKey !== storageKey) {
      prevKeyRef.current = storageKey
      setMsgs(loadChat(storageKey))
    }
  }, [storageKey]) // eslint-disable-line react-hooks/exhaustive-deps

  // msgs 变化:防抖落盘
  useEffect(() => {
    if (!storageKey) return
    const t = setTimeout(() => saveChat(storageKey, msgs), 400)
    return () => clearTimeout(t)
  }, [storageKey, msgs])

  // 卸载:立即落盘当前
  useEffect(() => () => saveChat(prevKeyRef.current, msgsRef.current), [])
}
