// CX-Task 7:势力(faction)设定库元数据驱动渲染 + 关系区。
// 覆盖计划任务7 Step1 失败测试清单的 ①②③④⑤⑥(详见
// docs/superpowers/plans/2026-07-14-codex-layer-redesign.md Task 7):
//   ① 拉 GET /codex-schema/faction 后按元数据渲染表单,不再读硬编码 fieldMap
//   ② array<object> 字段(如关键人物)渲染可增删行的子表
//   ③ object 字段(如组织结构)渲染嵌套字段组
//   ④ secret_capable 字段渲染「限知」开关;开启时值显示掩码,且掩码哨兵不会被当真值回写
//   ⑤ 元数据拉取失败 → fallback 到旧 fieldMap(不白屏)
//   ⑥ 势力详情页「关系」区:列出 entity_relation(双方认知并排;truth 不显示除非 reveal)
//
// 仅 mock `../api`(等价于 mock fetch——CodexView.jsx/CodexDetail.jsx 的唯一网络出口都是它),
// 不碰真实后端/真实 fetch,与仓内既有 __tests__/codex-lifecycle-delete.test.jsx 同款约定。
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DetailView, SECRET_MASK } from '../views/CodexView'
import { CodexDetail } from '../CodexDetail'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  del: vi.fn(),
  entityRelations: vi.fn(),
  addEntityRelation: vi.fn(),
  delEntityRelation: vi.fn(),
  characterRelations: vi.fn(),
  entities: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

// 精简版注册表 fixture(字段子集,覆盖 text/textarea+secret/object/array<object>/deprecated 五种
// 情形即可验证渲染逻辑;不需要复刻后端全部 28 字段)。形状对齐真实
// codex_schema.schema_for('faction') 的 JSON 字典:key/label/type/secret_capable/in_prompt/
// desc/enum/item_schema/deprecated 齐全。
const FACTION_SCHEMA_FIXTURE = [
  { key: 'name', label: '势力名', type: 'text', secret_capable: false, in_prompt: true, desc: '', enum: null, item_schema: null, deprecated: false },
  { key: 'origin', label: '起源', type: 'textarea', secret_capable: true, in_prompt: true, desc: '势力真实的成立缘起,可能与其对外宣称的说法不同。', enum: null, item_schema: null, deprecated: false },
  {
    key: 'structure', label: '组织结构', type: 'object', secret_capable: false, in_prompt: true, desc: '', enum: null, deprecated: false,
    item_schema: [
      { key: 'core_size', label: '核心圈人数', type: 'int', secret_capable: false, in_prompt: true, desc: '', enum: null, item_schema: null, deprecated: false },
      { key: 'succession', label: '继承机制', type: 'text', secret_capable: false, in_prompt: true, desc: '', enum: null, item_schema: null, deprecated: false },
    ],
  },
  {
    key: 'key_figures', label: '关键人物', type: 'array<object>', secret_capable: false, in_prompt: true, desc: '', enum: null, deprecated: false,
    item_schema: [
      { key: 'name', label: '姓名', type: 'text', secret_capable: false, in_prompt: true, desc: '', enum: null, item_schema: null, deprecated: false },
      { key: 'generation', label: '代际', type: 'int', secret_capable: false, in_prompt: true, desc: '', enum: null, item_schema: null, deprecated: false },
    ],
  },
  { key: 'private_operation', label: '私下运作(已废弃)', type: 'textarea', secret_capable: true, in_prompt: false, desc: '', enum: null, item_schema: null, deprecated: true },
]

const schemaOnlyGet = (url) =>
  url === '/codex-schema/faction' ? Promise.resolve(FACTION_SCHEMA_FIXTURE) : Promise.reject(new Error(`unexpected GET ${url}`))

describe('CodexView DetailView(factions) 元数据驱动渲染', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation(schemaOnlyGet)
  })

  it('① 拉取 codex-schema 成功后按元数据渲染新字段(含 object 嵌套/array<object>),deprecated 无值不显示', async () => {
    const row = { name: '衔尾蛇秘会', origin: '来源不可考', structure: { core_size: 3, succession: '禅让' }, key_figures: [] }
    render(<DetailView type="factions" row={row} isNew={false} onUpdate={vi.fn()} onDelete={vi.fn()} />)

    // 旧 fieldMap.factions 里没有这些字段(它只有 name/ideology/leader/public_face/
    // private_operation/known_members/private_operation_secret 七个)——出现即证明走的是
    // 元数据渲染路径,不是硬编码 fallback。
    expect(await screen.findByText('起源')).toBeTruthy()
    expect(screen.getByText('组织结构')).toBeTruthy()
    expect(screen.getByText('关键人物')).toBeTruthy()

    // 已存在设定只读:object/array 以纯文本展示(非输入框)
    expect(screen.getByText(/core_size/, { exact: false })).toBeTruthy()
    expect(screen.getByText(/禅让/, { exact: false })).toBeTruthy()

    // deprecated 字段(private_operation)本行无值 → 不显示(hasValue 判空)
    expect(screen.queryByText(/私下运作/)).toBeNull()
  })

  it('② array<object> 字段(关键人物)可增删行(仅新建可写)', async () => {
    const onUpdate = vi.fn()
    const row = { name: '衔尾蛇秘会', key_figures: [{ name: '甲', generation: 1 }] }
    render(<DetailView type="factions" row={row} isNew onUpdate={onUpdate} onDelete={vi.fn()} />)

    // 折叠态先能看到既有行的摘要
    expect(await screen.findByText(/甲/)).toBeTruthy()

    // 增:点"添加"展开新行表单,填姓名,保存 → onUpdate 收到追加后的两行
    fireEvent.click(screen.getByRole('button', { name: '添加' }))
    fireEvent.change(screen.getByLabelText('姓名'), { target: { value: '乙' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    await waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1))
    expect(onUpdate.mock.calls[0][0].key_figures).toEqual([
      { name: '甲', generation: 1 },
      { name: '乙', generation: null },
    ])

    // 删:点既有第1行的删除按钮 → onUpdate 收到过滤后的空数组
    fireEvent.click(screen.getByRole('button', { name: '删除第1行' }))
    await waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(2))
    expect(onUpdate.mock.calls[1][0].key_figures).toEqual([])
  })

  it('③ secret_capable 字段(起源)渲染限知开关,反映当前状态且可切换(仅新建可写)', async () => {
    const onUpdate = vi.fn()
    const row = { name: '衔尾蛇秘会', origin: '真实起源文本', origin_secret: true, key_figures: [] }
    render(<DetailView type="factions" row={row} isNew onUpdate={onUpdate} onDelete={vi.fn()} />)

    const toggle = await screen.findByLabelText(/限知/)
    expect(toggle.checked).toBe(true)

    fireEvent.click(toggle)
    await waitFor(() => expect(onUpdate).toHaveBeenCalled())
    expect(onUpdate.mock.calls.at(-1)[0].origin_secret).toBe(false)
  })

  it('④ 关键陷阱回归:掩码哨兵不会在编辑其它字段时被当真值回写(新建/可写路径)', async () => {
    const onUpdate = vi.fn()
    // 后端 GET(未 reveal)对已标 secret 的字段回传掩码哨兵(app.py _SECRET_MASK),非真值——
    // 前端拿到的 row.origin 此刻字面就是这个占位符。
    const row = { name: '衔尾蛇秘会', origin: SECRET_MASK, origin_secret: true, key_figures: [] }
    render(<DetailView type="factions" row={row} isNew onUpdate={onUpdate} onDelete={vi.fn()} />)

    await screen.findByLabelText(/限知/)

    // immediate 新建:改势力名每键 onSave
    const nameInput = screen.getByDisplayValue('衔尾蛇秘会')
    fireEvent.change(nameInput, { target: { value: '衔尾蛇秘会(改名)' } })

    await waitFor(() => expect(onUpdate).toHaveBeenCalled())
    const payload = onUpdate.mock.calls.at(-1)[0]
    expect(payload.name).toBe('衔尾蛇秘会(改名)')
    // 核心断言:掩码哨兵字符串没有被当真值回写进 payload——stripSecretMask 按值过滤,整键剔除
    expect('origin' in payload).toBe(false)
    expect(payload.origin).not.toBe(SECRET_MASK)
    // 秘密旗标本身(布尔值,非哨兵字符串)照常透传,证明过滤是按值精确命中,不是误伤整个 secret 家族
    expect(payload.origin_secret).toBe(true)
  })

  it('⑤ codex-schema 拉取失败 → fallback 到旧 fieldMap,不白屏', async () => {
    apiMock.get.mockRejectedValue(new Error('network down'))
    const row = { name: '衔尾蛇秘会', ideology: '万物寄生共荣' }
    render(<DetailView type="factions" row={row} isNew={false} onUpdate={vi.fn()} onDelete={vi.fn()} />)

    // 旧 fieldMap.factions 字段(意识形态)全程可见——挂载瞬间就是它(fallback 是初值,不是等错误后才切换)
    expect(screen.getByText('意识形态')).toBeTruthy()
    await waitFor(() => expect(apiMock.get).toHaveBeenCalledWith('/codex-schema/faction'))
    // 拒绝落定之后仍是旧表单,没有白屏/ 崩溃
    expect(screen.getByText('意识形态')).toBeTruthy()
    // 新字段(起源等)不在旧 fieldMap 里,自然不出现
    expect(screen.queryByText('起源')).toBeNull()
  })
})

describe('角色质变与详情外层联动', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation((url) =>
      url.startsWith('/char-states?') ? Promise.resolve([]) : Promise.resolve([]))
    apiMock.post.mockResolvedValue({ ok: true })
    apiMock.characterRelations.mockResolvedValue([])
    apiMock.entities.mockResolvedValue([])
  })

  it('已存在角色弧光区只读,引导主编写入(不直填质变表单)', async () => {
    sessionStorage.clear()
    render(<DetailView type="chars" row={{ id: 'role:季棠', name: '季棠' }} isNew={false}
      onUpdate={vi.fn()} onDelete={vi.fn()} />)

    fireEvent.click(await screen.findByTestId('timeline-ask-chief'))
    const seed = sessionStorage.getItem('s3.chief.seed') || ''
    expect(seed).toMatch(/弧光质变/)
    expect(apiMock.post).not.toHaveBeenCalled()
  })
})

describe('CodexDetail 势力「关系」区(entity_relation,CX-Task 5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('⑥ 双向展示各自认知(a/b 视角随本势力所处方位互换),truth 照掩码显示不 reveal', async () => {
    apiMock.get.mockImplementation((url) => {
      if (url === '/factions') return Promise.resolve([{ name: '衔尾蛇秘会', key_figures: [] }])
      return schemaOnlyGet(url)
    })
    apiMock.entityRelations.mockResolvedValue([
      {
        a: 'faction:衔尾蛇秘会', b: 'faction:天龙座', relation_type: '臣服',
        perception_a: '虚与委蛇,视为台阶', perception_b: '视其为地球代理人',
        truth: SECRET_MASK, truth_secret: true, since_chapter: 1, until_chapter: null,
      },
      {
        a: 'faction:某旧盟', b: 'faction:衔尾蛇秘会', relation_type: '结盟',
        perception_a: '认为对方是可靠盟友', perception_b: '认为对方迟早背刺',
        truth: null, truth_secret: false, since_chapter: 2, until_chapter: null,
      },
    ])

    render(<CodexDetail node={{ id: 'faction:衔尾蛇秘会', type: 'faction', ref: '衔尾蛇秘会', label: '衔尾蛇秘会' }} />)
    await screen.findByTestId('faction-relations')

    // 第一条:本势力(衔尾蛇秘会)是 a → 我方认知取 perception_a,对方(天龙座)认知取 perception_b
    expect(screen.getByText('faction:天龙座')).toBeTruthy()
    expect(screen.getByText('虚与委蛇,视为台阶')).toBeTruthy()
    expect(screen.getByText('视其为地球代理人')).toBeTruthy()
    // truth 默认掩码:原样显示后端返回的掩码占位符,不做任何"解锁"尝试
    expect(screen.getByText(SECRET_MASK, { exact: false })).toBeTruthy()

    // 第二条:本势力是 b → 视角互换,我方认知取 perception_b,对方(某旧盟)认知取 perception_a
    expect(screen.getByText('faction:某旧盟')).toBeTruthy()
    expect(screen.getByText('认为对方迟早背刺')).toBeTruthy()   // 我方(衔尾蛇秘会)认知
    expect(screen.getByText('认为对方是可靠盟友')).toBeTruthy() // 对方(某旧盟)认知
  })

  it('关系区只读 + 让主编维护(不再直填 POST/DELETE)', async () => {
    sessionStorage.clear()
    apiMock.get.mockImplementation((url) => {
      if (url === '/factions') return Promise.resolve([{ name: '衔尾蛇秘会', key_figures: [] }])
      return schemaOnlyGet(url)
    })
    apiMock.entityRelations.mockResolvedValue([])

    render(<CodexDetail node={{ id: 'faction:衔尾蛇秘会', type: 'faction', ref: '衔尾蛇秘会', label: '衔尾蛇秘会' }} />)
    await screen.findByTestId('faction-relations')

    fireEvent.click(screen.getByTestId('faction-rel-ask-chief'))
    const seed = sessionStorage.getItem('s3.chief.seed') || ''
    expect(seed).toMatch(/势力关系|entity_relation/)
    expect(apiMock.addEntityRelation).not.toHaveBeenCalled()
    expect(screen.queryByPlaceholderText(/对方实体/)).toBeNull()
  })
})
