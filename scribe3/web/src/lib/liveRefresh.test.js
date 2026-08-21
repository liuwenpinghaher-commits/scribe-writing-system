import { describe, expect, it } from 'vitest'
import {
  liveTouchesChapter,
  liveTouchesTable,
  parseChapterSeqFromLiveId,
} from './liveRefresh.js'
import {
  shouldShowVolumeOrganizeHint,
  shouldShowCrossArcVolumeHint,
  volumeReviewPlain,
  VOLUME_SOFT_HINT_DEFAULT_N,
} from './volumeSoftHint.js'

describe('liveRefresh', () => {
  it('table-only chapter refresh', () => {
    expect(liveTouchesChapter({ table: 'chapter' }, 3)).toBe(true)
    expect(liveTouchesChapter({ table: 'promise' }, 3)).toBe(false)
  })

  it('id-aware skips other chapters', () => {
    expect(liveTouchesChapter({ table: 'chapter', id: 'chapter:5' }, 3)).toBe(false)
    expect(liveTouchesChapter({ table: 'chapter', id: 'chapter:3' }, 3)).toBe(true)
  })

  it('parseChapterSeqFromLiveId', () => {
    expect(parseChapterSeqFromLiveId('chapter:12')).toBe(12)
    expect(parseChapterSeqFromLiveId('x')).toBe(null)
  })

  it('liveTouchesTable', () => {
    expect(liveTouchesTable({ table: 'chapter' }, ['chapter', 'promise'])).toBe(true)
    expect(liveTouchesTable({ table: 'idea' }, ['chapter'])).toBe(false)
    expect(liveTouchesTable({ table: '_init' }, ['chapter'])).toBe(false)
  })

  it('accepts detail.tb alias', () => {
    expect(liveTouchesTable({ tb: 'promise' }, ['promise'])).toBe(true)
    expect(liveTouchesChapter({ tb: 'chapter', id: 'chapter:3' }, 3)).toBe(true)
    expect(liveTouchesChapter({ tb: 'chapter', id: 'chapter:9' }, 3)).toBe(false)
  })
})

describe('volumeSoftHint', () => {
  it('shows only when unassigned >= threshold and not dismissed', () => {
    expect(shouldShowVolumeOrganizeHint({ unassignedCount: 11, threshold: 12 })).toBe(false)
    expect(shouldShowVolumeOrganizeHint({ unassignedCount: 12, threshold: 12 })).toBe(true)
    expect(shouldShowVolumeOrganizeHint({ unassignedCount: 20, dismissed: true })).toBe(false)
    expect(VOLUME_SOFT_HINT_DEFAULT_N).toBe(12)
  })
})

describe('crossArcVolumeHint', () => {
  it('shows when overdue >= 1', () => {
    expect(shouldShowCrossArcVolumeHint({ overduePromiseCount: 0 })).toBe(false)
    expect(shouldShowCrossArcVolumeHint({ overduePromiseCount: 1 })).toBe(true)
    expect(shouldShowCrossArcVolumeHint({ overduePromiseCount: 3, dismissed: true })).toBe(false)
  })
})

describe('volumeReviewPlain', () => {
  it('does not dump machine JSON', () => {
    const raw = {
      seqs: [1, 2, 3, 4],
      overdue_count: 0,
      motifs_no_echo: [{ name: '冷与烫' }, { name: '囚笼与摇篮' }],
    }
    const text = volumeReviewPlain(raw)
    expect(text).toContain('冷与烫')
    expect(text).not.toContain('seqs')
    expect(text).not.toContain('motif_id')
  })
  it('hides when there is nothing to say', () => {
    expect(volumeReviewPlain({ seqs: [1], overdue_count: 0, motifs_no_echo: [] })).toBe('')
  })
})
