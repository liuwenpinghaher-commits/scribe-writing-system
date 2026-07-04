import { describe, it, expect } from 'vitest'
import { mdToHTML, docToMd } from './markdown'

describe('mdToHTML', () => {
  it('纯文本段落:\\n\\n 分段,段内 \\n 为 <br>', () => {
    expect(mdToHTML('甲\n\n乙')).toBe('<p>甲</p><p>乙</p>')
    expect(mdToHTML('甲\n乙')).toBe('<p>甲<br>乙</p>')
  })
  it('五层小标题 H3 + 纯文本混排不炸', () => {
    expect(mdToHTML('### 看到/听到\n他看见灯灭了。')).toBe('<h3>看到/听到</h3><p>他看见灯灭了。</p>')
  })
  it('行内标记', () => {
    expect(mdToHTML('**粗** 与 *斜* 与 ~~删~~')).toBe('<p><strong>粗</strong> 与 <em>斜</em> 与 <s>删</s></p>')
  })
  it('列表与引用', () => {
    expect(mdToHTML('- a\n- b')).toBe('<ul><li><p>a</p></li><li><p>b</p></li></ul>')
    expect(mdToHTML('1. a\n2. b')).toBe('<ol><li><p>a</p></li><li><p>b</p></li></ol>')
    expect(mdToHTML('> 引')).toBe('<blockquote><p>引</p></blockquote>')
  })
  it('分隔线:--- / ___ / - - - 是 hr;星号行(场景断)按字面段落保留', () => {
    expect(mdToHTML('甲\n\n---\n\n乙')).toBe('<p>甲</p><hr><p>乙</p>')
    expect(mdToHTML('___')).toBe('<hr>')
    // 空格分隔的 dash/underscore 也是 hr(CommonMark thematic break;不落列表项 - -)
    expect(mdToHTML('- - -')).toBe('<hr>')
    expect(mdToHTML('甲\n\n- - -\n\n乙')).toBe('<p>甲</p><hr><p>乙</p>')
    expect(mdToHTML('_ _ _')).toBe('<hr>')
    // 星号族(* * * / ***)不认 hr —— 是正文场景断记号,按字面段落保留
    expect(mdToHTML('* * *')).toBe('<p>* * *</p>')
    expect(mdToHTML('***')).toBe('<p>***</p>')
  })
  it('ul 星号行守卫:列表间的场景断(* * *)不被吃成列表项,列表就此断开', () => {
    // 修前:内层 ul 收集循环把 `* * *` 吃成列表项 `* *`;修后星号行守卫挡下,交回主循环按字面保留
    expect(mdToHTML('- a\n* * *\n- b'))
      .toBe('<ul><li><p>a</p></li></ul><p>* * *</p><ul><li><p>b</p></li></ul>')
  })
  it('斜体不吞空白内容(星号行不误判)', () => {
    expect(mdToHTML('a * * b')).toBe('<p>a * * b</p>')
    expect(mdToHTML('a *x* b')).toBe('<p>a <em>x</em> b</p>')
  })
  it('HTML 转义', () => {
    expect(mdToHTML('<script>x</script>')).toBe('<p>&lt;script&gt;x&lt;/script&gt;</p>')
  })
  it('空值', () => {
    expect(mdToHTML('')).toBe('<p></p>')
    expect(mdToHTML(null)).toBe('<p></p>')
  })
})

// 迷你 ProseMirror node 造手 —— 仅覆盖 docToMd 读取的表面
// (type.name / attrs / forEach / textContent / text / marks),不引真 schema,快且够用。
const mk = (name, { attrs = {}, children = [], text, marks = [] } = {}) => ({
  type: { name },
  attrs,
  text,
  marks: marks.map((n) => ({ type: { name: n } })),
  textContent: children.length ? children.map((c) => c.textContent ?? c.text ?? '').join('') : (text ?? ''),
  forEach: (fn) => children.forEach((c, i) => fn(c, i, i)),
})
const txt = (s, ...marks) => mk('text', { text: s, marks })
const para = (...kids) => mk('paragraph', { children: kids.length ? kids : [txt('')] })
const heading = (level, ...kids) => mk('heading', { attrs: { level }, children: kids })
const li = (...blocks) => mk('listItem', { children: blocks })
const bullet = (...items) => mk('bulletList', { children: items })
const ordered = (start, ...items) => mk('orderedList', { attrs: { start }, children: items })
const hr = () => mk('horizontalRule')
const doc = (...blocks) => ({ forEach: (fn) => blocks.forEach((b, i) => fn(b, i, i)) })

describe('docToMd(序列化方向)', () => {
  it('hr round-trip:horizontalRule → --- → hr', () => {
    const d = doc(para(txt('甲')), hr(), para(txt('乙')))
    expect(docToMd(d)).toBe('甲\n\n---\n\n乙')
    expect(mdToHTML(docToMd(d))).toBe('<p>甲</p><hr><p>乙</p>')   // 双向不变形
  })
  it('星号行保字面:含 * * * 的段落序列化为字面,不被当作 hr', () => {
    expect(docToMd(doc(para(txt('* * *'))))).toBe('* * *')
    const d = doc(para(txt('甲')), para(txt('* * *')), para(txt('乙')))
    expect(mdToHTML(docToMd(d))).toBe('<p>甲</p><p>* * *</p><p>乙</p>')   // 场景断经 doc→md→html 存活
  })
  it('列表 round-trip:bulletList / orderedList → - / 1.', () => {
    const ul = doc(bullet(li(para(txt('a'))), li(para(txt('b')))))
    expect(docToMd(ul)).toBe('- a\n- b')
    expect(mdToHTML(docToMd(ul))).toBe('<ul><li><p>a</p></li><li><p>b</p></li></ul>')
    const ol = doc(ordered(1, li(para(txt('a'))), li(para(txt('b')))))
    expect(docToMd(ol)).toBe('1. a\n2. b')
    expect(mdToHTML(docToMd(ol))).toBe('<ol><li><p>a</p></li><li><p>b</p></li></ol>')
  })
  it('行内 mark + 标题序列化', () => {
    expect(docToMd(doc(para(txt('粗', 'bold'), txt(' '), txt('斜', 'italic'))))).toBe('**粗** *斜*')
    expect(docToMd(doc(heading(3, txt('看到/听到'))))).toBe('### 看到/听到')
    expect(mdToHTML(docToMd(doc(para(txt('粗', 'bold')))))).toBe('<p><strong>粗</strong></p>')
  })
})
