/** 从梗概读出一章的剧情四格。规则分类，不设比例闸。句子好坏不进这里。 */

export const ACTIONS = ['买', '换', '骗', '抢', '拖', '揭发', '结盟', '背叛', '其他']
export const OUTCOMES = ['成', '败', '半成', '未知']
export const RELATIONS = ['结盟', '反目', '摊牌', '未变']

export const ACTION_TOKEN = {
  买: 'brand',
  换: 'irony',
  骗: 'secret',
  抢: 'danger',
  拖: 'warn',
  揭发: 'ok',
  结盟: 'fore',
  背叛: 'danger',
  其他: 'faint',
}

export const OUTCOME_TOKEN = {
  成: 'ok',
  败: 'danger',
  半成: 'warn',
  未知: 'faint',
}

function textOf(chapter) {
  return String(chapter?.synopsis || chapter?.title || '')
}

function inferFocalizer(chapter) {
  const raw = String(chapter?.focalizer || '').replace(/^role:/, '').trim()
  if (raw) return raw
  const t = textOf(chapter)
  const m = t.match(/^([\u4e00-\u9fff]{1,6})/)
  if (t.includes('柳岸青')) return '柳岸青'
  if (m && !'第在把被从'.includes(m[1][0])) return m[1]
  return '作者全知'
}

function inferAction(t, stored) {
  if (stored && stored !== '其他' && ACTIONS.includes(stored)) return stored
  if (/揭发|摊牌|点破|告发/.test(t)) return '揭发'
  if (/背叛|出卖/.test(t)) return '背叛'
  if (/结盟|联手/.test(t)) return '结盟'
  if (/反目/.test(t)) return '背叛'
  if (/骗|假名|瞒过/.test(t) && !/付/.test(t)) return '骗'
  if (/抢|夺回|抢走/.test(t)) return '抢'
  if (/拖延|拖过|延后三息/.test(t) && !/付/.test(t)) return '拖'
  if (/换(?!成)|兑换/.test(t) && !/付.{0,12}度/.test(t)) return '换'
  if (/付.{0,12}度|买.{0,8}息|买断/.test(t)) return '买'
  return '其他'
}

function inferOutcome(t) {
  if (/成立|完成|稳住|过关/.test(t)) return '成'
  if (/失败|被锁|挡住|挡秤/.test(t)) return '败'
  if (/只差|半枚|仍不|仍未|半成|没合上/.test(t)) return '半成'
  if (/付.{0,12}度/.test(t)) return '半成'
  return '未知'
}

function inferRelation(t) {
  if (/反目|摊牌|背叛/.test(t)) return '反目'
  if (/结盟|联手/.test(t)) return '结盟'
  return '未变'
}

export function plotBeat(chapter) {
  const t = textOf(chapter)
  const stored = String(chapter?.plot_action || '').trim()
  return {
    focalizer: inferFocalizer(chapter),
    action: inferAction(t, stored),
    outcome: inferOutcome(t),
    relation: inferRelation(t),
  }
}
