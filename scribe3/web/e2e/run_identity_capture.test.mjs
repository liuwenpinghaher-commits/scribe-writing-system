import test from 'node:test'
import assert from 'node:assert/strict'
import { attachCompletedRunCapture, attachRunIdentityCapture } from './run_identity_capture.mjs'

test('从真实 ai/runs 创建响应捕获 run_id 与 URL 中的作品隔离键', async () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  let seen = null
  attachRunIdentityCapture(page, (value) => { seen = value })

  await handlers.get('response')({
    status: () => 200,
    url: () => 'http://127.0.0.1:3311/api/ai/runs?work=book_bf144d14',
    request: () => ({ method: () => 'POST' }),
    json: async () => ({ run_id: 'run_real', status: 'created' }),
  })

  assert.deepEqual(seen, { id: 'run_real', work: 'book_bf144d14' })
})

test('非创建响应或无 run_id 的响应不覆盖已知身份', async () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  let calls = 0
  attachRunIdentityCapture(page, () => { calls += 1 })
  await handlers.get('response')({
    status: () => 200,
    url: () => 'http://127.0.0.1:3311/api/ai/runs/run_real?work=book_bf144d14',
    request: () => ({ method: () => 'GET' }),
    json: async () => ({ run_id: 'run_real' }),
  })
  await handlers.get('response')({
    status: () => 200,
    url: () => 'http://127.0.0.1:3311/api/ai/runs?work=book_bf144d14',
    request: () => ({ method: () => 'POST' }),
    json: async () => ({}),
  })
  assert.equal(calls, 0)
})

test('只从浏览器实际收到的 completed 状态响应记录可证实终态', async () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  const seen = []
  attachCompletedRunCapture(page, (value) => { seen.push(value) })

  await handlers.get('response')({
    status: () => 200,
    url: () => 'http://127.0.0.1:3311/api/ai/runs/run_completed?work=book_bf144d14',
    request: () => ({ method: () => 'GET' }),
    json: async () => ({ run_id: 'run_completed', status: 'completed' }),
  })
  await handlers.get('response')({
    status: () => 200,
    url: () => 'http://127.0.0.1:3311/api/ai/runs/run_unverified?work=book_bf144d14',
    request: () => ({ method: () => 'GET' }),
    json: async () => ({ run_id: 'run_unverified', status: 'completed_unverified' }),
  })

  assert.deepEqual(seen, [{ id: 'run_completed', work: 'book_bf144d14' }])
})
