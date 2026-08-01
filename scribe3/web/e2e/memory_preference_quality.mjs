// 跨会话偏好消费的可解释质量闸：判定叙事动作，不能把自然措辞绑死在“借”一个字上。
const EBB_SIGNAL = /退潮|潮退|潮水[^。！？\n]{0,16}[退落]|水位[^。！？\n]{0,16}[退落]/
const EBB_LEVERAGE_SIGNALS = [
  /借[^。！？\n]{0,8}?(?:回溜|回水|退势|潮|势|力|着)/,
  /趁(?:着)?[^。！？\n]{0,6}(?:回溜|退溜|退势|退潮)/,
  /(?:踏着|顺着|借着)[^。！？\n]{0,8}(?:回溜|退溜|退势|退潮)/,
]

/**
 * 作者偏好“先退潮借力，再承担风险”的最小语义判定。
 * 必须先交代退潮，再出现对退势/回溜的主动利用；单纯把退潮当背景不通过。
 */
export function consumesEbbLeveragePreference(prose) {
  const text = String(prose || '')
  const ebbIndex = text.search(EBB_SIGNAL)
  if (ebbIndex < 0) return false
  return EBB_LEVERAGE_SIGNALS.some((signal) => {
    const match = text.match(signal)
    // “趁退潮借水”里主动利用动作从“退潮”前一个字开始；只比较动作起点会
    // 把这种自然表达误判为先借力后退潮。要求动作短语与退潮信号重叠或在其后，
    // 仍能拒绝“先借回水、后才交代潮退”的倒置因果。
    return Boolean(match && match.index !== undefined && match.index + match[0].length > ebbIndex)
  })
}
