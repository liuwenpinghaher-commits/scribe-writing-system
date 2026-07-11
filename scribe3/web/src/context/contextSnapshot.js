// 统一上下文快照 · 纯 reducer 层(Task 5)。
//
// 为什么是纯函数:四栏的语义状态此前是"双源"——入口在 FourPaneShell 内部
// state(leftTab),条目在 BinderLayout 共享 sel——两源各自变化时四栏可能
// 短暂读到互相矛盾的组合。收敛为「快照 + 意图」后,乐观更新 / 服务端确认 /
// 降级直通三条路径复用同一套推进规则,revision 单调递增,四栏永远读同一份。
// 形状与后端 context_models.ContextSnapshot / NavigationIntent 对齐。

export function reduceSnapshot(current, intent) {
  if (!current) throw new Error('context_snapshot_missing')
  // CAS 语义与后端 advance_context 一致:失配即拒绝,绝不悄悄覆盖
  if (intent.expected_revision !== current.revision) throw new Error('stale_context')
  return {
    ...current,
    entry: intent.entry,
    directory_path: [...intent.directory_path],
    focus: { ...intent.focus },
    detail_route: intent.detail_route,
    // 完整语义状态:intent 未带的字段归 null,不残留上一份快照的旧值
    chapter: intent.chapter ?? null,
    phase: intent.phase ?? null,
    focalizer: intent.focalizer ?? null,
    navigation_id: intent.navigation_id,
    previous_revision: current.revision,
    revision: current.revision + 1,
    // 乐观快照的 hash 一律失效(hash 是服务端快照的身份指纹,本地推进即失真)。
    // 这是 reducer 的责任,不泄漏给调用方——确认前发 LLM 请求应继续用带 hash 的旧快照
    context_hash: null,
  }
}

// 由"局部语义 patch"构造一条完整 NavigationIntent:navigation_id 全新
// (后端幂等键),expected_revision 钉在当前快照(CAS 凭据),entry/path
// 未给时沿用快照现值——保证每个语义动作只发【一个】完整意图。
export function semanticIntent(snapshot, patch) {
  return {
    navigation_id: crypto.randomUUID(),
    expected_revision: snapshot.revision,
    entry: patch.entry ?? snapshot.entry,
    directory_path: patch.directory_path ?? snapshot.directory_path,
    focus: patch.focus,
    detail_route: patch.detail_route,
    chapter: patch.chapter ?? null,
    phase: patch.phase ?? null,
    focalizer: patch.focalizer ?? null,
    reason: patch.reason,
  }
}

// 本地引导快照:Provider 尚未拿到(或拿不到)服务端会话时的降级基座。
// entry/focus 留空 → 消费端(FourPaneShell)回退既有本地投影(leftTab 偏好),
// 统一上下文不抢夺现状——fail-soft 是本仓宪法。
export function bootstrapSnapshot(work) {
  return {
    session_id: null,
    work: work ?? null,
    revision: 0,
    entry: null,
    directory_path: [],
    focus: null,
    detail_route: null,
    chapter: null,
    phase: null,
    focalizer: null,
    previous_revision: null,
    navigation_id: null,
    context_hash: null,
  }
}

// 后端 FocusType 白名单(context_models.FocusType)。未列入的 node.type 必须
// 兜底 'view',否则 NavigationIntent 校验 422、整条导航记录丢失。
const FOCUS_TYPES = new Set([
  'entry', 'view', 'chapter', 'scene', 'character', 'fact', 'event',
  'promise', 'motif', 'material', 'review_issue', 'selection',
])
// 前端节点类型 → 后端焦点类型的别名(与 targetNavigation 的命名习惯对齐)
const FOCUS_ALIAS = {
  role: 'character',
  proposition: 'fact',
  frame_fact: 'fact',
  promise_view: 'promise',
  motif_view: 'motif',
  entry_capability: 'entry',
}
// 后端 PhaseName 枚举:垃圾 phase 不入意图(后端同样会拒)
const PHASES = new Set(['outline', 'beats', 'deduce', 'draft', 'final'])

export function focusForNode(node) {
  if (!node) return { type: 'view', id: 'view:empty', label: '' }
  const raw = String(node.type || '')
  const type = FOCUS_ALIAS[raw] || (FOCUS_TYPES.has(raw) ? raw : 'view')
  if ((type === 'chapter' || type === 'scene') && node.ref != null) {
    return { type, id: `chapter:${node.ref}`, label: node.label || '' }
  }
  return { type, id: String(node.id || `${type}:${node.ref ?? 'unknown'}`), label: node.label || '' }
}

// detail_route 是显示/审计用字符串:章统一 chapter:seq,其余用节点 id
export function detailRouteForNode(node) {
  if (!node) return 'empty'
  if ((node.type === 'chapter' || node.type === 'scene') && node.ref != null) return `chapter:${node.ref}`
  return String(node.id || node.type || 'unknown')
}

// 语义动作"激活一级入口"的完整 patch
export function entryPatch(key, label = '') {
  return {
    entry: key,
    directory_path: [key],
    focus: { type: 'entry', id: `entry:${key}`, label },
    detail_route: `entry:${key}`,
    reason: 'entry',
  }
}

// 语义动作"选中目录/详情条目"的完整 patch;entryKey 给出时同步收敛 entry+path
export function nodePatch(node, entryKey) {
  const isChapterish = node?.type === 'chapter' || node?.type === 'scene'
  const seq = isChapterish ? Number(node.ref) : NaN
  const patch = {
    focus: focusForNode(node),
    detail_route: detailRouteForNode(node),
    chapter: Number.isFinite(seq) ? seq : null,
    phase: isChapterish && PHASES.has(node?.phase) ? node.phase : null,
    reason: 'item',
  }
  if (entryKey) {
    patch.entry = entryKey
    patch.directory_path = node?.id ? [entryKey, String(node.id)] : [entryKey]
  }
  return patch
}
