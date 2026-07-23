import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useContextSnapshot } from './ContextSnapshotContext'
import { showToast } from '../ui/Toast.jsx'

/**
 * 作者面·待审正典揭示队列。
 * 调 shipped REST: GET /memory/pending-claims · POST .../resolve
 * fabric 默认开;capabilities 报关时不渲染(与 Inspector 诚实同口径)。
 */
export function PendingClaimsPanel() {
  const { capabilities } = useContextSnapshot()
  const fabricOn = capabilities?.flags?.memory_fabric_v1 !== false
  const [claims, setClaims] = useState([])
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState(null)

  const reload = useCallback(() => {
    if (!fabricOn || typeof api?.listPendingClaims !== 'function') return
    setLoading(true)
    setError(null)
    Promise.resolve(api.listPendingClaims('pending'))
      .then((r) => {
        const list = Array.isArray(r?.claims) ? r.claims : Array.isArray(r) ? r : []
        setClaims(list)
      })
      .catch((e) => {
        setClaims([])
        setError(e?.body?.detail || e?.message || '加载失败')
      })
      .finally(() => setLoading(false))
  }, [fabricOn])

  useEffect(() => {
    reload()
  }, [reload])

  const resolve = async (claimId, decision) => {
    if (!claimId || busyId) return
    setBusyId(claimId)
    try {
      const out = await api.resolvePendingClaim(claimId, {
        decision,
        valid_from: 1,
        secret: false,
      })
      if (decision === 'approve' && !out?.fact_id && out?.status !== 'approved') {
        throw new Error(out?.error || '批准未写入正典')
      }
      showToast(
        decision === 'approve' ? '已写入正典' : '已拒绝该条',
        { tone: decision === 'approve' ? 'ok' : 'warn' },
      )
      setClaims((prev) => prev.filter((c) => {
        const id = c.id || c.claim_id
        return id !== claimId && !(typeof id === 'string' && id.endsWith(claimId))
      }))
    } catch (e) {
      showToast(`处理失败:${e?.body?.detail || e?.message || e}`, { tone: 'danger' })
    } finally {
      setBusyId(null)
    }
  }

  if (!fabricOn) return null

  return (
    <div
      data-testid="pending-claims-panel"
      className="border-b border-line bg-surface/40 px-3 py-2 space-y-1.5"
    >
      <div className="flex items-center gap-2 text-meta">
        <span className="font-medium text-ink">待审正典</span>
        <span className="text-faint tabular-nums" data-testid="pending-claims-count">
          {loading ? '…' : claims.length}
        </span>
        <button
          type="button"
          data-testid="pending-claims-reload"
          className="ml-auto text-f12 text-brand hover:underline"
          onClick={reload}
        >
          刷新
        </button>
      </div>
      {error && (
        <div data-testid="pending-claims-error" className="text-meta text-danger">
          {typeof error === 'string' ? error : JSON.stringify(error)}
        </div>
      )}
      {!loading && claims.length === 0 && !error && (
        <div data-testid="pending-claims-empty" className="text-meta text-faint">
          暂无待审揭示
        </div>
      )}
      <ul data-testid="pending-claims-list" className="space-y-1.5">
        {claims.map((c) => {
          const id = c.id || c.claim_id
          const text = c.text || c.claim_text || c.summary
            || [c.entity, c.attribute, c.value].filter(Boolean).join(' · ')
            || id
          return (
            <li
              key={id}
              data-testid="pending-claim-row"
              data-claim-id={id}
              className="rounded border border-line bg-canvas/80 px-2 py-1.5 text-meta"
            >
              <div className="text-ink leading-snug break-words">{text}</div>
              <div className="mt-1 flex gap-2">
                <button
                  type="button"
                  data-testid="pending-claim-approve"
                  disabled={!!busyId}
                  className="text-f12 text-ok hover:underline disabled:opacity-40"
                  onClick={() => resolve(id, 'approve')}
                >
                  批准入正典
                </button>
                <button
                  type="button"
                  data-testid="pending-claim-reject"
                  disabled={!!busyId}
                  className="text-f12 text-warn hover:underline disabled:opacity-40"
                  onClick={() => resolve(id, 'reject')}
                >
                  拒绝
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
