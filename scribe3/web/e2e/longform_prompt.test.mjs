import assert from 'node:assert/strict'
import test from 'node:test'
import { buildLongformDraftPrompt } from './longform_prompt.mjs'

test('长程正文提示只依赖当前书已批准的正典上下文，不携带旧验收书人物', () => {
  const prompt = buildLongformDraftPrompt({
    seq: 17,
    brief: '雨夜追索一封未寄出的信，结尾留下一处可行动的选择',
    minLen: 2600,
  })

  assert.match(prompt, /第17章完整正文草稿/)
  assert.match(prompt, /2600字以上/)
  assert.match(prompt, /当前作品已批准的章计划、世界状态、知识帧与前章定稿/)
  assert.doesNotMatch(prompt, /沈砚|灰契|超自然机制/)
})
