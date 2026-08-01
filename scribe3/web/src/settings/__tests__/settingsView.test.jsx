import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  settings: vi.fn(), putSetting: vi.fn(), resetSetting: vi.fn(),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [] })),
  gatewayStatus: vi.fn(() => Promise.resolve({ gateways: [] })),
  gatewayFiles: vi.fn(() => Promise.resolve({ files: [] })),
  gatewayModelSummary: vi.fn(() => Promise.resolve({ gateways: [] })),
  dashboardStatus: vi.fn(() => Promise.resolve({ online: false, url: 'http://127.0.0.1:9119' })),
  dashboardStart: vi.fn(() => Promise.resolve({ online: true, message: 'ok' })),
  gatewayRestart: vi.fn(() => Promise.resolve({ online: true, profile: 'scribe3', message: 'ok' })),
  putGatewayFile: vi.fn(() => Promise.resolve({ sha256: 'new' })),
  aiUsage: vi.fn(() => Promise.resolve({ cap: { cap: 0, used_today: 0, remaining: 0, scope: 'shared' } })),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { SettingsView } from '../SettingsView'

const ITEMS = [
  { key: 'llm.model', category: 'llm', type: 'str', label: '补全模型名',
    value: 'qwen3.8-max-preview', default: 'qwen3.8-max-preview', source: 'default', effect: 'hot', danger: false, pending_restart: false },
  { key: 'SCRIBE3_DAILY_CALL_CAP', category: 'llm', type: 'int', label: '每日 LLM 调用日帽',
    value: 500, default: 500, source: 'default', effect: 'hot', danger: true, pending_restart: false },
  { key: 'SCRIBE3_SURREAL_URL', category: 'connection', type: 'str', label: 'SurrealDB 地址',
    value: 'ws://x', default: 'ws://127.0.0.1:8001/rpc', source: 'db', effect: 'restart', danger: false, pending_restart: true },
  { key: 'SCRIBE3_SURREAL_USER', category: 'connection', type: 'str', label: 'SurrealDB 用户名',
    value: 'admin', default: 'root', source: 'db', effect: 'restart', danger: false, pending_restart: false },
  { key: 'SCRIBE3_MEMORY_FABRIC_V1', category: 'flags', type: 'bool', label: '记忆织网检索 v1',
    value: false, default: false, source: 'default', effect: 'hot', danger: true, pending_restart: false },
  { key: 'SCRIBE3_API_TOKEN', category: 'flags', type: 'secret', label: '后端 API token',
    value: null, default: null, source: 'db', is_set: true, effect: 'restart', danger: false, pending_restart: false },
  { key: 'DEEPSEEK_API_KEY', category: 'gateway', type: 'secret', label: 'Qwen API 密钥（兼容键）',
    value: null, default: null, source: 'db', is_set: true, effect: 'hot', danger: false, pending_restart: false },
]

const usagePayload = ({ model = 'qwen3.8-max-preview', cap = 0, used = 0, key = true } = {}) => ({
  work: 'main',
  cap: {
    cap,
    used_today: used,
    remaining: cap === 0 ? null : Math.max(0, cap - used),
    scope: 'shared',
    unlimited: cap === 0,
  },
  tokens: { days: [] },
  provider: {
    provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model,
    official: true, transport: 'direct', key_present: key,
  },
})

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.settings.mockResolvedValue({ settings: ITEMS, categories: ['connection', 'llm', 'craft', 'flags', 'gateway'] })
  apiMock.putSetting.mockResolvedValue({})
  apiMock.resetSetting.mockResolvedValue({})
  apiMock.aiUsage = vi.fn(() => Promise.resolve(usagePayload()))
})

describe('SettingsView', () => {
  it('元数据驱动渲染:分区导航 + 项 + 待重启黄标 + 来源徽章', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
    expect(screen.getByText('连接与服务')).toBeTruthy()
    fireEvent.click(screen.getByText('连接与服务'))
    expect(screen.getByText('重启后生效')).toBeTruthy()   // pending_restart 黄标
    expect(screen.getAllByText('已自定义').length).toBeGreaterThanOrEqual(1)   // source=db 徽章
  })

  it('danger 项修改需二次确认后才 PUT', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('灰度开关')).toBeTruthy())
    fireEvent.click(screen.getByText('灰度开关'))
    fireEvent.click(screen.getByRole('switch', { name: '记忆织网检索 v1' }))
    expect(apiMock.putSetting).not.toHaveBeenCalled()      // 先确认
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.putSetting).toHaveBeenCalledWith('SCRIBE3_MEMORY_FABRIC_V1', true))
  })

  it('恢复默认按钮走确认后调 resetSetting 并重拉', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    fireEvent.click(screen.getByRole('button', { name: '恢复默认:SurrealDB 地址' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledWith('SCRIBE3_SURREAL_URL'))
  })

  it('数字输入非法(清空失焦)本地拒绝,不出网', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
    const input = screen.getByRole('spinbutton', { name: '每日 LLM 调用日帽' })
    fireEvent.change(input, { target: { value: '' } })
    fireEvent.blur(input)
    expect(apiMock.putSetting).not.toHaveBeenCalled()
    expect(screen.getByRole('alert').textContent).toContain('请输入有效数字')
  })

  it('恢复默认失败显示错误反馈而非静默', async () => {
    apiMock.resetSetting.mockRejectedValueOnce(new Error('boom'))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    fireEvent.click(screen.getByRole('button', { name: '恢复默认:SurrealDB 地址' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('boom'))
  })

  it('分区级「全部恢复默认」:该分区有 db 项时才出现,确认后逐项调 resetSetting 并重拉', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    // connection 分区有 SCRIBE3_SURREAL_URL + SCRIBE3_SURREAL_USER 两个 source=db 项
    const btn = screen.getByRole('button', { name: '全部恢复默认' })
    fireEvent.click(btn)
    expect(apiMock.resetSetting).not.toHaveBeenCalled()   // 先确认
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledTimes(2))
    expect(apiMock.resetSetting).toHaveBeenCalledWith('SCRIBE3_SURREAL_URL')
    expect(apiMock.resetSetting).toHaveBeenCalledWith('SCRIBE3_SURREAL_USER')
    await waitFor(() => expect(apiMock.settings).toHaveBeenCalledTimes(2))   // 初次加载 + 重拉
  })

  it('分区级「全部恢复默认」:无 db 项的分区不出现按钮', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('工艺阈值')).toBeTruthy())
    fireEvent.click(screen.getByText('工艺阈值'))
    expect(screen.queryByRole('button', { name: '全部恢复默认' })).toBeNull()
  })

  it('分区级「全部恢复默认」:串行执行,某项失败即中断并显示是哪项失败', async () => {
    apiMock.resetSetting
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error('db 打不开'))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    fireEvent.click(screen.getByRole('button', { name: '全部恢复默认' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('db 打不开'))
    expect(screen.getByRole('alert').textContent).toContain('SurrealDB 用户名')   // 显示哪项失败
    expect(apiMock.settings).toHaveBeenCalledTimes(1)   // 中断:不重拉
  })

  it('secret 项 default 为 None 时,恢复默认提示显示「恢复为未设置」而非 null', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('灰度开关')).toBeTruthy())
    fireEvent.click(screen.getByText('灰度开关'))
    const btn = screen.getByRole('button', { name: '恢复默认:后端 API token' })
    expect(btn.title).toBe('恢复为未设置')
    expect(btn.title).not.toContain('null')
    fireEvent.click(btn)
    await waitFor(() => expect(screen.getByText('恢复为未设置')).toBeTruthy())
    expect(document.body.textContent).not.toContain('null')
  })

  it('llm 分区内嵌用量面板', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main', cap: { cap: 500, used_today: 417, remaining: 83, scope: 'shared' },
      tokens: { days: [], since: '2026-07-06' },
    }))
    render(<SettingsView work="demo" />)
    const usageText = await screen.findByText('今日已用 417 / 日帽 500')
    expect(screen.getByText('83%')).toBeTruthy()
    expect(usageText.parentElement?.parentElement?.querySelector('[style="width: 83%;"]')).toBeTruthy()
  })

  it('用量面板显示阿里云 TokenPlan 的模型与直连证据', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 3, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: {
        provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview',
        official: true, transport: 'direct', key_present: true,
      },
    }))
    render(<SettingsView work="demo" />)

    expect(await screen.findByText('阿里云 TokenPlan · Qwen 兼容 · qwen3.8-max-preview · 直连')).toBeTruthy()
  })

  it.each([
    ['provider 非 qwen', { provider: 'proxy', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview', official: true, transport: 'direct' }],
    ['official 非 true', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview', official: false, transport: 'direct' }],
    ['transport 非 direct', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview', official: true, transport: 'httpx' }],
    ['api_base 非官方精确值', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/extra', model: 'qwen3.8-max-preview', official: true, transport: 'direct' }],
    ['api_base 缺失', { provider: 'qwen', model: 'qwen3.8-max-preview', official: true, transport: 'direct' }],
    ['model 为空字符串', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: '', official: true, transport: 'direct' }],
    ['model 仅空白', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: '   ', official: true, transport: 'direct' }],
    ['model 非字符串', { provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 42, official: true, transport: 'direct' }],
  ])('非严格官方直连身份时隐藏官方行：%s', async (_label, provider) => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 1, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: { ...provider, key_present: true },
    }))
    render(<SettingsView work="demo" />)

    await screen.findByText(/今日已用 1 发/)
    expect(screen.queryByText(/官方 Qwen/)).toBeNull()
  })

  it.each([
    ['key_present 缺失', {}],
    ['key_present 为 null', { key_present: null }],
    ['key_present 为字符串', { key_present: 'true' }],
  ])('密钥状态非布尔时隐藏官方行：%s', async (_label, keyState) => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 1, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: {
        provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview',
        official: true, transport: 'direct', ...keyState,
      },
    }))
    render(<SettingsView work="demo" />)

    await screen.findByText(/今日已用 1 发/)
    expect(screen.queryByText(/官方 Qwen/)).toBeNull()
  })

  it('未显式配置 Qwen 兼容键时如实显示未配置', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 0, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: {
        provider: 'qwen', api_base: 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1', model: 'qwen3.8-max-preview',
        official: true, transport: 'direct', key_present: false,
      },
    }))
    render(<SettingsView work="demo" />)

    expect(await screen.findByText('未保存密钥')).toBeTruthy()
    expect(screen.queryByText(/ready|已就绪|已配置/i)).toBeNull()
  })

  it('无限用量时展示今日已用和不限次数', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main', cap: { cap: 0, used_today: 12, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [], since: '2026-07-06' },
    }))
    render(<SettingsView work="demo" />)

    const usage = await screen.findByText(/今日已用 12 发/)
    expect(usage.parentElement?.textContent).toContain('不限次数')
    expect(usage.parentElement?.textContent).not.toMatch(/\/\s*0/)
    expect(usage.parentElement?.textContent).not.toContain('日帽 0')
  })

  it('用量拉取失败时静默隐藏用量卡(fail-soft)', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.reject(new Error('boom')))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
    expect(screen.queryByText(/今日已用/)).toBeNull()
  })

  it('保存 llm.model 后同时重拉 settings 与 usage 并立即更新模型', async () => {
    apiMock.aiUsage
      .mockResolvedValueOnce(usagePayload({ model: 'qwen3.8-max-preview' }))
      .mockResolvedValueOnce(usagePayload({ model: 'qwen-plus' }))
    render(<SettingsView work="demo" />)
    expect(await screen.findByText('阿里云 TokenPlan · Qwen 兼容 · qwen3.8-max-preview · 直连')).toBeTruthy()

    const input = screen.getByRole('textbox', { name: '补全模型名' })
    fireEvent.change(input, { target: { value: 'qwen-plus' } })
    fireEvent.blur(input)

    await waitFor(() => expect(apiMock.putSetting).toHaveBeenCalledWith('llm.model', 'qwen-plus'))
    await waitFor(() => expect(apiMock.settings).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(apiMock.aiUsage).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('阿里云 TokenPlan · Qwen 兼容 · qwen-plus · 直连')).toBeTruthy()
  })

  it('保存日帽后 usage 卡立即更新', async () => {
    apiMock.aiUsage
      .mockResolvedValueOnce(usagePayload({ cap: 500, used: 25 }))
      .mockResolvedValueOnce(usagePayload({ cap: 100, used: 25 }))
    render(<SettingsView work="demo" />)
    expect(await screen.findByText('今日已用 25 / 日帽 500')).toBeTruthy()

    const input = screen.getByRole('spinbutton', { name: '每日 LLM 调用日帽' })
    fireEvent.change(input, { target: { value: '100' } })
    fireEvent.blur(input)
    fireEvent.click(screen.getByRole('button', { name: '确认' }))

    await waitFor(() => expect(apiMock.putSetting).toHaveBeenCalledWith('SCRIBE3_DAILY_CALL_CAP', 100))
    expect(await screen.findByText('今日已用 25 / 日帽 100')).toBeTruthy()
  })

  it('重置 Qwen 兼容 secret 后立即重拉 usage 并更新密钥状态', async () => {
    apiMock.aiUsage
      .mockResolvedValueOnce(usagePayload({ key: true }))
      .mockResolvedValueOnce(usagePayload({ key: false }))
    render(<SettingsView work="demo" />)
    expect(await screen.findByText('密钥记录存在（未验证）')).toBeTruthy()
    expect(screen.queryByText(/已配置|已就绪/)).toBeNull()

    fireEvent.click(screen.getByText('Hermes 网关'))
    fireEvent.click(screen.getByRole('button', { name: '恢复默认:Qwen API 密钥（兼容键）' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))

    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledWith('DEEPSEEK_API_KEY'))
    await waitFor(() => expect(apiMock.settings).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(apiMock.aiUsage).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByText('LLM 与用量'))
    expect(await screen.findByText('未保存密钥')).toBeTruthy()
  })

  it('较旧 usage 请求晚返回时不得覆盖新 revision', async () => {
    let resolveOld
    let resolveNew
    apiMock.aiUsage
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve }))
    render(<SettingsView work="demo" />)
    await screen.findByText('补全模型名')

    const input = screen.getByRole('textbox', { name: '补全模型名' })
    fireEvent.change(input, { target: { value: 'qwen-plus' } })
    fireEvent.blur(input)
    await waitFor(() => expect(apiMock.aiUsage).toHaveBeenCalledTimes(2))

    await act(async () => { resolveNew(usagePayload({ model: 'qwen-plus' })) })
    expect(await screen.findByText('阿里云 TokenPlan · Qwen 兼容 · qwen-plus · 直连')).toBeTruthy()
    await act(async () => { resolveOld(usagePayload({ model: 'qwen3.8-max-preview' })) })
    await waitFor(() => {
      expect(screen.getByText('阿里云 TokenPlan · Qwen 兼容 · qwen-plus · 直连')).toBeTruthy()
      expect(screen.queryByText('阿里云 TokenPlan · Qwen 兼容 · qwen3.8-max-preview · 直连')).toBeNull()
    })
  })

  it('较旧 settings 请求晚返回时不得覆盖保存后的新 revision', async () => {
    let resolveOld
    let resolveNew
    const settingsPayload = (model) => ({
      settings: ITEMS.map((item) => (
        item.key === 'llm.model' ? { ...item, value: model } : item
      )),
      categories: ['connection', 'llm', 'craft', 'flags', 'gateway'],
    })
    apiMock.settings
      .mockResolvedValueOnce(settingsPayload('qwen3.8-max-preview'))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve }))
    render(<SettingsView work="demo" />)

    const input = await screen.findByRole('textbox', { name: '补全模型名' })
    fireEvent.change(input, { target: { value: 'qwen-plus' } })
    fireEvent.blur(input)
    await waitFor(() => expect(apiMock.settings).toHaveBeenCalledTimes(2))

    fireEvent.change(input, { target: { value: 'qwen-newest' } })
    fireEvent.blur(input)
    await waitFor(() => expect(apiMock.settings).toHaveBeenCalledTimes(3))

    await act(async () => { resolveNew(settingsPayload('qwen-newest')) })
    await waitFor(() => expect(input.value).toBe('qwen-newest'))
    await act(async () => { resolveOld(settingsPayload('qwen-plus')) })
    await waitFor(() => expect(input.value).toBe('qwen-newest'))
  })

  it('拉取失败显示错误态与重试', async () => {
    apiMock.settings.mockRejectedValueOnce(new Error('boom'))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText(/设置加载失败/)).toBeTruthy())
    fireEvent.click(screen.getByText('重试'))
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
  })
})
