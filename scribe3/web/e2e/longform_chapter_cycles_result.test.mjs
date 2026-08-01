import assert from 'node:assert/strict'
import test from 'node:test'
import { chapterSequence, buildChapterCycleReport } from './longform_chapter_cycles_result.mjs'
import { readFileSync } from 'node:fs'

test('长程章节控制器只生成闭区间内的连续章节号', () => {
  assert.deepEqual(chapterSequence(2, 4), [2, 3, 4])
  assert.throws(() => chapterSequence(0, 4), /1/)
  assert.throws(() => chapterSequence(4, 3), /不能小于/)
})

test('长程章节控制器拒绝任何未显式成功、章节号漂移或缺 artifact 的子旅程', () => {
  const complete = buildChapterCycleReport({
    requested: [2, 3],
    steps: [
      { seq: 2, exitCode: 0, artifact: '/tmp/ch2.json', result: { ok: true, chapter_seq: 2 } },
      { seq: 3, exitCode: 0, artifact: '/tmp/ch3.json', result: { ok: true, chapter_seq: 3 } },
    ],
  })
  assert.equal(complete.ok, true)

  const incomplete = buildChapterCycleReport({
    requested: [2, 3],
    steps: [
      { seq: 2, exitCode: 0, artifact: '/tmp/ch2.json', result: { ok: true, chapter_seq: 2 } },
      { seq: 3, exitCode: 0, artifact: '/tmp/ch3.json', result: { ok: true, chapter_seq: 2 } },
    ],
  })
  assert.equal(incomplete.ok, false)
  assert.deepEqual(incomplete.failed_sequences, [3])
})

test('长程控制器在写显式汇总 artifact 前创建其父目录', () => {
  const source = readFileSync(new URL('./longform_chapter_cycles.mjs', import.meta.url), 'utf8')
  assert.match(source, /await mkdir\(dirname\(RESULT_FILE\), \{ recursive: true \}\)/)
})
