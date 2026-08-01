import assert from 'node:assert/strict'
import test from 'node:test'
import {
  APPROVAL_RUN_SETTLE_ATTEMPTS,
  isApprovedWriteFinalized,
} from './approval_run_wait.mjs'

test('图谱作者审批 Run 预留三分钟给真实工具审批和模型收尾', () => {
  assert.equal(APPROVAL_RUN_SETTLE_ATTEMPTS, 180)
})

test('仅当已批准的目标工具写入且 Run 已完成时，图谱写入才算完成', () => {
  const written = {
    status: 'completed',
    tool_outputs: [{ tool: 's3_add_character_relation', result_status: 'written' }],
  }
  assert.equal(isApprovedWriteFinalized(written, 's3_add_character_relation'), true)
  assert.equal(isApprovedWriteFinalized({ ...written, status: 'running' }, 's3_add_character_relation'), false)
})
