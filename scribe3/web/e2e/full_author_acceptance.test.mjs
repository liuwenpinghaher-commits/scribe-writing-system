import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('全量短链总控覆盖字段、图谱、素材、记忆、可靠性和质量决策', async () => {
  const source = await readFile(new URL('./full_author_acceptance.mjs', import.meta.url), 'utf8')

  for (const id of [
    'profile', 'faction', 'registry-item', 'registry-term', 'registry-rule',
    'graph', 'deduce', 'materials', 'memory', 'stream-recovery', 'quality-reference',
  ]) assert.match(source, new RegExp(`id: '${id}'`))
  assert.match(source, /buildAcceptanceReport/)
  assert.match(source, /collectHermesRunEvidence/)
  assert.match(source, /waitForHermesRunEvidence/)
  assert.match(source, /E2E_RESULT_FILE/)
  assert.match(source, /registry-rule[^\n]*E2E_KIND: 'world_rule'/)
  assert.doesNotMatch(source, /book_[a-f0-9]{8}/)
})

test('五万字长程只在显式开关下执行，短链不能冒充长程完成', async () => {
  const source = await readFile(new URL('./full_author_acceptance.mjs', import.meta.url), 'utf8')

  assert.match(source, /E2E_INCLUDE_LONG/)
  assert.match(source, /longform-50k/)
  assert.match(source, /not_run/)
})

test('总控同时从 run_ids 与 previewRunId 等字段读取 Hermes Run 证据', async () => {
  const source = await readFile(new URL('./full_author_acceptance.mjs', import.meta.url), 'utf8')

  assert.match(source, /\/run_\?ids\?\$\/i/)
})
