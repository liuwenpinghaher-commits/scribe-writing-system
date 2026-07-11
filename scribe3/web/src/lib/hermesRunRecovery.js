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

// Task 13:审批 409 → run 过期上下文卡片数据(前端展示"发起时/当前焦点 + 已过期")。
// run_context_changed = 影响当前章/条目 → 原审批作废,须重新发起(voided);
// run_context_stale   = 无关的过期 run → 用户二次确认后带 approve_stale=true 可放行。
export function runContextFromError(error) {
  const detail = error?.body?.detail
  if (!detail || typeof detail !== 'object') return null
  if (detail.code !== 'run_context_changed' && detail.code !== 'run_context_stale') return null
  return {
    code: detail.code,
    voided: detail.code === 'run_context_changed',
    originFocus: detail.origin_focus ?? null,
    currentFocus: detail.current_focus ?? null,
    originRevision: detail.origin_context_revision ?? null,
    currentRevision: detail.current_context_revision ?? null,
  }
}

// Task 13:刷新恢复只依 run_id + parent_thread_id——把 GET /ai/runs/{id}/trace 的
// 发起时上下文/写入影响回贴到对应 run 消息,不依赖任何进程内 React state。
export function applyRunTraceToMessages(messages, runId, trace) {
  if (!runId || !trace) return messages
  return patchRunMessage(messages, runId, (msg) => ({
    ...msg,
    run_id: msg.run_id || runId,
    parentThreadId: trace.parent_thread_id ?? msg.parentThreadId ?? null,
    originFocus: trace.focus ?? msg.originFocus ?? null,
    originRevision: trace.origin_context_revision ?? msg.originRevision ?? null,
    writeEffects: trace.write_effects ?? msg.writeEffects ?? [],
  }))
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
      // Task 13:先按 run_id 拉 trace,回贴 parent_thread_id/发起时焦点/写入影响
      // (刷新后卡片据此重建,不依赖内存 state)。best-effort:失败/未 mock 不阻断重连。
      if (typeof api.aiRunTrace === 'function') {
        api.aiRunTrace(runId)
          .then((trace) => setMsgs((items) => applyRunTraceToMessages(items, runId, trace)))
          .catch(() => {})
      }
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
                content: `${msg.content || ''}\n\n_出错:Hermes Run 恢复失败:${errorText(err)}_`,
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
            content: `${msg.content || ''}\n\n_出错:Hermes Run 状态恢复失败:${errorText(error)}_`,
          })))
        })
    }
  }, [msgs, setMsgs, setBusy, activeRunIdsRef])

  useEffect(() => () => {
    for (const stream of streamsRef.current.values()) stream?.close?.()
    streamsRef.current.clear()
  }, [])
}
