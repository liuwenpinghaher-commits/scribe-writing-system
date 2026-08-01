import test from 'node:test'
import assert from 'node:assert/strict'
import { attachBrowserErrorTrace, partitionVerifiedTerminalSseAborts } from './browser_error_trace.mjs'

test('浏览器404诊断保留方法、无查询参数的路径和资源类型，不保留响应体', async () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  const trace = attachBrowserErrorTrace(page)
  const request = {
    method: () => 'GET',
    resourceType: () => 'fetch',
  }
  const response = {
    status: () => 404,
    url: () => 'http://127.0.0.1:3321/context/sessions/session-1/trace/3?work=book_bf144d14&secret=never-record',
    request: () => request,
  }

  await handlers.get('response')(response)

  assert.deepEqual(trace, [{
    method: 'GET',
    path: '/context/sessions/session-1/trace/3',
    resource_type: 'fetch',
    status: 404,
  }])
})

test('浏览器404诊断不把正常响应或非404响应误记为404', async () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  const trace = attachBrowserErrorTrace(page)
  const request = { method: () => 'GET', resourceType: () => 'fetch' }
  await handlers.get('response')({ status: () => 200, url: () => 'http://127.0.0.1:3321/health', request: () => request })
  await handlers.get('response')({ status: () => 500, url: () => 'http://127.0.0.1:3321/health', request: () => request })
  assert.deepEqual(trace, [])
})

test('浏览器网络失败诊断保留方法、无查询参数路径、资源类型和失败代码', () => {
  const handlers = new Map()
  const page = { on(event, handler) { handlers.set(event, handler) } }
  const trace = attachBrowserErrorTrace(page)
  handlers.get('requestfailed')({
    method: () => 'GET',
    resourceType: () => 'eventsource',
    url: () => 'http://127.0.0.1:3311/api/ai/runs/run_1/events?work=book_bf144d14',
    failure: () => ({ errorText: 'net::ERR_CONNECTION_CLOSED' }),
  })

  assert.deepEqual(trace.failed_requests, [{
    method: 'GET',
    path: '/api/ai/runs/run_1/events',
    resource_type: 'eventsource',
    error: 'net::ERR_CONNECTION_CLOSED',
  }])
})

test('仅把已证实 completed Run 的 EventSource ERR_ABORTED 标为受控关闭', () => {
  const failures = [
    { method: 'GET', path: '/api/ai/runs/run_completed/events', resource_type: 'eventsource', error: 'net::ERR_ABORTED' },
    { method: 'GET', path: '/api/ai/runs/run_failed/events', resource_type: 'eventsource', error: 'net::ERR_ABORTED' },
    { method: 'GET', path: '/api/ai/runs/run_completed/events', resource_type: 'eventsource', error: 'net::ERR_CONNECTION_CLOSED' },
    { method: 'GET', path: '/api/chapters', resource_type: 'fetch', error: 'net::ERR_ABORTED' },
  ]

  const result = partitionVerifiedTerminalSseAborts(failures, new Set(['run_completed']))

  assert.deepEqual(result.controlled_closures, [{
    method: 'GET',
    path: '/api/ai/runs/run_completed/events',
    resource_type: 'eventsource',
    error: 'net::ERR_ABORTED',
    run_id: 'run_completed',
    reason: 'client_closed_after_verified_completed_run',
  }])
  assert.deepEqual(result.unexpected_failures, failures.slice(1))
})

test('浏览器关闭前解绑网络探针，不把 teardown 的主动断连记为验收失败', () => {
  const handlers = new Map()
  const page = {
    on(event, handler) { handlers.set(event, handler) },
    off(event, handler) { if (handlers.get(event) === handler) handlers.delete(event) },
  }
  const trace = attachBrowserErrorTrace(page)
  trace.detach()

  assert.equal(handlers.has('requestfailed'), false)
  assert.equal(handlers.has('response'), false)
})
