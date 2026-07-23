import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  INBOX_DECISION_KINDS,
  SESSION_CLIP_KINDS,
  buildSessionClipDraft,
  citeMaterialPayload,
  citeSelectionPayload,
  discussMaterialPayload,
  saveSessionClipAsMaterial,
  seedCiteMaterial,
  seedCiteSelection,
  seedDiscussMaterial,
} from './sessionClip.js'

describe('buildSessionClipDraft', () => {
  it('builds snippet/note draft with body + session provenance source', () => {
    const d = buildSessionClipDraft({
      text: '城墙上霜白如骨',
      kind: 'snippet',
      scopeLabel: '主编气泡',
      chapterSeq: 4,
      originLabel: '主编会话',
    })
    expect(d).not.toBeNull()
    expect(SESSION_CLIP_KINDS).toContain(d.kind)
    expect(d.kind).toBe('snippet')
    expect(d.body).toBe('城墙上霜白如骨')
    expect(d.source).toMatch(/会话摘录/)
    expect(d.source).toMatch(/主编会话/)
    expect(d.source).toMatch(/第4章/)
    expect(d.title).toBeTruthy()
  })

  it('note kind allowed; empty text → null', () => {
    expect(buildSessionClipDraft({ text: '  ' })).toBeNull()
    const n = buildSessionClipDraft({ text: '备忘一句', kind: 'note' })
    expect(n.kind).toBe('note')
    expect(n.source.length).toBeGreaterThan(0)
  })

  it('never produces inbox decision kinds', () => {
    for (const bad of INBOX_DECISION_KINDS) {
      const d = buildSessionClipDraft({ text: '别进收件箱', kind: bad })
      expect(d).not.toBeNull()
      expect(INBOX_DECISION_KINDS).not.toContain(d.kind)
      expect(SESSION_CLIP_KINDS).toContain(d.kind)
      expect(JSON.stringify(d)).not.toMatch(/needs_human|pilot_parked|promotable_lesson/)
    }
  })
})

describe('saveSessionClipAsMaterial (author clip path, no chief approval)', () => {
  it('POSTs /author/session-clips payload; never s3_add_material seed', async () => {
    const addClip = vi.fn(async (body) => ({ ok: true, id: 'mat-77', ...body }))
    const seeds = []
    const onSeed = (e) => seeds.push(e.detail)
    window.addEventListener('s3-chief-seed', onSeed)

    const saved = await saveSessionClipAsMaterial({
      text: '雨夜里的纸人',
      kind: 'snippet',
      chapterSeq: 2,
      scopeLabel: '会话',
      originLabel: '主编会话',
    }, addClip)

    window.removeEventListener('s3-chief-seed', onSeed)

    expect(addClip).toHaveBeenCalledTimes(1)
    const body = addClip.mock.calls[0][0]
    expect(body.kind).toBe('snippet')
    expect(body.body).toBe('雨夜里的纸人')
    expect(body.source).toMatch(/会话摘录/)
    expect(body.title).toBeTruthy()
    expect(body.origin_label).toBe('主编会话')
    expect(body.chapter_seq).toBe(2)
    expect(INBOX_DECISION_KINDS).not.toContain(body.kind)
    expect(saved).toMatchObject({ id: 'mat-77', kind: 'snippet' })
    expect(seeds).toEqual([])
    expect(sessionStorage.getItem('s3.chief.seed')).toBeNull()
  })

  it('rejects empty text without calling API', async () => {
    const addClip = vi.fn()
    expect(await saveSessionClipAsMaterial({ text: '  ' }, addClip)).toBeNull()
    expect(addClip).not.toHaveBeenCalled()
  })

  it('throws when API returns no id', async () => {
    const addClip = vi.fn(async () => ({ ok: true }))
    await expect(saveSessionClipAsMaterial({ text: 'x' }, addClip)).rejects.toThrow(/id/)
  })
})

describe('citeSelection / discuss / cite material', () => {
  beforeEach(() => { sessionStorage.clear() })
  afterEach(() => { sessionStorage.clear() })

  it('citeSelectionPayload introduces selection into session compose', () => {
    const p = citeSelectionPayload({ text: '半张契上的红印', scopeLabel: '会话' })
    expect(p.seedText).toMatch(/引入会话/)
    expect(p.seedText).toMatch(/半张契上的红印/)
    const t = seedCiteSelection({ text: '半张契上的红印', scopeLabel: '会话' })
    expect(t).toMatch(/引入会话/)
    expect(sessionStorage.getItem('s3.chief.seed')).toBe(t)
  })

  it('discuss names material id and title', () => {
    const p = discussMaterialPayload({
      id: 'mat-9',
      title: '霜白城墙',
      kind: 'snippet',
      source: '会话摘录 · 主编会话',
    })
    expect(p.focus.id).toBe('mat-9')
    expect(p.seedText).toMatch(/mat-9|霜白城墙/)
  })

  it('citeMaterial attaches stable material ref', () => {
    const p = citeMaterialPayload({ id: 12, title: '井底还魂', kind: 'note' }, '用在第三章钩子')
    expect(p.ref).toBe('material:12')
    expect(p.seedText).toMatch(/material:12/)
    expect(seedCiteMaterial({ id: 'm42', title: '半张契' })).toMatch(/material:m42/)
  })

  it('seedDiscussMaterial includes material identity', () => {
    const d = seedDiscussMaterial({ id: 'm42', title: '半张契', kind: 'snippet' })
    expect(d).toMatch(/m42|半张契/)
  })
})
