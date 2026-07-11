import { targetNodeToSelection } from './targetNavigation'

// ContextSnapshot → 四栏选中态(sel)的纯投影层(Task 5)。
//
// 为什么需要它:ContextSnapshot 记录的是「语义事实」(entry/focus/detail_route/
// chapter/phase),而栏3/栏4 的组件吃的是老 sel 合同({mode,node}/{mode,view})。
// 快照推进(尤其是跨窗口 409 对齐到 latest)后,若四栏仍读本地 sel,就会出现
// "revision 已翻页、内容还停在旧条目"的撕裂。这个纯函数把快照安全地投影成 sel,
// 让四栏与 revision 同帧翻页。
//
// 节点形状不自己发明:一律复用 targetNodeToSelection(本地导航的权威节点构造器),
// 逐类型产出与它同形的节点。这条铁律修掉了 I-1——codex/material 节点的 ref 全仓
// 约定是【去前缀本地 id】('甲' 而非 'character:甲'):
//   · CodexDetail.pickRow 按 localOf(row) === node.ref 匹配;
//   · PropositionDetail 拼 fact:${node.ref};
//   · MaterialDetail 按 row.id === node.ref。
// 若投影自造全限定 id 当 ref,跨窗口 409 对齐到 codex/material 对象时栏3 会空白——
// 而跨窗口对齐正是本特性的立身路径。
//
// 三条安全边界(缺一即回归既有原子性用例):
//   ① 路由相同 → 返回【同一对象引用】(toBe),不生成等值副本:既有原子用例靠引用
//      不变判定"未撕裂",副本会触发无谓 re-render 与断言回归;也保留本地 sel 里
//      比快照更丰富的字段(meta/payload 等)。
//   ② 白名单 type 才投影,未知 focus 类型一律回退 fallbackSel——绝不臆造节点。
//   ③ 章/场景判据以 focus.type 为准(见下),不用 ambient chapter 误判。

// 后端 FocusType → targetNodeToSelection 能识别的 hint type。review_issue 走 'issue'
// 触发 issueNode(补 payload/target_node,并让 DetailPane 路由到 ReviewIssueDetail);
// promise/motif 经 targetNodeToSelection 产出 promise_view/motif_view,直达
// PromiseDetailPane/MotifDetailPane(而非落到 CODEX_LEAF 的 CodexDetail)——顺带闭合 M-1。
const DELEGATE_TYPE = {
  character: 'character',
  material: 'material',
  promise: 'promise',
  motif: 'motif',
  fact: 'fact',
  review_issue: 'issue',
}

// 把本地 sel 归一成 detail_route 同构的字符串,用于与快照 detail_route 比对是否"同一处"。
// 章/场景统一 chapter:seq;view 用 view:key;空选为 empty。
const routeOf = (sel) => {
  const node = sel?.node
  if (!node) return sel?.mode === 'view' ? `view:${sel.viewKey}` : 'empty'
  if (node.type === 'chapter' || node.type === 'scene') return `chapter:${node.type === 'scene' ? node.ref?.seq : node.ref}`
  return String(node.id || node.type)
}

// 从 focus.id 剥掉首段 `前缀:`,得【去前缀本地 id】——promise/motif/material 的 ref 靠它回填
const localRef = (id) => String(id || '').replace(/^[^:]+:/, '')

export function selectionFromSnapshot(snapshot, fallbackSel) {
  // 快照无 focus(降级基座 / 未导航)→ 不投影,维持本地 sel 现状
  if (!snapshot?.focus) return fallbackSel
  // ① 路由相同 → 原样返回本地 sel(同引用 + 保留更丰富字段)
  if (routeOf(fallbackSel) === snapshot.detail_route) return fallbackSel
  const focus = snapshot.focus
  // 视图入口:回填 view 模式(空视图无意义 → 回退)
  if (focus.type === 'view') {
    const viewKey = String(focus.id || '').replace(/^view:/, '')
    return viewKey && viewKey !== 'empty' ? { mode: 'view', viewKey } : fallbackSel
  }
  // ③ 章/场景:判据以 focus.type 为准(I-3)。绝不用 `snapshot.chapter != null`,否则
  // 一个带 ambient chapter 的角色 focus 会被误投成章节(角色 label 挂到章上)。
  // seq 优先 snapshot.chapter,退而解析 detail_route 的 chapter:seq;带上 phase。
  if (focus.type === 'chapter' || focus.type === 'scene') {
    const seq = Number(snapshot.chapter ?? String(snapshot.detail_route || '').split(':')[1])
    if (!Number.isFinite(seq)) return fallbackSel
    return { mode: 'node', node: { id: `ch:${seq}`, type: 'chapter', ref: seq, label: focus.label || `${seq}`, phase: snapshot.phase || undefined } }
  }
  // ② 其余条目类:委托 targetNodeToSelection 产出同形节点(ref = 去前缀本地 id)
  const hint = DELEGATE_TYPE[focus.type]
  if (!hint) return fallbackSel
  const target = { type: hint, id: focus.id, label: focus.label || focus.id }
  // review_issue 的章号由 issueNode 从 chapter/target_node 推:别把剥出的 id 尾段
  // 当 ref 塞进去污染成假章号;其余类型 ref = 去前缀本地 id。
  if (hint !== 'issue') target.ref = localRef(focus.id)
  const selected = targetNodeToSelection(target)
  return selected?.node ? { mode: 'node', node: selected.node } : fallbackSel
}
