import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { closeBrowserWithin } from './lib.mjs'

test('浏览器关闭卡住时在界定时间内返回失败状态，避免真人验收永远不落工件', async () => {
  const started = Date.now()
  const result = await closeBrowserWithin({ close: () => new Promise(() => {}) }, { timeoutMs: 20 })

  assert.equal(result.closed, false)
  assert.ok(Date.now() - started < 200, '关闭超时必须有界，不能阻塞验收进程')
})

test('浏览器正常关闭时保留成功状态', async () => {
  let calls = 0
  const result = await closeBrowserWithin({ close: async () => { calls += 1 } }, { timeoutMs: 20 })

  assert.equal(result.closed, true)
  assert.equal(calls, 1)
})

test('打开作品以 DOM 与具体写作壳就绪为准，不等待永不静止的 SSE networkidle', async () => {
  const source = await readFile(new URL('./lib.mjs', import.meta.url), 'utf8')
  const openBook = source.slice(source.indexOf('export async function openBook'))

  assert.match(openBook, /waitUntil:\s*'domcontentloaded'/)
  assert.match(openBook, /\[data-testid="four-col"\]/)
  assert.doesNotMatch(openBook, /waitUntil:\s*'networkidle'/)
})
