import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ObjectFrame } from '../ObjectFrame'
import { getObjectMeta } from '../objectRegistry'

// 通用对象模板(spec §4 地基):任何对象套同一插槽。这里验证 chapter/character/material 三类
// 都能按注册表填出 面包屑 + 对象tab + 状态,且未知类型友好兜底。
describe('ObjectFrame 通用对象模板', () => {
  it('chapter: 渲染面包屑(含第1章)+ 阶段tab(含正文)+ 状态(含6.6k)', () => {
    render(<ObjectFrame type="chapter" obj={{ seq: 1, title: '第1章', word_count: 6600 }} />)
    expect(screen.getByText(/第1章/)).toBeTruthy()
    expect(screen.getByText('正文')).toBeTruthy()
    expect(screen.getByText(/6\.6k/)).toBeTruthy()
  })

  it('character: 面包屑走"设定库›角色›名"+ tab 含弧光', () => {
    render(<ObjectFrame type="character" obj={{ name: '小翠', first_chapter: 2 }} />)
    expect(screen.getByText(/小翠/)).toBeTruthy()
    expect(screen.getByText('弧光')).toBeTruthy()
  })

  it('未知类型: 友好兜底不崩', () => {
    render(<ObjectFrame type="nope" obj={{}} />)
    expect(screen.getByText(/未知对象类型/)).toBeTruthy()
  })

  it('getObjectMeta 纯函数: 返回 crumb/tabs/status/auxTabs', () => {
    const m = getObjectMeta('material', { title: '冷硬白描', ref_tags: ['手法'], recall_count: 3 })
    expect(m.crumb).toContain('冷硬白描')
    expect(m.auxTabs).toContain('联想')
    expect(m.status).toContain('3')
  })
})
