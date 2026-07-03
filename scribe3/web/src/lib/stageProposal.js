// 块二:主编讨论↔中区闭环的纯逻辑(proposal 匹配 + 节拍解析),便于单测。
//
// stageProposal 形状:{ phase, seq, target, content, ts }
//  - phase: 'outline' | 'beats' | 'deduce' | 'draft'(UI 阶段名)
//  - seq:   章号(发布时捕获)
//  - target:演绎的落点('truth' 或 character_id 如 'role:崔判');其余阶段 null
//  - content:主编生成的 markdown 文本
//  - ts:    递增计数器(区分「同一内容再次生成」以便重新提示,不依赖时钟)

/** 校验 proposal 与当前接收端(phase/seq/target)匹配才返回,否则 null——切章/切阶段/切演绎目标后旧 proposal 不得错落。 */
export function matchStageProposal(p, { phase, seq, target = null }) {
  if (!p) return null
  if (p.phase !== phase || p.seq !== seq) return null
  if ((p.target ?? null) !== (target ?? null)) return null
  if (!(p.content || '').trim()) return null
  return p
}

/**
 * 主编生成的节拍 markdown → 条目文本数组。
 * 优先剥行首列表标记(- * + / 1. 1、 1) / 一、);标题行(#)是分组名不是条目,跳过;
 * 无列表标记时按非空行拆。条目内的行内 markdown(加粗等)原样保留(节拍编辑器就是 markdown)。
 */
export function beatsFromMarkdown(md) {
  const items = []
  for (const raw of (md || '').split('\n')) {
    const l = raw.trim()
    if (!l) continue
    if (/^#{1,6}\s/.test(l)) continue
    const t = l.replace(/^([-*+]|\d+[.、)]|[一二三四五六七八九十]+[、.])\s*/, '').trim()
    if (t) items.push(t)
  }
  return items
}
