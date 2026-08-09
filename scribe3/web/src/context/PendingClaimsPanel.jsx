import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import { useContextSnapshot } from './ContextSnapshotContext'
import { showToast } from '../ui/Toast.jsx'

/**
 * 作者面·待审正典揭示队列。
 *
 * 业务：讨论/写作捕获的高风险设定断言(身份/血缘/生死/秘密…)不进 memory_item，
 * 先进 pending_authority_claim；作者批入正典或拒绝。
 * API: GET /memory/pending-claims · POST .../resolve
 * fabric 关时不渲染。
 */
const IDENTITY_ATTRS = new Set([
  'identity', 'kinship', 'secret', 'betrayal', '身份', '真名', '本名',
])

export function PendingClaimsPanel() {
  const { capabilities, snapshot } = useContextSnapshot()
  const fabricOn = capabilities?.flags?.memory_fabric_v1 !== false
  const workKey = (snapshot?.work || (typeof api?.getWork === 'function' ? api.getWork() : null) || '')
  const chapter = snapshot?.chapter != null && Number.isFinite(Number(snapshot.chapter))
    ? Number(snapshot.chapter)
    : null
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
  }, [fabricOn, workKey])

  useEffect(() => {
    reload()
  }, [reload])

  // 讨论/写作结束后可刷新：听 live 或短轮询不合适；作者点刷新即可。
  // work 切换已由 workKey 触发 reload。

  const resolve = async (claim, decision) => {
    const claimId = claim?.id || claim?.claim_id
    if (!claimId || busyId) return
    setBusyId(claimId)
    try {
      const attr = String(claim?.attribute || '').trim()
      const secretDefault = IDENTITY_ATTRS.has(attr)
      const validFrom = chapter != null && chapter > 0 ? chapter : 1
      const out = await api.resolvePendingClaim(claimId, {
        decision,
        valid_from: validFrom,
        // 身份类默认 secret；其它尊重后端/默认 false
        secret: decision === 'approve' ? secretDefault : false,
      })
      if (decision === 'approve' && !out?.fact_id && out?.status !== 'approved') {
        throw new Error(out?.error || '批准未写入正典')
      }
      showToast(
        decision === 'approve'
          ? (out?.secret ? '已写入正典（标为私密）' : '已写入正典')
          : '已拒绝该条',
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
        <div data-testid="pending-claims-empty" className="text-meta text-faint leading-snug">
          暂无待审揭示。讨论或写作中若提到身份/血缘/生死/秘密等稳定断言，会进入此队列等人批后再写进设定圣经（与 Codex「待确认设定」不同路径）。
        </div>
      )}
      <ul data-testid="pending-claims-list" className="space-y-1.5">
        {claims.map((c) => {
          const id = c.id || c.claim_id
          const text = c.text || c.claim_text || c.summary
            || [c.entity, c.attribute, c.value].filter(Boolean).join(' · ')
            || id
          const meta = [c.entity, c.attribute].filter(Boolean).join(' · ')
          return (
            <li
              key={id}
              data-testid="pending-claim-row"
              data-claim-id={id}
              className="rounded border border-line bg-canvas/80 px-2 py-1.5 text-meta"
            >
              <div className="text-ink leading-snug break-words">{text}</div>
              {meta ? (
                <div className="mt-0.5 text-faint text-f12 font-mono truncate" title={meta}>
                  {meta}
                  {IDENTITY_ATTRS.has(String(c.attribute || '')) ? ' · 将标私密' : ''}
                </div>
              ) : null}
              <div className="mt-1 flex gap-2">
                <button
                  type="button"
                  data-testid="pending-claim-approve"
                  disabled={!!busyId}
                  className="text-f12 text-ok hover:underline disabled:opacity-40"
                  onClick={() => resolve(c, 'approve')}
                >
                  批准入正典
                </button>
                <button
                  type="button"
                  data-testid="pending-claim-reject"
                  disabled={!!busyId}
                  className="text-f12 text-warn hover:underline disabled:opacity-40"
                  onClick={() => resolve(c, 'reject')}
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
