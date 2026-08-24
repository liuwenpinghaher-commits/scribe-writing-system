import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  focusChiefWithSeed,
  seedChiefCodexWrite,
  seedChiefCodexCreate,
  seedChiefNarrativeWrite,
  seedChiefReorderChapters,
  seedChiefDeleteVolume,
  seedBookPortraitIntent,
  seedChapterOutline,
  seedChapterBeats,
  seedChapterDeduce,
  SCAFFOLD_FORBID_SAVE,
} from './chiefSeed.js'
import { shouldUseHermesRun, assembleWorldWriteInstructions } from './hermesRunIntent.js'

describe('chiefSeed helpers', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })
  afterEach(() => {
    sessionStorage.clear()
  })

  it('seedBookPortraitIntent 派 s3-right-tab=chief 且点名 s3_set_intent', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    const t = seedBookPortraitIntent()
    expect(t).toMatch(/s3_set_intent/)
    expect(t).toMatch(/s3_get_intent/)
    expect(tabs).toEqual(['chief'])
  })

  it('focusChiefWithSeed writes storage, seed event, and right-tab focus', () => {
    const seeds = []
    const tabs = []
    const onSeed = (e) => seeds.push(e.detail)
    const onTab = (e) => tabs.push(e.detail)
    window.addEventListener('s3-chief-seed', onSeed)
    window.addEventListener('s3-right-tab', onTab)

    const text = focusChiefWithSeed('hello chief')
    expect(text).toBe('hello chief')
    expect(sessionStorage.getItem('s3.chief.seed')).toBe('hello chief')
    expect(seeds).toEqual(['hello chief'])
    expect(tabs).toEqual(['chief'])

    window.removeEventListener('s3-chief-seed', onSeed)
    window.removeEventListener('s3-right-tab', onTab)
  })

  it('完整设定更正使用注册表驱动的待批工具并聚焦主编', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    const t = seedChiefCodexWrite('chars', { name: '季棠', aliases: ['小棠'], abilities: ['读唇'] }, '补外貌')
    expect(t).toMatch(/季棠/)
    expect(t).toMatch(/补外貌/)
    expect(t).toMatch(/s3_generate_codex/)
    expect(t).toMatch(/禁止把薄字段预填/)
    expect(t).not.toMatch(/aliases":/)
    expect(sessionStorage.getItem('s3.chief.seed')).toBe(t)
    expect(tabs).toContain('chief')
  })

  it('seedChiefNarrativeWrite focuses chief', () => {
    const tabs = []
    window.addEventListener('s3-right-tab', (e) => tabs.push(e.detail))
    seedChiefNarrativeWrite('outline', '第 1 章大纲', '请更新')
    expect(tabs).toContain('chief')
    expect(sessionStorage.getItem('s3.chief.seed')).toMatch(/第 1 章大纲/)
  })

  it('production structure/codex seeds route to Hermes Run', () => {
    const samples = [
      seedChiefCodexCreate('character', { name: '甲' }),
      seedChiefReorderChapters('vol1', [3, 1, 2]),
      seedChiefDeleteVolume('vol1', '卷一'),
      seedChiefNarrativeWrite('volume', '新建分卷「潮」', '请用 s3_add_volume 创建卷'),
    ]
    for (const s of samples) {
      expect(shouldUseHermesRun(s)).toBe(true)
    }
  })

  it('outline/beats/deduce seeds name plan tool and forbid scaffold save', () => {
    const o = seedChapterOutline(3, '旧债上门')
    expect(o).toMatch(/s3_generate_stage/)
    expect(o).toMatch(/stage=duty/)
    expect(o).toMatch(/s3_save_chapter/)
    expect(o).toContain('禁止用 s3_save_chapter')
    expect(shouldUseHermesRun(o)).toBe(true)

    const b = seedChapterBeats(2, [{ text: '抵达' }, { text: '对峙' }])
    expect(b).toMatch(/s3_generate_stage/)
    expect(b).toMatch(/stage=design/)
    expect(b).toMatch(/s3_patch_contract/)
    expect(b).toContain('禁止用 s3_save_chapter')
    expect(shouldUseHermesRun(b)).toBe(true)

    const d = seedChapterDeduce(1, '后室有人先到')
    expect(d).toMatch(/s3_generate_stage/)
    expect(d).toMatch(/stage=deduce/)
    expect(d).toContain('禁止用 s3_save_chapter')
    expect(shouldUseHermesRun(d)).toBe(true)

    expect(SCAFFOLD_FORBID_SAVE).toMatch(/s3_save_chapter/)
  })

  it('volume scope narrative seed names s3_patch_volume when hint omits tool', () => {
    const t = seedChiefNarrativeWrite('volume', '分卷甲', '请把卷纲写成：潮声将至')
    expect(t).toMatch(/s3_patch_volume/)
    expect(shouldUseHermesRun(t)).toBe(true)
  })

  it('assembleWorldWriteInstructions concatenates suffix when phase cleared', () => {
    const s = assembleWorldWriteInstructions({
      chapter: 4,
      instructionSuffix: '域纪律(章设计):s3_generate_stage',
      phase: 'outline',
    })
    expect(s).toMatch(/scribe3/)
    expect(s).toMatch(/域纪律/)
    expect(s).toMatch(/s3_generate_stage/)
    // phase 不进入 base 业务阶段行（world_write 清空）
    expect(s).not.toMatch(/当前阶段:outline/)
  })
})
