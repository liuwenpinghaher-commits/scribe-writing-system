// 容器卡片墙/大纲表的色彩编码:label 语义色 + POV 稳定哈希色。
// 复用全站 --color-* token,不引入新调色板。

// label(状态)→ CSS 变量 token
export const LABELS = ['idea', 'draft', 'revise', 'done', 'beat']
export const LABEL_META = {
  idea:   { token: 'faint',  text: '构思' },
  draft:  { token: 'irony',  text: '初稿' },
  revise: { token: 'warn',   text: '待改' },
  done:   { token: 'ok',     text: '完成' },
  beat:   { token: 'secret', text: '节拍' },
}

// POV 稳定哈希:同一 focalizer 恒定取同一色(从一组语义 token 里挑)
const POV_TOKENS = ['brand', 'fore', 'irony', 'secret', 'ok', 'warn', 'danger']
function hashStr(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}
export function povToken(focalizer) {
  if (!focalizer) return 'faint'
  return POV_TOKENS[hashStr(focalizer) % POV_TOKENS.length]
}

// 给定章 + 模式 → CSS 颜色字符串(用于色条 background)
export function cardColorVar(chapter, mode) {
  let token = 'line'
  if (mode === 'pov') token = povToken(chapter.focalizer)
  else { // 'status'(默认)
    const m = LABEL_META[chapter.label]
    token = m ? m.token : 'line'
  }
  return `var(--color-${token})`
}

// focalizer → 展示名:剥 "role:" 前缀;空 = 作者全知(未设 POV 即全知叙述)。
// 视角决定该章限知(该章只写 focalizer 知道/看到的),故全书大纲章行常显。
export function povLabel(focalizer) {
  const f = String(focalizer || '').replace(/^role:/, '').trim()
  return f || '作者全知'
}
// 章行视角的轻提示(tooltip 文案,统一一处)
export const POV_HINT = '视角决定该章限知(只写该视角知道/看到的)'

// 字数 → 紧凑显示(1234 → 1.2k)
export function wcLabel(n) {
  const v = n || 0
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
}
