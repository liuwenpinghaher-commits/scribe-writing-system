import { useEffect, useRef } from 'react'

// 轻量对话历史持久化:按 storageKey 存/取 localStorage。
// 切 key(切章/切节点)时:先把当前对话刷回旧 key,再载入新 key 的历史。
// 仅存最近 MAX 条,避免 localStorage 膨胀;失败静默(隐私模式/超额)。
//
// Task 6:线程模式(opts.mode === 'thread')降权为「未发送草稿 + 断网未同步消息」缓存——
// 键前缀 draft:,且**不 load-replace 消息**(消息由服务端 threadMessages 供给,持久层不接管
// setMsgs,否则会 clobber 掉刚载入的线程历史)。旧 chatKey 模式行为一字不变。
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
 * useChatPersist(storageKey, msgs, setMsgs, opts?)
 *  - 旧模式(opts 缺省):storageKey 变化 → 落旧 key、用新 key 历史替换 msgs;msgs 变化防抖落盘。
 *  - 线程模式(opts.mode === 'thread'):持久键降权为 draft:<storageKey>,只防抖落盘、
 *    **不** 在 key 切换时 load-replace 消息(消息事实源在服务端)。
 * 返回时不需要任何值;副作用即持久化。
 */
export function useChatPersist(storageKey, msgs, setMsgs, opts) {
  const thread = opts?.mode === 'thread'
  // 线程模式用独立 draft: 命名空间,不与旧 chatKey 全量历史撞键。
  const persistKey = thread && storageKey ? 'draft:' + storageKey : storageKey
  const prevKeyRef = useRef(null)
  const msgsRef = useRef(msgs)
  msgsRef.current = msgs

  // key 切换:旧模式先落旧 key、再载新 key;线程模式不 load-replace(不 clobber 服务端消息)。
  useEffect(() => {
    const prevKey = prevKeyRef.current
    if (!thread && prevKey && prevKey !== persistKey) saveChat(prevKey, msgsRef.current)
    if (prevKey !== persistKey) {
      prevKeyRef.current = persistKey
      if (!thread) setMsgs(loadChat(persistKey))
    }
  }, [persistKey, thread]) // eslint-disable-line react-hooks/exhaustive-deps

  // msgs 变化:防抖落盘(两种模式都做——线程模式即「断网未同步消息」的本地兜底)。
  useEffect(() => {
    if (!persistKey) return
    const t = setTimeout(() => saveChat(persistKey, msgs), 400)
    return () => clearTimeout(t)
  }, [persistKey, msgs])

  // 卸载:立即落盘当前(线程模式同样兜底,键为 draft:)。
  useEffect(() => () => saveChat(prevKeyRef.current, msgsRef.current), [])
}
