import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'

afterEach(() => { vi.restoreAllMocks() })

// 捕获最近一次 fetch 的请求体(JSON 解析)。
function spyFetch() {
  const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true, status: 200, json: async () => ({ ok: true }),
  })
  return spy
}
const lastBody = (spy) => JSON.parse(spy.mock.calls.at(-1)[1].body)

// P1-3:前端行数据用 `kind`,后端 PromIn 读 `promise_kind`。若整行回传(编辑文案)时不带
// promise_kind,后端默认 'promise' 会把 red_herring 静默重置。api 层须把 kind 转译为 promise_kind。
describe('伏笔 kind→promise_kind 转译(P1-3)', () => {
  it('editPromise 改文案时保留 red_herring:请求体带 promise_kind', async () => {
    const spy = spyFetch()
    await api.editPromise('promise:abc', { id: 'promise:abc', text: '改后的伏笔文案', kind: 'red_herring' })
    const body = lastBody(spy)
    expect(body.promise_kind).toBe('red_herring')   // 不再被默认 'promise' 重置
    expect(body.text).toBe('改后的伏笔文案')
  })

  it('addPromiseNew 新建障眼法:请求体带 promise_kind', async () => {
    const spy = spyFetch()
    await api.addPromiseNew({ text: '新伏笔', setup_chapter: 1, tier: 'chapter', kind: 'red_herring' })
    expect(lastBody(spy).promise_kind).toBe('red_herring')
  })

  it('无 kind 字段时不注入 promise_kind(后端默认 promise)', async () => {
    const spy = spyFetch()
    await api.editPromise('promise:abc', { id: 'promise:abc', text: '只改文案' })
    expect(lastBody(spy)).not.toHaveProperty('promise_kind')
  })
})
