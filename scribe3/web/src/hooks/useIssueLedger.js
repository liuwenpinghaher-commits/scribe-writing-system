import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

export function normalizeDegradedSource(source) {
  if (!source) return null
  if (typeof source === 'string') return { source, reason: '' }
  if (typeof source === 'object') {
    return {
      source: source.source || source.name || 'unknown',
      chapter: source.chapter,
      reason: source.reason || source.message || '',
    }
  }
  return { source: String(source), reason: '' }
}

export function normalizeIssueLedgerResponse(response) {
  return {
    issues: Array.isArray(response?.issues) ? response.issues : [],
    degraded: (Array.isArray(response?.degraded_sources) ? response.degraded_sources : [])
      .map(normalizeDegradedSource)
      .filter(Boolean),
  }
}

export function useIssueLedger(seq) {
  const [state, setState] = useState({ loading: true, err: '', issues: [], degraded: [] })
  const [reloadKey, setReloadKey] = useState(0)
  const reload = useCallback(() => setReloadKey((v) => v + 1), [])

  useEffect(() => {
    let alive = true
    setState({ loading: true, err: '', issues: [], degraded: [] })
    api.issues(seq)
      .then((response) => {
        if (!alive) return
        const next = normalizeIssueLedgerResponse(response)
        setState({ loading: false, err: '', issues: next.issues, degraded: next.degraded })
      })
      .catch((e) => {
        if (!alive) return
        setState({ loading: false, err: e?.body?.detail || e?.message || '校验台账加载失败', issues: [], degraded: [] })
      })
    return () => { alive = false }
  }, [seq, reloadKey])

  return { ...state, reload }
}
