/**
 * WriteProposal 多 op 审批卡（编排层产物）。
 * 展示 summary + ops；批准/拒绝走 /orchestration/proposal/apply（execute 默认 false，
 * 生产主路径仍是 Hermes 审批；本卡用于编排预览与测试契约）。
 */
import { useState } from 'react'
import { api } from './api'
import { applyUiEvents } from './lib/uiDirective'
import { Btn } from './ui.jsx'

export function WriteProposalCard({ proposal, onDone, execute = false }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  if (!proposal?.ops?.length && !result) return null
  const ops = result?.ops || proposal.ops || []
  const status = result?.status || proposal.status || 'pending'

  const act = async (decision) => {
    setBusy(true)
    try {
      const res = await api.orchApplyProposal({
        proposal: result || proposal,
        decision,
        execute: !!execute && decision === 'approve',
      })
      setResult(res.proposal)
      if (res.ui_events?.length) applyUiEvents(res.ui_events)
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
      <div className="text-f13 font-medium">{(result || proposal).summary || '写入提案'}</div>
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
      {(result || proposal).note && (
        <p className="text-meta text-faint">{(result || proposal).note}</p>
      )}
    </div>
  )
}
