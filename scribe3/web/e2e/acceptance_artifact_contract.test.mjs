import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

for (const script of [
  'codex_complete_profile_approval.mjs',
  'codex_complete_faction_approval.mjs',
  'codex_complete_simple_registry_approval.mjs',
  'graph_semantics_approval.mjs',
]) {
  test(`${script} 向全量总控写入结构化结果`, async () => {
    const source = await readFile(new URL(`./${script}`, import.meta.url), 'utf8')

    assert.match(source, /E2E_RESULT_FILE/)
    assert.match(source, /writeFile/)
  })
}

test('角色全字段旅程失败时仍保留已创建的 work 与 Run ID 供总控诊断', async () => {
  const source = await readFile(new URL('./codex_complete_profile_approval.mjs', import.meta.url), 'utf8')

  assert.match(source, /observedWork/)
  assert.match(source, /observedRunIds/)
})
