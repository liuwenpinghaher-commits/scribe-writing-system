// 轻量 markdown ↔ TipTap(StarterKit)转换,零依赖。
// 口径约定(与 RichEditor 序列化一致,保证 round-trip 稳定):
// - 块间以空行(\n\n)分隔;段内单个 \n = hardBreak(保留既有纯文本的行结构)。
// - 支持:# 标题(1-6)、- / * 无序列表、1. 有序列表、> 引用、--- 分隔线、``` 围栏代码。
// - 行内:**粗** *斜* ~~删~~ `码`。纯文本(无 md 记号)进出完全不变形。

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// 行内 md → html(输入已 escape)
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+(?:\*[^*]+)*)\*\*/g, '<strong>$1</strong>')
    .replace(/~~([^~]+)~~/g, '<s>$1</s>')
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')
}
const il = (s) => inline(esc(s))

export function mdToHTML(md) {
  const lines = (md || '').replace(/\r\n/g, '\n').split('\n')
  const out = []
  let para = []
  const flushPara = () => {
    if (!para.length) return
    out.push('<p>' + para.map(il).join('<br>') + '</p>')
    para = []
  }
  let i = 0
  while (i < lines.length) {
    const raw = lines[i]
    const t = raw.trim()
    let m
    if (!t) { flushPara(); i++; continue }
    if ((m = /^(#{1,6})\s+(.*)$/.exec(t))) {
      flushPara(); out.push(`<h${m[1].length}>${il(m[2])}</h${m[1].length}>`); i++; continue
    }
    if (/^(-{3,}|_{3,}|\*{3,})$/.test(t.replace(/\s/g, ''))) { flushPara(); out.push('<hr>'); i++; continue }
    if (t.startsWith('```')) {
      flushPara()
      const code = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) { code.push(lines[i]); i++ }
      i++ // 跳过收尾 ```
      out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>')
      continue
    }
    if (/^[-*+]\s+/.test(t)) {
      flushPara()
      const items = []
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) { items.push(lines[i].trim().replace(/^[-*+]\s+/, '')); i++ }
      out.push('<ul>' + items.map((x) => `<li><p>${il(x)}</p></li>`).join('') + '</ul>')
      continue
    }
    if (/^\d+[.)]\s+/.test(t)) {
      flushPara()
      const items = []
      while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) { items.push(lines[i].trim().replace(/^\d+[.)]\s+/, '')); i++ }
      out.push('<ol>' + items.map((x) => `<li><p>${il(x)}</p></li>`).join('') + '</ol>')
      continue
    }
    if (/^>\s?/.test(t)) {
      flushPara()
      const qs = []
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) { qs.push(lines[i].trim().replace(/^>\s?/, '')); i++ }
      out.push('<blockquote><p>' + qs.map(il).join('<br>') + '</p></blockquote>')
      continue
    }
    para.push(raw)
    i++
  }
  flushPara()
  return out.join('') || '<p></p>'
}

// ——— TipTap doc(ProseMirror node)→ markdown ———

function inlineMd(node) {
  let s = ''
  node.forEach((child) => {
    if (child.type.name === 'hardBreak') { s += '\n'; return }
    let t = child.text || ''
    if (!t) return
    const marks = child.marks || []
    const has = (n) => marks.some((mk) => mk.type.name === n)
    if (has('code')) t = '`' + t + '`'
    else {
      if (has('bold')) t = `**${t}**`
      if (has('italic')) t = `*${t}*`
      if (has('strike')) t = `~~${t}~~`
    }
    s += t
  })
  return s
}

function listItemMd(li) {
  const parts = []
  li.forEach((c) => { const b = serializeBlock(c); if (b) parts.push(b.replace(/\n/g, ' ')) })
  return parts.join(' ')
}

function serializeBlock(node) {
  switch (node.type.name) {
    case 'heading': return '#'.repeat(node.attrs.level || 1) + ' ' + inlineMd(node)
    case 'paragraph': return inlineMd(node)
    case 'bulletList': {
      const items = []
      node.forEach((li) => items.push('- ' + listItemMd(li)))
      return items.join('\n')
    }
    case 'orderedList': {
      const items = []
      let n = node.attrs.start || 1
      node.forEach((li) => items.push(`${n++}. ` + listItemMd(li)))
      return items.join('\n')
    }
    case 'blockquote': {
      const inner = []
      node.forEach((c) => { const b = serializeBlock(c); if (b != null) inner.push(b) })
      return inner.join('\n\n').split('\n').map((l) => '> ' + l).join('\n')
    }
    case 'codeBlock': return '```\n' + node.textContent + '\n```'
    case 'horizontalRule': return '---'
    default: return node.textContent
  }
}

export function docToMd(doc) {
  const blocks = []
  doc.forEach((node) => { blocks.push(serializeBlock(node) ?? '') })
  const md = blocks.join('\n\n')
  return md.trim() === '' ? '' : md
}
