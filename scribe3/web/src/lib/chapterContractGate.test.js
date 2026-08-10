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
  parseOutlineStakes,
  executionSoftSummary,
  mergedSoftBannerSummary,
  shouldShowMergedSoftBanner,
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

await test('high pressure missing stakes → warn not error', () => {
  const syn = '压力级:4\nchapter_role:高压\n' + '甲'.repeat(40)
  const r = evaluateChapterContract({
    synopsis: syn,
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '乙'.repeat(50),
  })
  assert.equal(r.hasError, false)
  assert.equal(r.stakesOk, false)
  assert.ok(r.issues.some((i) => i.id === 'missingOutlineStakes' && i.level === 'warn'))
  const stakes = parseOutlineStakes(syn)
  assert.equal(stakes.warning, 'missing_outline_stakes')
  assert.equal(stakes.highPressure, true)
})

await test('high pressure with stakes → no stakes warning', () => {
  const syn = '压力级:5\nchapter_role:推进\nstakes: 铜钱易主则功名尽\n' + '甲'.repeat(20)
  const r = evaluateChapterContract({
    synopsis: syn,
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '乙'.repeat(50),
  })
  assert.equal(r.stakesOk, true)
  assert.ok(!r.issues.some((i) => i.id === 'missingOutlineStakes'))
  assert.ok(parseOutlineStakes(syn).present)
})

await test('low pressure no stakes → no stakes warning', () => {
  const r = evaluateChapterContract({
    synopsis: '压力级:2\n' + '甲'.repeat(40),
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '乙'.repeat(50),
  })
  assert.ok(!r.issues.some((i) => i.id === 'missingOutlineStakes'))
  assert.equal(r.stakesOk, true)
})

await test('executionSoftSummary and merged banner', () => {
  const soft = {
    soft_fulfill: { ok_soft: false, gaps: ['dialogue_low'], quotes: 1, severity: 'advisory' },
    drift: { drift: false },
  }
  const exec = executionSoftSummary(soft)
  assert.ok(exec.includes('对白'))
  const ch = { synopsis: '', beats: [], scene_truth: '' }
  const merged = mergedSoftBannerSummary(ch, soft)
  assert.ok(merged.includes('章前契约') || merged.includes('大纲'))
  assert.ok(merged.includes('执行对照'))
  assert.equal(shouldShowMergedSoftBanner(ch, soft), true)
  assert.equal(shouldShowMergedSoftBanner({
    synopsis: '甲'.repeat(50),
    beats: [{ text: '一' }, { text: '二' }, { text: '三' }],
    scene_truth: '乙'.repeat(50),
  }, { soft_fulfill: { ok_soft: true }, drift: { drift: false } }), false)
})

console.log('chapterContractGate tests done')
