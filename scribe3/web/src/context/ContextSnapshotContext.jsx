import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { showToast } from '../ui/Toast.jsx'
import { bootstrapSnapshot, reduceSnapshot, semanticIntent } from './contextSnapshot'

// 统一上下文快照 Provider(Task 5)。
//
// 三条路径共用同一个纯 reducer(contextSnapshot.reduceSnapshot):
//   ① 乐观:navigate(patch) 立即本地推进快照,四栏同帧读到同一 revision;
//   ② 确认:服务端确认【串行化】——同一时刻最多一个 navigateContext 在途;
//      在途期间的新意图进单槽 pending(新覆盖旧,只发最后一个 = last-intent-wins),
//      发送时 expected_revision 用**服务端最新已确认 revision**(而非乐观值)。
//      这消灭 pipelined CAS 竞态:A 失败只影响 A,B 以真实基线重试语义,
//      不会出现两步回滚或快照/sel 撕裂;
//   ③ 降级:会话建不起来 / context API 未 mock(旧测试)→ 本地直通,
//      乐观快照即最终快照,revision 本地自增——fail-soft,绝不崩四栏。
//
// 409 stale_context:若用户没有更新的在途操作(seq 命中)→ 整体换成服务端
// latest(服务端赢,FourPaneShell 收到后把 leftTab 对齐过去,见 I-1);
// 若用户已再导航(seq 失配)→ latest 只更新 CAS 基线,不回滚用户最新操作,
// pending 以新基线重试。

const ContextSnapshotCtx = createContext(null)

// 能力默认态与后端 settings 产品默认对齐(snapshot/fabric/inspector 开;editorial 关)。
// 后端 /capabilities 是权威——拉取成功后覆盖;拉取失败时保持与后端一致的 always-on 默认,
// 绝不因失败静默退化成「全关休眠」。
export const DEFAULT_CAPABILITIES = {
  flags: {
    snapshot_v1: true,
    editorial_thread_v1: false,
    memory_fabric_v1: true,
    context_inspector_v1: true,
    assembler_v1: true,
  },
  versions: {},
}

// Provider 缺席(旧测试直渲 FourPaneShell / 旧三栏路径)时的兜底:
// navigate 为 no-op、snapshot 为 null → 消费端全部回退既有本地投影。
// Provider 缺席不是一次“服务端已声明 snapshot_v1 但仍在建会话”的状态：旧的独立
// 消费面和测试会直接渲染 WriteChat，此时没有可绑定的会话，也不能伪造一个。
// 真实产品根由 ContextSnapshotProvider 包住，会立即以 DEFAULT_CAPABILITIES 再向后端
// 取权威能力；这里只把无 Provider 的兼容面显式标为不要求绑定。
const NOOP = {
  snapshot: null, navigate: () => {}, switchThread: () => {}, restoring: false,
  error: null, navigated: false, sessionId: null, snapshotConfirmed: false,
  capabilities: { ...DEFAULT_CAPABILITIES, flags: { ...DEFAULT_CAPABILITIES.flags, snapshot_v1: false } },
}

export function ContextSnapshotProvider({ work, children }) {
  const [snapshot, setSnapshot] = useState(() => bootstrapSnapshot(work))
  // 与可见 snapshot 分离：乐观快照可立即驱动四栏，但在服务端完成 CAS 前不能被
  // ContextInspector 当成可读 trace 的 revision，否则会对尚未持久化的版本发起 404 请求。
  const [snapshotConfirmed, setSnapshotConfirmed] = useState(true)
  // 首帧即标为恢复中，堵住 createContextSession 的 effect 尚未调度、但写作台已可输入的
  // 微小窗口。没有该 API 的旧部署仍从首帧按本地直通模式运行。
  const [restoring, setRestoring] = useState(() => typeof api?.createContextSession === 'function')
  const [error, setError] = useState(null)
  // navigated:本客户端是否已发生过语义导航——投影守卫用(服务端初始快照的
  // 默认 entry 不应抢走用户 leftTab 偏好,导航发生后快照才成为渲染事实源)。
  const [navigated, setNavigated] = useState(false)
  // Task 16-B:服务端灰度能力(后端 /capabilities 权威下发)。默认全关;拉取失败保持默认,
  // 消费端据此门控就绪能力,而非读 localStorage。additive:不改任何既有导航/降级行为。
  const [capabilities, setCapabilities] = useState(DEFAULT_CAPABILITIES)
  const modeRef = useRef('local')          // 'local'(降级直通)| 'server'(乐观+串行确认)
  const snapRef = useRef(snapshot)         // 同步读最新【乐观】快照(事件回调连发时不吃陈旧 state)
  const confirmedRef = useRef(null)        // 服务端最新【已确认】快照 = CAS 基线(session_id/revision 取此)
  const inflightRef = useRef(false)        // 在途互斥:同一时刻最多一个 navigateContext
  const pendingRef = useRef(null)          // 单槽 pending({reason}):在途期间新意图覆盖旧的
  const navSeqRef = useRef(0)              // 导航序号:过期确认不覆盖可见快照(last-write-wins)
  const epochRef = useRef(0)               // 会话代际:work 切换 +1,旧代际的一切回调整体作废

  const commit = useCallback((snap) => {
    snapRef.current = snap
    setSnapshot(snap)
  }, [])

  // 把 pending 的语义状态发给服务端(串行:在途时不发,由上一个确认的 finally 续发)。
  // wire intent 从【乐观快照现值】构造(last-intent-wins 的合并结果),
  // expected_revision 钉在【已确认基线】上——这是 I-2 竞态修复的核心。
  const flushRef = useRef(() => {})
  const flush = useCallback(() => {
    if (inflightRef.current) return
    if (!pendingRef.current) return
    const confirmed = confirmedRef.current
    if (!confirmed || modeRef.current !== 'server' || typeof api?.navigateContext !== 'function') {
      pendingRef.current = null
      return
    }
    const pending = pendingRef.current
    pendingRef.current = null
    const local = snapRef.current
    const wire = {
      navigation_id: crypto.randomUUID(),   // 每次 CAS 尝试都是一条新导航(后端幂等键)
      expected_revision: confirmed.revision,
      entry: local.entry,
      directory_path: [...(local.directory_path || [])],
      focus: local.focus,
      detail_route: local.detail_route,
      chapter: local.chapter ?? null,
      phase: local.phase ?? null,
      focalizer: local.focalizer ?? null,
      reason: pending.reason,
    }
    const epoch = epochRef.current
    const seq = navSeqRef.current
    inflightRef.current = true
    // 同步发出(测试与调用方可同帧观察);同步抛错并入统一的失败路径
    let sent
    try {
      sent = Promise.resolve(api.navigateContext(confirmed.session_id, wire))
    } catch (e) {
      sent = Promise.reject(e)
    }
    sent
      .then((snap) => {
        if (epoch !== epochRef.current) return   // work 已切换:旧代际确认整体作废
        if (snap && typeof snap === 'object' && typeof snap.revision === 'number') {
          confirmedRef.current = snap            // 基线永远推进(即使不覆盖可见快照)
          if (seq === navSeqRef.current) {
            commit(snap)                         // 无更新操作在后 → 服务端快照整体替换
            setSnapshotConfirmed(true)
            setError(null)                       // 错误不常驻:成功即清,防 toast 重复
          }
          // seq 失配 = 用户已再导航:确认只更新基线,可见快照留在用户最新操作上
        }
      })
      .catch((e) => {
        if (epoch !== epochRef.current) return
        const detail = e?.status === 409 ? e?.body?.detail : null
        if (detail?.code === 'stale_context' && detail.latest) {
          confirmedRef.current = detail.latest   // 新 CAS 基线(pending 将以它重试语义)
          if (seq === navSeqRef.current) {
            // 服务端 latest 赢:整体替换;FourPaneShell 据此把 leftTab 对齐过去(I-1)
            commit(detail.latest)
            setSnapshotConfirmed(true)
            setError({ code: 'stale_context', message: '上下文已在另一窗口更新' })
          }
          // seq 失配:用户已再导航 → latest 不回滚用户最新操作,只当基线用
        } else if (seq === navSeqRef.current) {
          // 同步失败不回滚本地投影(用户所见即所选),只报告错误——fail-soft
          setError({ code: 'navigate_failed', message: e?.body?.detail?.message || e?.message || '上下文同步失败' })
        }
      })
      .finally(() => {
        if (epoch !== epochRef.current) return
        inflightRef.current = false
        flushRef.current()                       // 在途期间若积了 pending,现在续发
      })
  }, [commit])
  flushRef.current = flush

  const navigate = useCallback((patch) => {
    const current = snapRef.current
    if (!current || !patch) return
    let intent
    let optimistic
    try {
      intent = semanticIntent(current, patch)
      optimistic = reduceSnapshot(current, intent)   // reducer 已内置乐观快照 hash 失效
    } catch {
      // intent 由当前快照同步生成,本地永不 stale;构造失败(如 crypto 缺席)按 no-op 降级
      return
    }
    commit(optimistic)
    setNavigated(true)
    // 降级直通:无服务端会话 → 乐观快照即最终快照(会话建成时经 restore 补发对齐)
    if (modeRef.current !== 'server') return
    setSnapshotConfirmed(false)
    navSeqRef.current += 1
    pendingRef.current = { reason: intent.reason }   // 单槽:新意图覆盖旧 pending
    flush()
  }, [commit, flush])

  useEffect(() => {
    let cancelled = false
    // 切书:代际 +1,废弃一切在途确认;回到本地基座重建会话
    epochRef.current += 1
    navSeqRef.current += 1
    modeRef.current = 'local'
    inflightRef.current = false
    pendingRef.current = null
    confirmedRef.current = null
    commit(bootstrapSnapshot(work))
    setSnapshotConfirmed(true)
    setError(null)
    setNavigated(false)
    // 优雅降级铁律:api.createContextSession 不存在(旧测试未 mock / 精简 api)
    // → 静默进入本地直通模式,统一上下文的存在不应被感知。
    if (typeof api?.createContextSession !== 'function') { setRestoring(false); return undefined }
    setRestoring(true)
    // P0a 当前线程解析链:localStorage 偏好 → 后端 active 默认。**每次向下切换必须可见**:
    // 偏好线程已归档/删除(404/409)→ toast 明示 + 清键 + 回默认重建一次;二次失败走既有
    // error 路径(context_session_failed 显式报错)。绝不静默换线程(零降级)。
    const wKey = work ?? api?.getWork?.() ?? 'main'
    const preferredKey = 's3.thread.current.' + wKey
    let preferred = null
    try { preferred = localStorage.getItem(preferredKey) || null } catch { /* */ }
    const create = (tid) => api.createContextSession({
      work: wKey, ...(tid ? { thread_id: tid } : {}) })
    Promise.resolve()
      .then(() => create(preferred))
      .catch((e) => {
        if (preferred && (e?.status === 404 || e?.status === 409)) {
          try { localStorage.removeItem(preferredKey) } catch { /* */ }
          showToast('原会话已归档/删除,已切到默认会话', { tone: 'info' })
          return create(null)
        }
        throw e
      })
      .then((snap) => {
        if (cancelled) return
        if (!snap || typeof snap !== 'object' || typeof snap.revision !== 'number') return
        modeRef.current = 'server'
        confirmedRef.current = snap
        const local = snapRef.current
        if (local?.navigation_id) {
          // 会话建立前用户已在本地导航过:不用服务端初始快照覆盖用户所在位置,
          // 而是把当前语义状态补发一次(reason=restore),确认后自然对齐(I-3③)。
          pendingRef.current = { reason: 'restore' }
          flush()
        } else {
          commit(snap)
          setSnapshotConfirmed(true)
        }
      })
      .catch((e) => {
        // 创建失败 → error 状态但不崩四栏:维持本地直通模式(navigate 直通本地投影)
        if (!cancelled) setError({ code: 'context_session_failed', message: e?.body?.detail?.message || e?.message || '上下文会话创建失败' })
      })
      .finally(() => { if (!cancelled) setRestoring(false) })
    return () => { cancelled = true }
  }, [work, commit, flush])

  // Task 16-B:挂载时拉一次后端能力(全局、不随 work 变)。fail-soft:api 缺席
  // (旧测试/精简 api)或请求失败 → 保持默认全关,前端不越权开启未就绪的服务端能力。
  useEffect(() => {
    if (typeof api?.fetchCapabilities !== 'function') return undefined
    let cancelled = false
    Promise.resolve()
      .then(() => api.fetchCapabilities())
      .then((caps) => {
        if (cancelled || !caps || typeof caps !== 'object') return
        setCapabilities({
          flags: { ...DEFAULT_CAPABILITIES.flags, ...(caps.flags || {}) },
          versions: caps.versions || {},
        })
      })
      .catch(() => { /* 保持默认全关 */ })
    return () => { cancelled = true }
  }, [])

  // P0a:切换主编会话=重建 context session 绑新线程(snapshot.thread_id 是前端线程唯一
  // 事实源,不裂)。成功:换绑 + localStorage 记偏好;失败:danger toast + **当前状态不变**
  // (零降级:绝不半切/静默回落)。
  const switchThread = useCallback((threadId) => {
    if (!threadId || typeof api?.createContextSession !== 'function') return Promise.resolve()
    const wKey = work ?? api?.getWork?.() ?? 'main'
    return Promise.resolve()
      .then(() => api.createContextSession({ work: wKey, thread_id: threadId }))
      .then((snap) => {
        if (!snap || typeof snap !== 'object' || typeof snap.revision !== 'number') {
          throw new Error('会话快照无效')
        }
        epochRef.current += 1            // 旧线程会话的在途确认整体作废(同切书语义)
        navSeqRef.current += 1
        inflightRef.current = false
        pendingRef.current = null
        modeRef.current = 'server'
        confirmedRef.current = snap
        commit(snap)
        setSnapshotConfirmed(true)
        setError(null)
        try { localStorage.setItem('s3.thread.current.' + wKey, threadId) } catch { /* */ }
      })
      .catch((e) => {
        showToast(`切换会话失败:${e?.body?.detail?.message || e?.body?.detail || e?.message || ''}`,
                  { tone: 'danger' })
      })
  }, [work, commit])

  // Task 6:显式暴露只读 sessionId(消费端绑定 LLM 调用的会话游标来源;
  // 降级/本地直通模式下快照无 session_id → null)。
  const sessionId = snapshot?.session_id ?? null
  const value = useMemo(
    () => ({ snapshot, navigate, switchThread, restoring, error, navigated, sessionId, snapshotConfirmed, capabilities }),
    [snapshot, navigate, switchThread, restoring, error, navigated, sessionId, snapshotConfirmed, capabilities],
  )
  return <ContextSnapshotCtx.Provider value={value}>{children}</ContextSnapshotCtx.Provider>
}

export function useContextSnapshot() {
  return useContext(ContextSnapshotCtx) ?? NOOP
}
