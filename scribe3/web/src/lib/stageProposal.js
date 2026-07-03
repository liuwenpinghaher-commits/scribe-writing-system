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
 * ``` / ~~~ 码块整段跳过;无列表标记时按非空行拆。行内 markdown(加粗等)原样保留。
 * 剥标记按 markdown 规范收紧:`- ` 后必须有空白(`-3度`/`**粗体**` 不误剥);
 * 数字序号后不得紧跟数字(`3.5万字` 是小数不是序号)。
 */
export function beatsFromMarkdown(md) {
  const items = []
  let inFence = false
  for (const raw of (md || '').split('\n')) {
    const l = raw.trim()
    if (/^(```|~~~)/.test(l)) { inFence = !inFence; continue }
    if (inFence) continue
    if (!l) continue
    if (/^#{1,6}\s/.test(l)) continue
    const t = l.replace(/^(?:[-*+]\s+|\d+[.、)](?!\d)\s*|[一二三四五六七八九十]+[、.]\s*)/, '').trim()
    if (t) items.push(t)
  }
  return items
}

/**
 * chatWrite 兜底发布的正文选择(块二质量审查必修,抽纯函数供单测):
 * - 收到过 proposal 收尾事件 → null(已按围栏稿发布,绝不重发/覆盖);
 * - 围栏开过但没收尾(LLM 在围栏内被 max-tokens 截断;后端 ProposalParser.flush 对未闭合
 *   围栏只吐 delta、不补 proposal 收尾)→ 发已累积的部分正文 propAcc——截断稿仍是正文,
 *   发 turnText 会把讨论前言当成果、丢掉半截稿;
 * - 整轮无围栏 → 发纯 delta 累积 turnText。
 */
export function fallbackProposalText({ gotProposal, propOpen, propAcc, turnText }) {
  if (gotProposal) return null
  return propOpen ? propAcc : turnText
}
