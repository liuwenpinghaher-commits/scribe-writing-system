import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('并发审批验收必须由两个页面同时点击同一待批卡，并只读回查正典', async () => {
  const source = await readFile(new URL('./concurrent_approval_conflict.mjs', import.meta.url), 'utf8')

  assert.match(source, /await Promise\.all\(\[\s*approve\.click\(\),\s*approvePeer\.click\(\),\s*\]\)/s)
  assert.match(source, /await peer\.reload\(\{ waitUntil: 'domcontentloaded' \}\)/)
  assert.match(source, /\/ai\/runs\/\$\{encodeURIComponent\(runId\)\}\/trace/)
  assert.match(source, /\/entities\?work=\$\{encodeURIComponent\(work\)\}/)
  assert.match(source, /\/characters\/\$\{encodeURIComponent\(NAME\)\}/)
  assert.match(source, /assert\(canonicalCount === 1/)
  assert.match(source, /already_resolved === true/)
  assert.doesNotMatch(source, /fetch\([^\n]+method:\s*['"]POST['"]/)
})
