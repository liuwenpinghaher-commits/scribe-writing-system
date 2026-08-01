import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

test('章节审批使用统一的主编 Run 等待器，不能在发送后盲轮询', async () => {
  const source = await readFile(new URL('./material_import_author_consumption.mjs', import.meta.url), 'utf8')

  assert.match(source, /import \{ approveAllPending, chiefSay \} from '\.\/author_decisions\.mjs'/)
  assert.match(source, /await chiefSay\(page,[\s\S]*s3_add_chapter/)
  assert.doesNotMatch(source, /const composer = page\.locator\('textarea\[placeholder\^="就当前内容问主编"\]'\)/)
})

test('素材真人旅程不把长期 SSE 连接误判为页面尚未可用', async () => {
  const source = await readFile(new URL('./material_import_author_consumption.mjs', import.meta.url), 'utf8')

  assert.doesNotMatch(source, /page\.goto\(BASE, \{ waitUntil: 'networkidle'/)
  assert.match(source, /page\.goto\(BASE, \{ waitUntil: 'domcontentloaded'/)
})

test('素材旅程把实际审批 Run 身份写入 artifact，供总控核验 TokenPlan 审计', async () => {
  const source = await readFile(new URL('./material_import_author_consumption.mjs', import.meta.url), 'utf8')

  assert.match(source, /runIds:/)
  assert.match(source, /chapterRunId/)
})

test('可显式复用既有作品与章节，补齐同一本长程验收的作者手动素材消费', async () => {
  const source = await readFile(new URL('./material_import_author_consumption.mjs', import.meta.url), 'utf8')

  assert.match(source, /const WORK = process\.env\.E2E_WORK \|\| null/)
  assert.match(source, /const CHAPTER_SEQ = Number\(process\.env\.E2E_CHAPTER_SEQ \|\| 1\)/)
  assert.match(source, /if \(!WORK\) \{[\s\S]*?resolveWorkSlugByExactTitle/)
  assert.match(source, /\[data-work-slug="\$\{work\}"\]/)
  assert.match(source, /Number\(row\.chapter\) === CHAPTER_SEQ/)
})
