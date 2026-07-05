// /causal 契约(批D P1-5 假绿根治):后端返回 {no_event_data: bool, violations: [{event, reason}]}。
// 用对象区分「因果完整」(有事件、无违规)与「根本没有事件数据可校验」(event 表对该章空),
// 杜绝空表恒返 [] 被前端 `.length` 读作「因果完整✅」的假绿(undefined>0=false→永久真绿)。
// 本函数把该返回体(含 null 初值 / 旧裸数组契约)归一化成三态,供状态条 + 校验徽章「同源」消费:
//   { state: 'violations', count: N }  有因果违规(N=violations.length,danger)
//   { state: 'no-data',    count: 0 }  无事件数据可校验(中性,非绿,不计入徽章)
//   { state: 'complete',   count: 0 }  有事件且无违规(真绿)
// count 仅在 violations 态 > 0 → verifyIssues 不会把「无数据」误算成一处问题。
export function causalStatus(causal) {
  // null/undefined:初值或拉取失败 → 中性「无数据」,绝不假绿(首帧不闪 complete)
  if (causal == null) return { state: 'no-data', count: 0 }
  // 旧裸数组契约兜底(万一命中过期缓存 / 混版后端回退):按违规数解读
  if (Array.isArray(causal)) {
    return causal.length > 0
      ? { state: 'violations', count: causal.length }
      : { state: 'complete', count: 0 }
  }
  const violations = Array.isArray(causal.violations) ? causal.violations : []
  // 违规优先:即便后端异常同时置 no_event_data,也不吞掉真实违规
  if (violations.length > 0) return { state: 'violations', count: violations.length }
  if (causal.no_event_data) return { state: 'no-data', count: 0 }
  return { state: 'complete', count: 0 }
}
