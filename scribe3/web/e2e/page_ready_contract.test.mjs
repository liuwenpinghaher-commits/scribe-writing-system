import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

for (const script of [
  'codex_complete_profile_approval.mjs',
  'deduce_preview_approval.mjs',
]) {
  test(`${script} 不把常驻 SSE 误判为页面未就绪`, async () => {
    const source = await readFile(new URL(`./${script}`, import.meta.url), 'utf8')

    assert.doesNotMatch(source, /page\.goto\([^\n]+waitUntil: 'networkidle'/)
    assert.match(source, /waitUntil: 'domcontentloaded'/)
  })
}
