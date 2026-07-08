import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SearchDetail } from '../capabilities/search/SearchDetail'
import { SearchDirectory } from '../capabilities/search/SearchDirectory'

const apiMock = vi.hoisted(() => ({
  search: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

const payload = {
  results: [
    {
      id: 'search:chapter:4',
      type: 'chapter',
      label: '借命铜炉',
      excerpt: '崔判在铜炉前提出借命交易。',
      source: '正文',
      chapter: 4,
      score: 1,
      target_node: { id: 'ch:4', type: 'chapter', ref: 4, label: '4 借命铜炉' },
    },
    {
      id: 'search:material:1',
      type: 'material',
      label: '借命仪式资料',
      excerpt: '铜炉、寿数与替身交易的民俗记录。',
      source: '素材',
      score: 0.8,
      target_node: { id: 'material:1', type: 'material', ref: 1, label: '借命仪式资料' },
    },
    {
      id: 'search:event:ev:借命摊牌',
      type: 'event',
      label: '借命摊牌',
      excerpt: '崔判逼柳怀玉签契。',
      source: '事件',
      chapter: 4,
      score: 0.78,
      target_node: { id: 'ev:借命摊牌', type: 'event', chapter: 4, label: '借命摊牌' },
    },
  ],
}

describe('全局搜索能力', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.search.mockResolvedValue(payload)
  })

  it('栏2执行搜索并按来源分组,点击结果传出详情节点', async () => {
    const onSelectItem = vi.fn()
    render(<SearchDirectory onSelectItem={onSelectItem} />)

    fireEvent.change(screen.getByLabelText('全局搜索'), { target: { value: '借命' } })
    fireEvent.click(screen.getByRole('button', { name: '搜索' }))

    await waitFor(() => expect(apiMock.search).toHaveBeenCalledWith('借命'))
    expect(screen.getByText('正文')).toBeTruthy()
    expect(screen.getByText('素材')).toBeTruthy()
    expect(screen.getByText('事件')).toBeTruthy()
    fireEvent.click(within(screen.getByTestId('search-results')).getByRole('button', { name: /借命仪式资料/ }))

    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'recall_result',
      label: '借命仪式资料',
      target_node: expect.objectContaining({ type: 'material' }),
    }))

    fireEvent.click(within(screen.getByTestId('search-results')).getByRole('button', { name: /借命摊牌/ }))
    expect(onSelectItem).toHaveBeenCalledWith(expect.objectContaining({
      type: 'recall_result',
      label: '借命摊牌',
      target_node: expect.objectContaining({ type: 'event', chapter: 4 }),
    }))
  })

  it('栏3展示命中详情并可打开真实目标', () => {
    const onOpenTarget = vi.fn()
    render(<SearchDetail node={{ ...payload.results[0], type: 'recall_result' }} onOpenTarget={onOpenTarget} />)

    expect(screen.getByText('借命铜炉')).toBeTruthy()
    expect(screen.getByText('崔判在铜炉前提出借命交易。')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /打开目标/ }))

    expect(onOpenTarget).toHaveBeenCalledWith(expect.objectContaining({ type: 'chapter', ref: 4 }))
  })
})
