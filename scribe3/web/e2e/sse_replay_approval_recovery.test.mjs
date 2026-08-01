import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('SSE 重放旅程在审批请求出现后刷新，并只用页面批准恢复写入', async () => {
  const source = await readFile(new URL('./sse_replay_approval_recovery.mjs', import.meta.url), 'utf8')

  assert.match(source, /approval-request-card/)
  assert.match(source, /await page\.reload\(\{ waitUntil: 'domcontentloaded' \}\)/)
  assert.match(source, /await approveAllPending\(page/)
  assert.match(source, /\/ai\/runs\/\$\{encodeURIComponent\(runId\)\}\/trace/)
  assert.match(source, /value\?\.status === 'completed'/)
  assert.doesNotMatch(source, /fetch\([^\n]+method:\s*['"]POST['"]/)
})
