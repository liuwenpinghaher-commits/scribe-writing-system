import { describe, it, expect } from 'vitest'
import {
  runContextFromError,
  applyRunTraceToMessages,
  collectPendingRunIds,
  patchRunMessage,
  upsertApprovalInMessages,
  patchApprovalInMessages,
} from './hermesRunRecovery'

// Task 13:审批 409 → 过期上下文卡片数据(纯映射,前端据此展示"发起时/当前焦点 + 已过期")。
describe('runContextFromError', () => {
  it('run_context_changed → voided=true,带发起时/当前焦点', () => {
    const rc = runContextFromError({
      status: 409,
      body: { detail: {
        code: 'run_context_changed',
        origin_focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章' },
        current_focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章' },
        origin_context_revision: 8,
        current_context_revision: 9,
      } },
    })
    expect(rc).toMatchObject({
      code: 'run_context_changed',
      voided: true,
      originRevision: 8,
      currentRevision: 9,
    })
    expect(rc.originFocus.label).toBe('第 9 章')
  })

  it('run_context_stale → voided=false(可二次确认放行)', () => {
    const rc = runContextFromError({ body: { detail: { code: 'run_context_stale', origin_focus: null, current_focus: null } } })
    expect(rc.voided).toBe(false)
    expect(rc.code).toBe('run_context_stale')
  })

  it('非 run 上下文错误 / 无 detail → null(回退通用提交失败)', () => {
    expect(runContextFromError({ body: { detail: { code: 'stale_context' } } })).toBeNull()
    expect(runContextFromError({ message: '网络断了' })).toBeNull()
    expect(runContextFromError(null)).toBeNull()
  })
})

// Task 13:刷新恢复只依 run_id + parent_thread_id——把 trace 回贴到对应 run 消息。
describe('applyRunTraceToMessages', () => {
  const trace = {
    parent_thread_id: 'ethread:book-a',
    focus: { type: 'chapter', id: 'chapter:9', label: '第 9 章' },
    origin_context_revision: 8,
    write_effects: [{ kind: 'approval', context_revision: 8 }],
  }

  it('按 run_id 命中 → 回贴 parent/发起焦点/写入影响(不依赖任何 React state)', () => {
    const msgs = [
      { role: 'user', content: '登记设定' },
      { role: 'assistant', content: '', run_id: 'run_1', approvals: [{ run_id: 'run_1', approval_id: 'ap_1' }] },
    ]
    const next = applyRunTraceToMessages(msgs, 'run_1', trace)
    expect(next[1].parentThreadId).toBe('ethread:book-a')
    expect(next[1].originFocus.id).toBe('chapter:9')
    expect(next[1].originRevision).toBe(8)
    expect(next[1].writeEffects).toHaveLength(1)
  })

  it('无 runId / 无 trace / 不命中 → 原数组不变', () => {
    const msgs = [{ role: 'assistant', run_id: 'other' }]
    expect(applyRunTraceToMessages(msgs, '', trace)).toBe(msgs)
    expect(applyRunTraceToMessages(msgs, 'run_1', null)).toBe(msgs)
    expect(applyRunTraceToMessages(msgs, 'run_1', trace)).toBe(msgs)
  })
})

describe('collectPendingRunIds', () => {
  it('未决审批的 run_id 入集;已批准/拒绝或在途 run 排除', () => {
    const msgs = [
      { approvals: [{ run_id: 'run_pending', approval_id: 'a1', status: 'pending' }] },
      { approvals: [{ run_id: 'run_done', approval_id: 'a2', status: 'approved' }] },
      { run_id: 'run_active', approvals: [{ approval_id: 'a3', status: 'pending' }] },
    ]
    const ids = collectPendingRunIds(msgs, new Set(['run_active']))
    expect(ids.has('run_pending')).toBe(true)
    expect(ids.has('run_done')).toBe(false)
    expect(ids.has('run_active')).toBe(false)
  })
})

describe('patchRunMessage / upsertApprovalInMessages / patchApprovalInMessages', () => {
  it('patchRunMessage 命中 run_id 才改;不命中返回原数组', () => {
    const msgs = [{ run_id: 'run_1', content: 'x' }, { content: 'y' }]
    const next = patchRunMessage(msgs, 'run_1', (m) => ({ ...m, content: 'z' }))
    expect(next[0].content).toBe('z')
    expect(patchRunMessage(msgs, 'nope', (m) => m)).toBe(msgs)
  })

  it('upsert 新审批后 patch 其状态', () => {
    let msgs = [{ run_id: 'run_1', content: '', approvals: [] }]
    msgs = upsertApprovalInMessages(msgs, 'run_1', { approval_id: 'ap_1', message: '允许?' })
    expect(msgs[0].approvals[0].status).toBe('pending')
    msgs = patchApprovalInMessages(msgs, { run_id: 'run_1', approval_id: 'ap_1' }, { status: 'approved' })
    expect(msgs[0].approvals[0].status).toBe('approved')
  })
})
