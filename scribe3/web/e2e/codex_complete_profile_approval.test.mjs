import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('完整角色档案真人旅程给 Hermes 的工具检索与首次审批足够的真实等待窗口', async () => {
  const source = await readFile(new URL('./codex_complete_profile_approval.mjs', import.meta.url), 'utf8')
  assert.match(source, /async function waitFor\(read, predicate, label, attempts = 180\)/)
  assert.doesNotMatch(source, /async function waitFor\(read, predicate, label, attempts = 40\)/)
})
