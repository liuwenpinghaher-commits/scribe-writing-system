import { describe, it, expect } from 'vitest'
import { matchStageProposal, beatsFromMarkdown, fallbackProposalText } from './stageProposal'

describe('matchStageProposal', () => {
  const p = { phase: 'outline', seq: 4, target: null, content: '一段大纲', ts: 1 }
  it('phase/seq/target 全匹配才返回', () => {
    expect(matchStageProposal(p, { phase: 'outline', seq: 4 })).toBe(p)
  })
  it('null proposal / 空内容 → null', () => {
    expect(matchStageProposal(null, { phase: 'outline', seq: 4 })).toBeNull()
    expect(matchStageProposal({ ...p, content: '  ' }, { phase: 'outline', seq: 4 })).toBeNull()
  })
  it('切阶段(phase 不符)不错落', () => {
    expect(matchStageProposal(p, { phase: 'draft', seq: 4 })).toBeNull()
  })
  it('切章(seq 不符)不错落', () => {
    expect(matchStageProposal(p, { phase: 'outline', seq: 5 })).toBeNull()
  })
  it('演绎 target 精确匹配:truth 与角色互不错落', () => {
    const d = { phase: 'deduce', seq: 4, target: 'role:崔判', content: 'x', ts: 2 }
    expect(matchStageProposal(d, { phase: 'deduce', seq: 4, target: 'role:崔判' })).toBe(d)
    expect(matchStageProposal(d, { phase: 'deduce', seq: 4, target: 'truth' })).toBeNull()
    expect(matchStageProposal(d, { phase: 'deduce', seq: 4, target: 'role:柳怀玉' })).toBeNull()
  })
  it('target 缺省与 null 等价(大纲/节拍/草稿)', () => {
    expect(matchStageProposal({ ...p, target: undefined }, { phase: 'outline', seq: 4, target: null })).toBeTruthy()
  })
})

describe('beatsFromMarkdown', () => {
  it('剥 - / 数字列表标记,一行一条', () => {
    expect(beatsFromMarkdown('- 焦三进坊\n- 初见铜炉\n')).toEqual(['焦三进坊', '初见铜炉'])
    expect(beatsFromMarkdown('1. 开场\n2. 转折\n3、收束')).toEqual(['开场', '转折', '收束'])
  })
  it('标题行跳过,空行跳过,无标记按非空行拆', () => {
    expect(beatsFromMarkdown('## 本章节拍\n\n开场:雨夜\n收束:灯灭')).toEqual(['开场:雨夜', '收束:灯灭'])
  })
  it('行内 markdown 原样保留;空输入 → []', () => {
    expect(beatsFromMarkdown('- **开场**:雨夜')).toEqual(['**开场**:雨夜'])
    expect(beatsFromMarkdown('')).toEqual([])
    expect(beatsFromMarkdown(null)).toEqual([])
  })
  it('负例:行首粗体不误剥(* 后无空白不是列表)', () => {
    expect(beatsFromMarkdown('**开场**:雨夜')).toEqual(['**开场**:雨夜'])
  })
  it('负例:负数不误剥(- 后无空白)', () => {
    expect(beatsFromMarkdown('-3度的寒夜里守灵')).toEqual(['-3度的寒夜里守灵'])
  })
  it('负例:小数不误剥(序号后不得紧跟数字)', () => {
    expect(beatsFromMarkdown('3.5万字内收束本卷')).toEqual(['3.5万字内收束本卷'])
  })
  it('负例:``` 码块整段跳过', () => {
    expect(beatsFromMarkdown('- 真条目\n```\n- 码块里的假条目\nx = 1\n```\n- 又一条')).toEqual(['真条目', '又一条'])
  })
})

describe('fallbackProposalText(chatWrite 兜底发布选择)', () => {
  it('收到过 proposal 收尾 → null(绝不重发覆盖围栏稿)', () => {
    expect(fallbackProposalText({ gotProposal: true, propOpen: true, propAcc: '半截稿', turnText: '讨论' })).toBeNull()
  })
  it('围栏开过但没收尾(截断)→ 发部分正文 propAcc,不发讨论前言', () => {
    expect(fallbackProposalText({ gotProposal: false, propOpen: true, propAcc: '半截正文', turnText: '处理思路…' })).toBe('半截正文')
  })
  it('整轮无围栏 → 发纯 delta 累积 turnText', () => {
    expect(fallbackProposalText({ gotProposal: false, propOpen: false, propAcc: '', turnText: '纯讨论正文' })).toBe('纯讨论正文')
  })
})
