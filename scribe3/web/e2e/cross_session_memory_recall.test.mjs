import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'
import { consumesEbbLeveragePreference } from './memory_preference_quality.mjs'

test('跨会话偏好质量闸接受自然的退潮借势表达，但拒绝只有退潮背景的成稿', () => {
  assert.equal(consumesEbbLeveragePreference('潮退到第三道石坎，潮票Alpha借那一线回溜，把缆绳斜抛过沉船桅。'), true)
  assert.equal(consumesEbbLeveragePreference('潮退半篙，缆桩露泥。潮票Alpha趁退溜踏湿板下桩，反手扣住溺儿。'), true)
  assert.equal(consumesEbbLeveragePreference('潮退半篙，缆绳吃松。潮票Alpha借回水一拧，将溺者从桩缝里拖出。'), true)
  assert.equal(consumesEbbLeveragePreference('潮票Alpha贴身未热，先趁退潮借水。黑泥滩上，缆桩吐出断绳。'), true)
  assert.equal(consumesEbbLeveragePreference('潮退半篙，缆桩露泥。潮票Alpha踏湿板下桩，反手扣住溺儿。'), false)
  assert.equal(consumesEbbLeveragePreference('潮票Alpha借回溜跃下跳板，潮退半篙，缆桩露泥。'), false)
})

test('跨会话验收在轮询结果未定义时保留原始失败标签', async () => {
  const script = await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url), 'utf8')
  assert.match(script, /String\(JSON\.stringify\(value\)\)\.slice\(0, 1000\)/)
})

test('跨会话真人旅程不把长期 SSE 连接误判为页面尚未可用', async () => {
  const source = await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url), 'utf8')

  assert.doesNotMatch(source, /page\.goto\([^\n]*waitUntil: 'networkidle'/)
  assert.match(source, /page\.goto\([^\n]*waitUntil: 'domcontentloaded'/)
})

test('跨会话真人旅程允许新书写作壳先挂载，再等待后续可见交互控件', async () => {
  const source = await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url), 'utf8')

  assert.match(source, /locator\('\[data-testid="four-col"\]'\)\.waitFor\(\{ state: 'attached'/)
  assert.match(source, /chapterButton\.waitFor\(\{ state: 'visible'/)
  assert.match(source, /draftTab\.waitFor\(\{ state: 'visible'/)
})

test('跨会话工件记录执行脚本哈希，拒绝用旧脚本结果冒充当前验收', async () => {
  const source = await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url), 'utf8')

  assert.match(source, /harness_source_sha256/)
  assert.match(source, /createHash\('sha256'\)/)
})

test('跨会话工件从已持久化 assistant trace 提取真实 TokenPlan 请求与用量证据', async () => {
  const source = await readFile(new URL('./cross_session_memory_recall.mjs', import.meta.url), 'utf8')

  assert.match(source, /toDirectQwenEvidence/)
  assert.match(source, /model_evidence/)
  assert.match(source, /second\.assistant\.trace/)
})
