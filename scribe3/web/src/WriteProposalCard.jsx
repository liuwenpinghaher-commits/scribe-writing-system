/**
 * WriteProposal 多 op 审批卡（编排层产物）。
 * 展示 summary + ops；批准/拒绝走 /orchestration/proposal/apply（execute 默认 false，
 * 生产主路径仍是 Hermes 审批；本卡用于编排预览与测试契约）。
 */
import { useEffect, useState } from 'react'
import { api } from './api'
import { applyUiEvents } from './lib/uiDirective'
import { withFeedback } from './lib/withFeedback.js'
import { Btn } from './ui.jsx'

export function WriteProposalCard({ proposal, onDone, execute = false, onSel = null, setFocus = null }) {
  const optsOnSel = onSel
  const optsSetFocus = setFocus
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [hydrated, setHydrated] = useState(null)
  useEffect(() => {
    const pid = proposal?.id
    if (!pid || typeof api.orchGetProposal !== 'function') return
    let dead = false
    api.orchGetProposal(pid).then((row) => {
      if (!dead && row && (row.ops || row.summary)) setHydrated(row)
    }).catch(() => {})
    return () => { dead = true }
  }, [proposal?.id])
  const view = result || hydrated || proposal
  if (!view?.ops?.length && !result) return null
  const ops = view.ops || []
  const status = view.status || 'pending'

  const act = async (decision) => {
    setBusy(true)
    try {
      const res = await withFeedback(
        api.orchApplyProposal({
          proposal: view,
          decision,
          execute: !!execute && decision === 'approve',
        }),
        { ok: decision === 'approve' ? '提案已批准' : '提案已拒绝', fail: '操作失败' },
      )
      setResult(res.proposal)
      if (res.ui_events?.length) {
        applyUiEvents(res.ui_events, { onSel: optsOnSel, setFocus: optsSetFocus })
      }
      onDone?.(res)
    } catch (e) {
      setResult({
        ...(result || proposal),
        status: 'error',
        error: e?.body?.detail || e?.message || '失败',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      data-testid="write-proposal-card"
      className="rounded-lg border border-brand/30 bg-brand/5 p-3 space-y-2 text-ink"
    >
      <div className="text-f13 font-medium">{view.summary || '写入提案'}</div>
      <ul className="space-y-1 text-meta">
        {ops.map((op, i) => (
          <li key={i} data-status={op.status} className="flex gap-2">
            <span className="text-faint shrink-0">{op.status || 'pending'}</span>
            <span>{op.label || op.tool}</span>
          </li>
        ))}
      </ul>
      {status === 'pending' || status === 'awaiting_hermes_approval' ? (
        <div className="flex gap-2">
          <Btn size="sm" disabled={busy} onClick={() => act('approve')} data-testid="proposal-approve">
            批准
          </Btn>
          <Btn size="sm" variant="ghost" disabled={busy} onClick={() => act('reject')} data-testid="proposal-reject">
            拒绝
          </Btn>
        </div>
      ) : (
        <div className="text-meta text-faint">状态：{status}</div>
      )}
      {view.note && (
        <p className="text-meta text-faint">{view.note}</p>
      )}
    </div>
  )
}
