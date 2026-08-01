import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

test('作者裁决恢复旅程逐项等待 UI 提交响应并回读十维结果', () => {
  const source = readFileSync(new URL('./resume_quality_author_verdicts.mjs', import.meta.url), 'utf8')

  assert.match(source, /waitForResponse/)
  assert.match(source, /\/quality\/author-judgment/)
  assert.match(source, /AUTHOR_VERDICTS_UI_SUBMITTED/)
  assert.match(source, /dimensions\?\.every\(\(item\) => item\.author/)
})
