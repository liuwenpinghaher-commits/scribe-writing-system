import { describe, it, expect, vi, afterEach } from 'vitest'
import { api } from '../api.js'
import { buildPropositionCategory } from '../codexTree.js'

afterEach(() => { vi.restoreAllMocks() })

// 捕获最近一次 fetch 的 [url, opts]。
function spyFetch() {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true, status: 200, json: async () => ({ ok: true }),
  })
}
const lastUrl = (spy) => spy.mock.calls.at(-1)[0]
const lastOpts = (spy) => spy.mock.calls.at(-1)[1]
const lastBody = (spy) => JSON.parse(spy.mock.calls.at(-1)[1].body)

// ═══ 批D 件1:命题 supersede/forget api wrapper ═══
describe('批D 件1 · 命题 supersede/forget wrapper', () => {
  it('supersedeFact → POST /facts/supersede,带 entity_id/attribute/value/since_chapter/secret', async () => {
    const spy = spyFetch()
    await api.supersedeFact({ entity_id: 'role:焦三', attribute: '职业', value: '医官', since_chapter: 5, secret: true })
    expect(lastUrl(spy)).toContain('/facts/supersede')
    expect(lastOpts(spy).method).toBe('POST')
    const b = lastBody(spy)
    expect(b.entity_id).toBe('role:焦三')
    expect(b.attribute).toBe('职业')
    expect(b.value).toBe('医官')
    expect(b.since_chapter).toBe(5)
    expect(b.secret).toBe(true)
  })

  it('forgetKnowledge → POST /knowledge/forget,带 knower_id/proposition_id/until_chapter', async () => {
    const spy = spyFetch()
    await api.forgetKnowledge({ knower_id: 'reader', proposition_id: 'fact:abc123', until_chapter: 8 })
    expect(lastUrl(spy)).toContain('/knowledge/forget')
    expect(lastOpts(spy).method).toBe('POST')
    const b = lastBody(spy)
    expect(b.knower_id).toBe('reader')
    expect(b.proposition_id).toBe('fact:abc123')
    expect(b.until_chapter).toBe(8)
  })

  it('命题写操作 HTTP 500 应 reject(res.ok 检查)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: 'x' }) })
    await expect(api.supersedeFact({ entity_id: 'role:a', attribute: 'b', value: 'c', since_chapter: 1 }))
      .rejects.toThrow('HTTP 500')
  })
})

// ═══ 批D 件2:角色关系 wrapper ═══
describe('批D 件2 · character_relation wrapper', () => {
  it('characterRelations(ch) → GET /character-relations?chapter=', async () => {
    const spy = spyFetch()
    await api.characterRelations(9999)
    expect(lastUrl(spy)).toContain('/character-relations')
    expect(lastUrl(spy)).toContain('chapter=9999')
  })

  it('characterRelations() 无章参数 → GET /character-relations(不带 chapter)', async () => {
    const spy = spyFetch()
    await api.characterRelations()
    expect(lastUrl(spy)).toContain('/character-relations')
    expect(lastUrl(spy)).not.toContain('chapter=')
  })

  it('addCharacterRelation → POST /character-relations,带 src/dst/relation/since_chapter', async () => {
    const spy = spyFetch()
    await api.addCharacterRelation({ src: 'role:焦三', dst: 'role:单嫣', relation: '师徒', since_chapter: 2, note: 'x' })
    expect(lastUrl(spy)).toContain('/character-relations')
    expect(lastOpts(spy).method).toBe('POST')
    const b = lastBody(spy)
    expect(b.src).toBe('role:焦三')
    expect(b.dst).toBe('role:单嫣')
    expect(b.relation).toBe('师徒')
    expect(b.since_chapter).toBe(2)
  })

  it('evolveRelation → POST /character-relations/evolve', async () => {
    const spy = spyFetch()
    await api.evolveRelation({ src: 'role:焦三', dst: 'role:单嫣', relation: '仇敌', since_chapter: 9 })
    expect(lastUrl(spy)).toContain('/character-relations/evolve')
    expect(lastOpts(spy).method).toBe('POST')
    expect(lastBody(spy).relation).toBe('仇敌')
  })

  it('endRelation → POST /character-relations/end,带 until_chapter', async () => {
    const spy = spyFetch()
    await api.endRelation({ src: 'role:焦三', dst: 'role:单嫣', until_chapter: 12 })
    expect(lastUrl(spy)).toContain('/character-relations/end')
    expect(lastOpts(spy).method).toBe('POST')
    expect(lastBody(spy).until_chapter).toBe(12)
  })
})

// ═══ 批D 件1:项目树命题分类注入(纯函数) ═══
describe('批D 件1 · buildPropositionCategory 注入', () => {
  it('公开命题:叶 label 含 实体·属性 = 值,ref=local,无 secret 角标', () => {
    const cat = buildPropositionCategory([
      { id: 'fact:a1', entity: 'role:焦三', attribute: '年龄', is_secret: false, value: '三十' },
    ])
    expect(cat.type).toBe('codex_category')
    expect(cat.ref).toBe('proposition')
    expect(cat.label).toBe('命题')
    expect(cat.badges[0].value).toBe(1)
    const leaf = cat.children[0]
    expect(leaf.id).toBe('proposition:a1')
    expect(leaf.type).toBe('proposition')
    expect(leaf.ref).toBe('a1')
    expect(leaf.label).toContain('焦三')
    expect(leaf.label).toContain('年龄')
    expect(leaf.label).toContain('三十')
    expect(leaf.badges).toBeUndefined()
  })

  it('私密命题:值被后端屏蔽(value=null),叶不露值、带 secret 角标', () => {
    const cat = buildPropositionCategory([
      { id: 'fact:s9', entity: 'role:单嫣', attribute: '真实身份', is_secret: true, value: null },
    ])
    const leaf = cat.children[0]
    expect(leaf.badges?.[0]?.kind).toBe('secret')
    expect(leaf.label).not.toContain('null')
    expect(leaf.label).toContain('真实身份')
  })

  it('空/无输入 → 空分类(count 0)', () => {
    expect(buildPropositionCategory([]).children).toHaveLength(0)
    expect(buildPropositionCategory(null).badges[0].value).toBe(0)
  })
})
