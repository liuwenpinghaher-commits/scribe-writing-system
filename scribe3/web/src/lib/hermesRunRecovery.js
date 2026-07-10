import { useEffect, useRef } from 'react'
import { api } from '../api'

const CLOSED_APPROVAL = new Set(['approved', 'denied'])

function runIdOf(value) {
  return value?.run_id || value?.id || ''
}

function approvalKey(approval) {
  return `${approval?.run_id || ''}:${approval?.approval_id || ''}`
}

function errorText(error) {
  return error?.body?.detail || error?.message || String(error || '连接中断')
}

export function patchApprovalInMessages(messages, approval, patch) {
  const key = approvalKey(approval)
  if (!key || key === ':') return messages
  return (messages || []).map((msg) => {
    if (!msg.approvals?.length) return msg
    return {
      ...msg,
      approvals: msg.approvals.map((ap) =>
        approvalKey(ap) === key ? { ...ap, ...patch } : ap),
    }
  })
}

export function collectPendingRunIds(messages, activeRunIds = new Set()) {
  const ids = new Set()
  for (const msg of messages || []) {
    for (const approval of msg.approvals || []) {
      const runId = approval?.run_id || msg.run_id
      if (!runId || activeRunIds.has(runId)) continue
      if (CLOSED_APPROVAL.has(approval.status)) continue
      ids.add(runId)
    }
  }
  return ids
}

export function patchRunMessage(messages, runId, updater) {
  if (!runId) return messages
  let changed = false
  const next = (messages || []).map((msg) => {
    const hit = msg.run_id === runId || (msg.approvals || []).some((ap) => ap.run_id === runId)
    if (!hit) return msg
    changed = true
    return updater(msg)
  })
  return changed ? next : messages
}

export function upsertApprovalInMessages(messages, runId, approval) {
  const normalized = {
    ...approval,
    run_id: approval?.run_id || runId,
    status: approval?.status || 'pending',
  }
  const key = approvalKey(normalized)
  return patchRunMessage(messages, normalized.run_id, (msg) => {
    const approvals = msg.approvals || []
    const exists = approvals.some((ap) => approvalKey(ap) === key)
    return {
      ...msg,
      run_id: msg.run_id || normalized.run_id,
      approvals: exists
        ? approvals.map((ap) => approvalKey(ap) === key ? { ...ap, ...normalized } : ap)
        : [...approvals, normalized],
    }
  })
}

export function useHermesRunRecovery({ msgs, setMsgs, setBusy, activeRunIdsRef }) {
  const streamsRef = useRef(new Map())
  const closedRef = useRef(new Set())

  useEffect(() => {
    const active = activeRunIdsRef?.current || new Set()
    const pending = collectPendingRunIds(msgs, active)
    for (const [runId, stream] of streamsRef.current.entries()) {
      if (!pending.has(runId)) {
        stream?.close?.()
        streamsRef.current.delete(runId)
      }
    }
    for (const runId of pending) {
      if (streamsRef.current.has(runId) || closedRef.current.has(runId)) continue
      const marker = { close: null }
      streamsRef.current.set(runId, marker)
      api.aiRunStatus(runId)
        .then((status) => {
          if (!streamsRef.current.has(runId)) return
          const currentRunId = runIdOf(status) || runId
          setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
            ...msg,
            run_id: msg.run_id || currentRunId,
            runStatus: status?.status || status?.state || msg.runStatus,
          })))
          const es = api.aiRunEvents(runId, {
            onDelta: (delta) => setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
              ...msg,
              content: (msg.content || '') + delta,
            }))),
            onTool: (name) => setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
              ...msg,
              tools: [...(msg.tools || []), name],
            }))),
            onToolOutput: (output, call_id) => setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
              ...msg,
              toolOutputs: [...(msg.toolOutputs || []), { output, call_id }],
            }))),
            onApproval: (approval) => setMsgs((items) => upsertApprovalInMessages(items, runId, approval)),
            onApprovalResolved: (approval) => {
              const status = approval?.decision === 'approve' ? 'approved' : 'denied'
              setMsgs((items) => patchApprovalInMessages(items, { ...approval, run_id: approval?.run_id || runId }, { ...approval, status }))
            },
            onRun: (run) => setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
              ...msg,
              run_id: msg.run_id || runIdOf(run) || runId,
              runStatus: run?.status || msg.runStatus,
            }))),
            onDone: () => {
              closedRef.current.add(runId)
              streamsRef.current.delete(runId)
              setBusy(false)
            },
            onError: (err) => {
              closedRef.current.add(runId)
              streamsRef.current.delete(runId)
              setBusy(false)
              setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
                ...msg,
                content: `${msg.content || ''}\n\n_⚠ Hermes Run 恢复失败:${errorText(err)}_`,
              })))
            },
          })
          marker.close = () => es?.close?.()
        })
        .catch((error) => {
          closedRef.current.add(runId)
          streamsRef.current.delete(runId)
          setMsgs((items) => patchRunMessage(items, runId, (msg) => ({
            ...msg,
            content: `${msg.content || ''}\n\n_⚠ Hermes Run 状态恢复失败:${errorText(error)}_`,
          })))
        })
    }
  }, [msgs, setMsgs, setBusy, activeRunIdsRef])

  useEffect(() => () => {
    for (const stream of streamsRef.current.values()) stream?.close?.()
    streamsRef.current.clear()
  }, [])
}
