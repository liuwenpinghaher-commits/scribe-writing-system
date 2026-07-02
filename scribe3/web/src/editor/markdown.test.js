import { describe, it, expect } from 'vitest'
import { mdToHTML } from './markdown'

// docToMd 需要 PM node,round-trip 由真机验收覆盖;此处只测 mdToHTML 的解析口径。
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
  it('HTML 转义', () => {
    expect(mdToHTML('<script>x</script>')).toBe('<p>&lt;script&gt;x&lt;/script&gt;</p>')
  })
  it('空值', () => {
    expect(mdToHTML('')).toBe('<p></p>')
    expect(mdToHTML(null)).toBe('<p></p>')
  })
})
