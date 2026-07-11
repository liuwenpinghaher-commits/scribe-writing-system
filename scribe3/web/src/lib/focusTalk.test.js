// 块三:通用选中总线纯逻辑单测——focusFromSel(sel→focus 镜像)+ focusTalk(focus→主编话术)+ focusChatKey。
import { describe, it, expect } from 'vitest'
import { focusTalk, focusChatKey, nextChatFocusKey } from './focusTalk'
import { focusFromSel } from '../selectionContext'

describe('focusFromSel(sel → focus 镜像)', () => {
  it('空 sel → null', () => {
    expect(focusFromSel(null)).toBeNull()
    expect(focusFromSel({ mode: 'node', node: null })).toBeNull()
  })
  it('视图级 sel → type view + origin sel', () => {
    const f = focusFromSel({ mode: 'view', viewKey: 'atlas' })
    expect(f).toMatchObject({ type: 'view', id: 'atlas', origin: 'sel' })
  })
  it('节点级 sel → 节点 type/id/label + origin sel', () => {
    const f = focusFromSel({ mode: 'node', node: { id: 'character:role:崔判', type: 'character', ref: 'role:崔判', label: '崔判' } })
    expect(f).toMatchObject({ type: 'character', id: 'character:role:崔判', label: '崔判', origin: 'sel' })
    expect(f.payload.ref).toBe('role:崔判')
  })
  it('无 label 节点回退 ref', () => {
    const f = focusFromSel({ mode: 'node', node: { id: 'ch:3', type: 'chapter', ref: 3 } })
    expect(f.label).toBe('3')
  })
})

describe('focusTalk(focus → 话术;null=回退 selContext)', () => {
  it('focus 为空 / sel 镜像 / 演绎目标 → null(回退)', () => {
    expect(focusTalk(null)).toBeNull()
    expect(focusTalk({ type: 'character', id: 'x', label: 'x', origin: 'sel' })).toBeNull()
    expect(focusTalk({ type: 'deduction', id: 'truth', label: '场景真相', origin: 'deduce' })).toBeNull()
  })
  it('伏笔:label 含文本片段,prefix 带埋/收章与超期', () => {
    const t = focusTalk({ type: 'promise', id: 'p1', label: '借命契续命者一栏为何空着', payload: { setup_chapter: 1, payoff_chapter: null, overdue: true }, origin: 'panel' })
    expect(t.label).toContain('伏笔 · 借命契续命者一栏为何空着')
    expect(t.prefix).toContain('第1章埋')
    expect(t.prefix).toContain('待收')
    expect(t.prefix).toContain('已超期')
    expect(t.suggests.length).toBeGreaterThan(0)
  })
  it('母题:prefix 带主题与本章触及', () => {
    const t = focusTalk({ type: 'motif', id: 'm1', label: '命与纸', payload: { theme: '纸为命之载体', evidence: '纸人僵立' }, origin: 'panel' })
    expect(t.label).toBe('母题 · 命与纸')
    expect(t.prefix).toContain('纸为命之载体')
    expect(t.prefix).toContain('纸人僵立')
  })
  it('时间线事件/弧光/关系:payload.cat 细分称谓,带章号', () => {
    const ev = focusTalk({ type: 'event', id: 'e1', label: '抢得半张借命契', payload: { cat: 'event', chapter: 4 }, origin: 'timeline' })
    expect(ev.label).toContain('事件 ·')
    expect(ev.prefix).toContain('第4章')
    const arc = focusTalk({ type: 'event', id: 'a1', label: '烫疤预警', payload: { cat: 'arc', chapter: 1 }, origin: 'timeline' })
    expect(arc.label).toContain('弧光 ·')
    const rel = focusTalk({ type: 'event', id: 'r1', label: '师徒', payload: { cat: 'relation' }, origin: 'timeline' })
    expect(rel.label).toContain('关系 ·')
  })
  it('私密命题不泄明文', () => {
    const t = focusTalk({ type: 'frame_fact', id: 'f1', label: '崔判·真身:阴差', payload: { secret: true }, origin: 'atlas' })
    expect(t.label).toBe('命题 · 私密')
    expect(t.prefix).not.toContain('阴差')
  })
  it('角色(图谱来源)与长名截断', () => {
    const t = focusTalk({ type: 'character', id: 'role:崔判', label: '崔判', origin: 'atlas' })
    expect(t.label).toBe('角色 · 崔判')
    expect(t.prefix).toContain('角色「崔判」')
    const long = focusTalk({ type: 'promise', id: 'p2', label: 'A'.repeat(40), payload: {}, origin: 'panel' })
    expect(long.label.length).toBeLessThan(40)
  })
})

describe('focusChatKey(chat 历史判别段)', () => {
  it('镜像/演绎不改 key;显式聚焦各自成串', () => {
    expect(focusChatKey(null)).toBe('')
    expect(focusChatKey({ type: 'chapter', id: 'ch:1', origin: 'sel' })).toBe('')
    expect(focusChatKey({ type: 'deduction', id: 'role:崔判', origin: 'deduce' })).toBe('')
    expect(focusChatKey({ type: 'promise', id: 'p1', origin: 'panel' })).toBe(':focus:promise:p1')
  })
})

describe('nextChatFocusKey(必修2:busy 期间冻结 fKey)', () => {
  it('流在途(busy=true):沿用 prev,不因显式聚焦断流', () => {
    expect(nextChatFocusKey('', ':focus:motif:m1', true)).toBe('')
    expect(nextChatFocusKey(':focus:promise:p1', ':focus:motif:m1', true)).toBe(':focus:promise:p1')
  })
  it('空闲(busy=false):即时应用 live', () => {
    expect(nextChatFocusKey('', ':focus:motif:m1', false)).toBe(':focus:motif:m1')
    expect(nextChatFocusKey(':focus:motif:m1', '', false)).toBe('')
  })
  it('流结束后再切:先冻结、解锁后应用(时序模拟)', () => {
    let key = ''
    key = nextChatFocusKey(key, ':focus:motif:m1', true)   // 生成中点母题 → 冻结
    expect(key).toBe('')
    key = nextChatFocusKey(key, ':focus:motif:m1', false)  // onDone 后下一轮渲染 → 应用
    expect(key).toBe(':focus:motif:m1')
  })
})

describe('focusTalk material 分支(块四a-1 素材库)', () => {
  it('素材聚焦:label 含标题,prefix 含分类展示名与非正典口径', () => {
    const t = focusTalk({ type: 'material', id: 'm1', label: '北宋纸扎工艺', payload: { kind: 'research', source: '县志' }, origin: 'panel' })
    expect(t.label).toBe('素材 · 北宋纸扎工艺')
    expect(t.prefix).toContain('素材「北宋纸扎工艺」')
    expect(t.prefix).toContain('研究')
    expect(t.prefix).toContain('县志')
    expect(t.prefix).toContain('非正典')
    expect(t.suggests.length).toBeGreaterThan(0)
  })
  it('未知 kind 兜底笔记;无 source 不渲染来源段', () => {
    const t = focusTalk({ type: 'material', id: 'm2', label: '随手记', payload: {}, origin: 'panel' })
    expect(t.prefix).toContain('笔记')
    expect(t.prefix).not.toContain('来源')
  })
  it('镜像来源(origin=sel)仍回退 null', () => {
    expect(focusTalk({ type: 'material', id: 'm1', label: 'x', origin: 'sel' })).toBeNull()
  })
})
