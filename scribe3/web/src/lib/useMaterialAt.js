/**
 * 主编输入框 @ 引用：章节 / 视图 / 设定 / 事件 / 命题 / 素材。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import {
  buildAtCatalog,
  detectAtQuery,
  filterAtCatalog,
  insertAtMention,
} from './sessionClip.js'
import { nextAtActiveIndex, normalizeMaterialRows } from '../ui/MaterialAtPicker.jsx'

function maxChapterFromTree(manuscriptRoot) {
  let max = 0
  const walk = (n) => {
    if (!n || typeof n !== 'object') return
    if (n.type === 'chapter' && n.ref != null) {
      const s = Number(n.ref)
      if (Number.isFinite(s) && s > max) max = s
    }
    for (const c of n.children || []) walk(c)
  }
  walk(manuscriptRoot)
  return max
}

export async function loadAtCatalogSources(query = '') {
  const q = String(query || '').trim()
  const [matPayload, tree, timelinePayload, entitiesPayload] = await Promise.all([
    api.materials(q ? { q, limit: 80 } : { limit: 300 }),
    api.projectTree().catch(() => null),
    api.timeline(1).catch(() => null),
    api.entities().catch(() => []),
  ])
  const materials = normalizeMaterialRows(matPayload)
  const manuscriptRoot = tree?.manuscript || null
  const codexRoot = tree?.codex || null
  const views = tree?.views || []
  const maxCh = maxChapterFromTree(manuscriptRoot)
  let facts = []
  if (maxCh >= 1) {
    try {
      facts = await api.facts(maxCh)
    } catch {
      facts = []
    }
  }
  return buildAtCatalog({
    materials,
    codexRoot,
    manuscriptRoot,
    views,
    timeline: timelinePayload,
    facts: Array.isArray(facts) ? facts : [],
    entities: Array.isArray(entitiesPayload) ? entitiesPayload : [],
  })
}

export function useMaterialAt({ input, setInput, taRef }) {
  const [at, setAt] = useState(null) // { atIndex, query, caret }
  const [catalog, setCatalog] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (!at) return undefined
    if (catalog != null) return undefined
    let alive = true
    setLoading(true)
    setError('')
    loadAtCatalogSources(at.query)
      .then((cat) => {
        if (!alive) return
        setCatalog(cat)
      })
      .catch((e) => {
        if (!alive) return
        setError(e?.body?.detail || e?.message || '引用目录加载失败')
        setCatalog([])
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [at, catalog])

  const items = useMemo(
    () => filterAtCatalog(catalog || [], at?.query || '', 60),
    [catalog, at?.query],
  )

  const syncFromValue = useCallback((value, caret) => {
    const d = detectAtQuery(value, caret)
    setAt(d)
    if (d) setActiveIndex(0)
  }, [])

  const pick = useCallback((item) => {
    const el = taRef?.current
    const caret = el && typeof el.selectionStart === 'number'
      ? el.selectionStart
      : (at?.caret ?? String(input || '').length)
    const out = insertAtMention(input, caret, item)
    if (!out) return false
    setInput(out.text)
    setAt(null)
    requestAnimationFrame(() => {
      const ta = taRef?.current
      if (!ta) return
      ta.focus()
      try { ta.setSelectionRange(out.caret, out.caret) } catch { /* */ }
    })
    return true
  }, [input, setInput, taRef, at?.caret])

  const openManual = useCallback(() => {
    const el = taRef?.current
    const start = el?.selectionStart ?? String(input || '').length
    const end = el?.selectionEnd ?? start
    const s = String(input || '')
    const next = `${s.slice(0, start)}@${s.slice(end)}`
    const caret = start + 1
    setInput(next)
    setAt({ atIndex: start, query: '', caret })
    setActiveIndex(0)
    setCatalog(null)
    requestAnimationFrame(() => {
      const ta = taRef?.current
      if (!ta) return
      ta.focus()
      try { ta.setSelectionRange(caret, caret) } catch { /* */ }
    })
  }, [input, setInput, taRef])

  const onKeyDown = useCallback((e, { onEnterSend } = {}) => {
    if (!at) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        onEnterSend?.()
      }
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      setAt(null)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((i) => nextAtActiveIndex(i, 1, items.length))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => nextAtActiveIndex(i, -1, items.length))
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const m = items[activeIndex]
      if (m) pick(m)
      return
    }
  }, [at, items, activeIndex, pick])

  const close = useCallback(() => setAt(null), [])

  useEffect(() => {
    const onSaved = () => setCatalog(null)
    window.addEventListener('s3-material-saved', onSaved)
    return () => window.removeEventListener('s3-material-saved', onSaved)
  }, [])

  return {
    open: !!at,
    query: at?.query || '',
    items,
    loading,
    error,
    activeIndex,
    setActiveIndex,
    syncFromValue,
    pick,
    openManual,
    onKeyDown,
    close,
  }
}
