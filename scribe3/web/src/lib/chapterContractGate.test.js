/**
 * Pure node runner:
 *   node --experimental-vm-modules web/src/lib/chapterContractGate.test.js
 *   or: node web/src/lib/chapterContractGate.test.js
 */
import { pathToFileURL } from 'url'
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

let test, assert
try {
  ;({ test } = await import('node:test'))
  assert = await import('node:assert/strict')
} catch {
  assert = await import('node:assert/strict')
  test = async (name, fn) => {
    try {
      await fn()
      console.log(`ok - ${name}`)
    } catch (e) {
      console.error(`FAIL - ${name}`, e)
      process.exitCode = 1
    }
  }
}

const mod = await import(pathToFileURL(join(__dirname, 'chapterContractGate.js')).href)
const {
  evaluateChapterContract,
  contractNeedsAttention,
  contractSoftSummary,
  countBeatTexts,
  MIN_BEAT_TEXTS,
} = mod

await test('empty chapter → B1 B2 B3 errors', () => {
  const r = evaluateChapterContract({})
  assert.equal(r.hasError, true)
  assert.equal(r.synopsisOk, false)
  assert.equal(r.beatsOk, false)
  assert.equal(r.sceneTruthOk, false)
  const ids = r.issues.map((i) => i.id)
  assert.ok(ids.includes('missingSynopsis'))
  assert.ok(ids.includes('missingBeats'))
  assert.ok(ids.includes('missingSceneTruth'))
  assert.equal(contractNeedsAttention({}), true)
})

await test('full contract → no error', () => {
  const ch = {
    synopsis: '甲'.repeat(50),
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '乙'.repeat(50),
  }
  const r = evaluateChapterContract(ch)
  assert.equal(r.hasError, false)
  assert.equal(contractNeedsAttention(ch), false)
})

await test('short synopsis is warn not error if non-empty', () => {
  const r = evaluateChapterContract({
    synopsis: '短',
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '丙'.repeat(50),
  })
  assert.equal(r.hasError, false)
  assert.ok(r.issues.some((i) => i.id === 'shortSynopsis' && i.level === 'warn'))
})

await test('two beats → missingBeats error', () => {
  const r = evaluateChapterContract({
    synopsis: '甲'.repeat(50),
    beats: [{ text: '一' }, { text: '二' }],
    scene_truth: '乙'.repeat(50),
  })
  assert.equal(r.beatCount, 2)
  assert.ok(r.issues.some((i) => i.id === 'missingBeats'))
})

await test('countBeatTexts ignores empty', () => {
  assert.equal(countBeatTexts([{ text: '' }, { text: 'x' }, '  ', 'y']), 2)
  assert.equal(MIN_BEAT_TEXTS, 3)
})

await test('contractSoftSummary lists errors', () => {
  const s = contractSoftSummary({})
  assert.ok(s.includes('大纲'))
})

console.log('chapterContractGate tests done')
