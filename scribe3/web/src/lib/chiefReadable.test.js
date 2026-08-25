import { describe, expect, it } from 'vitest'
import {
  chiefSendKind,
  chiefSendHint,
  chiefEmptyKind,
  chiefEmptyCopy,
  pendingApprovalOf,
  seedOrigin,
} from './chiefReadable.js'
import { shouldUseHermesRun } from './hermesRunIntent.js'

describe('chiefSendKind', () => {
  it('marks world-write talk as write, next-stroke as discuss', () => {
    expect(chiefSendKind('请调用 s3_patch_character 写入落库(需我审批)')).toBe('write')
    expect(shouldUseHermesRun('请调用 s3_patch_character 写入落库(需我审批)')).toBe(true)
    expect(chiefSendKind('【时间线】围绕第4章的「井底夜审」只讨论下一笔可落地的动作（不要调用写库工具）。')).toBe('discuss')
    expect(chiefSendHint('write')).toMatch(/改库/)
    expect(chiefSendHint('discuss')).toMatch(/讨论/)
  })
})

describe('chiefEmptyKind', () => {
  it('does not say 一切有账', () => {
    expect(chiefEmptyKind({ work: '', msgs: [] })).toBe('no_work')
    expect(chiefEmptyCopy('no_work').title).toMatch(/选书/)
    expect(chiefEmptyKind({ work: 'demo', threadMode: true, threadId: null, msgs: [] })).toBe('no_thread')
    expect(chiefEmptyKind({ work: 'demo', msgs: [], pending: true })).toBe('awaiting')
    expect(chiefEmptyKind({
      work: 'demo',
      pending: true,
      msgs: [{ role: 'assistant', approvals: [{ status: 'pending' }] }],
    })).toBe(null)
    expect(chiefEmptyCopy('awaiting').title).toMatch(/批/)
    expect(chiefEmptyCopy('empty_ask').body).not.toMatch(/一切有账/)
    expect(chiefEmptyCopy('fresh').title).not.toMatch(/一切有账/)
    expect(chiefEmptyKind({ work: 'demo', msgs: [], surface: 'write' })).toBe('write_ask')
    expect(chiefEmptyCopy('write_ask').title).toMatch(/空会话可以问/)
    expect(chiefEmptyCopy('write_ask').body).toMatch(/草稿卡/)
    expect(chiefEmptyCopy('write_ask').body).not.toMatch(/一切有账/)
  })
})

describe('pendingApprovalOf', () => {
  it('finds the last pending approval', () => {
    const ap = pendingApprovalOf([
      { role: 'user', content: '写' },
      { role: 'assistant', approvals: [{ approval_id: 'a1', status: 'approved' }] },
      { role: 'assistant', approvals: [{ approval_id: 'a2', status: 'pending', message: '允许写入?' }] },
    ])
    expect(ap.approval_id).toBe('a2')
    expect(pendingApprovalOf([])).toBe(null)
  })
})

describe('seedOrigin', () => {
  it('reads seed header without changing text', () => {
    expect(seedOrigin('【时间线】围绕第3章')).toBe('timeline')
    expect(seedOrigin('【仪表盘】针对第3章')).toBe('insight')
    expect(seedOrigin('【图谱·信息差】截至第3章')).toBe('atlas')
    expect(seedOrigin('普通问一句')).toBe(null)
  })
})
