import assert from 'node:assert/strict'
import test from 'node:test'
import { isReadOnlyRunCompleted } from './run_trace_status.mjs'

test('只读 Run 的远端完成态不因本地审计汇总尚未结束而被误判为未完成', () => {
  const trace = {
    status: 'remote_completed_pending_audit',
    response: { status: 'completed' },
    tool_calls: [{ name: 's3_get_chapter' }],
  }

  assert.equal(isReadOnlyRunCompleted(trace, 's3_get_chapter'), true)
})

test('只读 Run 缺少必需读取工具或远端未完成时不能通过', () => {
  assert.equal(isReadOnlyRunCompleted({
    status: 'remote_completed_pending_audit',
    response: { status: 'completed' },
    tool_calls: [],
  }, 's3_get_chapter'), false)
  assert.equal(isReadOnlyRunCompleted({
    status: 'running',
    response: { status: 'running' },
    tool_calls: [{ name: 's3_get_chapter' }],
  }, 's3_get_chapter'), false)
})
