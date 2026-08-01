import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('长程补章能定位当前手稿序号，并在 UI 新建章后完成作者审批再回读', async () => {
  const source = await readFile(new URL('./hq_wordcount_push.mjs', import.meta.url), 'utf8')

  assert.match(source, /new RegExp\(`\^\$\{seq\}\\\\s\+\|第/)
  assert.match(source, /await approveAllPending\(p\)/)
  assert.match(source, /chapter_count \|\| 0\) <= beforeCount/)
  assert.match(source, /aria-pressed/)
  assert.match(source, /manuscript-directory/)
  assert.match(source, /E2E_RESULT_FILE/)
  assert.match(source, /run_ids/)
  assert.match(source, /in_progress/)
})

test('长程补字数在退出前必须运行逐章只读审计，不能把字数命中当作完整验收通过', async () => {
  const source = await readFile(new URL('./hq_wordcount_push.mjs', import.meta.url), 'utf8')

  assert.match(source, /collectLongformAcceptanceInput/)
  assert.match(source, /buildLongformAcceptanceReport/)
  assert.match(source, /longform_report/)
  assert.match(source, /longform_report\.ok/)
})

test('长程补字数在草稿阶段填入后必须显式采用为正文，不能把未保存草稿计入字数', async () => {
  const source = await readFile(new URL('./hq_wordcount_push.mjs', import.meta.url), 'utf8')

  assert.match(source, /adoptDraftAsFinal/)
  assert.match(source, /acc\.kind === 'stage'/)
})
