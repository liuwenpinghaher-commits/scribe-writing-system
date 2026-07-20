import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  settings: vi.fn(), putSetting: vi.fn(), resetSetting: vi.fn(),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [] })),
  gatewayStatus: vi.fn(() => Promise.resolve({ gateways: [] })),
  gatewayFiles: vi.fn(() => Promise.resolve({ files: [] })),
  aiUsage: vi.fn(() => Promise.resolve({ cap: { cap: 0, used_today: 0, remaining: 0, scope: 'shared' } })),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { SettingsView } from '../SettingsView'

const ITEMS = [
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
]

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.settings.mockResolvedValue({ settings: ITEMS, categories: ['connection', 'llm', 'craft', 'flags', 'gateway'] })
  apiMock.putSetting.mockResolvedValue({})
  apiMock.resetSetting.mockResolvedValue({})
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

  it('用量面板显示官方 DeepSeek 模型与直连证据', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 3, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: {
        provider: 'deepseek', api_base: 'https://api.deepseek.com', model: 'deepseek-chat',
        official: true, transport: 'direct', key_configured: true,
      },
    }))
    render(<SettingsView work="demo" />)

    expect(await screen.findByText('官方 DeepSeek · deepseek-chat · 直连')).toBeTruthy()
  })

  it('未显式配置 DeepSeek 密钥时如实显示未配置', async () => {
    apiMock.aiUsage = vi.fn(() => Promise.resolve({
      work: 'main',
      cap: { cap: 0, used_today: 0, remaining: null, scope: 'shared', unlimited: true },
      tokens: { days: [] },
      provider: {
        provider: 'deepseek', api_base: 'https://api.deepseek.com', model: 'deepseek-chat',
        official: true, transport: 'direct', key_configured: false,
      },
    }))
    render(<SettingsView work="demo" />)

    expect(await screen.findByText('未配置密钥')).toBeTruthy()
    expect(screen.queryByText(/ready|已就绪/i)).toBeNull()
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

  it('拉取失败显示错误态与重试', async () => {
    apiMock.settings.mockRejectedValueOnce(new Error('boom'))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText(/设置加载失败/)).toBeTruthy())
    fireEvent.click(screen.getByText('重试'))
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
  })
})
