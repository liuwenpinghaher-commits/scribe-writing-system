/**
 * 经验压力层 api.js 接线断言:真实路径字符串,mock fetch 在网络边界。
 * 不重实现后端;只验 URL/method/body 与 shipped 路由一致。
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'

afterEach(() => { vi.restoreAllMocks() })

function spyFetch(payload = { ok: true }) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true, status: 200, json: async () => payload,
  })
}
const lastUrl = (spy) => spy.mock.calls.at(-1)[0]
const lastOpts = (spy) => spy.mock.calls.at(-1)[1]
const lastBody = (spy) => JSON.parse(spy.mock.calls.at(-1)[1].body)

describe('经验压力 api 接线 · 真实 /revision /continue 路径', () => {
  it('revisionLetter → GET /revision/letter', async () => {
    const spy = spyFetch({ items: [], item_count: 0 })
    await api.revisionLetter()
    expect(lastUrl(spy)).toContain('/revision/letter')
    expect(lastOpts(spy)?.method || 'GET').toMatch(/GET|undefined/i)
  })

  it('updateLetterItem → POST /revision/letter/items/{id}', async () => {
    const spy = spyFetch({ letter: { items: [] } })
    await api.updateLetterItem('item-1', { status: 'waived', author_note: 'ok' })
    expect(lastUrl(spy)).toContain('/revision/letter/items/item-1')
    expect(lastOpts(spy).method).toBe('POST')
    expect(lastBody(spy).status).toBe('waived')
  })

  it('getSceneGrid → GET /revision/scene-grid/{seq}', async () => {
    const spy = spyFetch({ grid: null })
    await api.getSceneGrid(7)
    expect(lastUrl(spy)).toMatch(/\/revision\/scene-grid\/7/)
  })

  it('putSceneGrid → PUT /revision/scene-grid/{seq} 带六格 body', async () => {
    const spy = spyFetch({ grid: { goal: 'g' }, issues: [] })
    await api.putSceneGrid(3, {
      goal: 'g', conflict: 'c', disaster: 'd',
      reaction: 'r', dilemma: 'm', decision: 'e', source: 'author',
    })
    expect(lastUrl(spy)).toMatch(/\/revision\/scene-grid\/3/)
    expect(lastOpts(spy).method).toBe('PUT')
    expect(lastBody(spy).goal).toBe('g')
    expect(lastBody(spy).decision).toBe('e')
  })

  it('continueSnapshot → GET /continue/snapshot?seq=', async () => {
    const spy = spyFetch({ require_reread: false, acked: false })
    await api.continueSnapshot(4)
    expect(lastUrl(spy)).toContain('/continue/snapshot')
    expect(lastUrl(spy)).toContain('seq=4')
  })

  it('ackReread → POST /continue/ack-reread', async () => {
    const spy = spyFetch({ ok: true })
    await api.ackReread(5)
    expect(lastUrl(spy)).toContain('/continue/ack-reread')
    expect(lastOpts(spy).method).toBe('POST')
    expect(lastBody(spy).seq).toBe(5)
  })

  it('setRequireReread → POST /continue/require-reread', async () => {
    const spy = spyFetch({ require_reread: true })
    await api.setRequireReread(true)
    expect(lastUrl(spy)).toContain('/continue/require-reread')
    expect(lastBody(spy).enabled).toBe(true)
  })
})
