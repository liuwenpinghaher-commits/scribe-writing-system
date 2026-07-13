import { useEffect, useState } from 'react'
import { ChevronRight, Eye, ShieldAlert } from 'lucide-react'
import { api } from '../api'
import { useContextSnapshot } from './ContextSnapshotContext'

// 统一上下文与记忆系统 · Task 14:上下文检查器 + 记忆溯源 UI。
//
// 让"主编到底看到了什么、为什么选这条记忆、为什么弃那条"透明可审计。三层:
//   第1层(常显):当前 focus / revision / 降级状态("主编知道你在看什么")。
//   第2层(展开):Global/Canonical/Recent/Procedural/Reference/Uncertainty 各块 token + 来源数。
//   第3层(证据):每条 source id / 时态 / 信心 / 选中理由;私密只显"秘密事实已屏蔽"(服务端已抹 value)。
//
// 诚实边界:真实 trace 数据待 Task 16 检索接进生产 prompt 后填充。当前多数快照版本
//   无溯源(GET trace 返 404)→ 第3层显"未检索到证据"(而非"没有相关事实"——
//   没检索≠没有相关事实)。

// 第2层六块(名称与 context_models.ContextBlock 枚举对齐)
const BLOCK_DEFS = [
  { key: 'global', label: 'Global' },
  { key: 'canonical', label: 'Canonical' },
  { key: 'recent', label: 'Recent' },
  { key: 'procedural', label: 'Procedural' },
  { key: 'reference', label: 'Reference' },
  { key: 'uncertainty', label: 'Uncertainty' },
]

// source_kind(Task 8 六类)→ 归属块(用于第2层来源计数)。canonical 特殊,其余经验类归 recent/自身。
const KIND_TO_BLOCK = {
  canonical: 'canonical', working: 'recent', episodic: 'recent',
  procedural: 'procedural', reference: 'reference', uncertainty: 'uncertainty',
}

const STATUS_META = {
  current: { label: '主编知道你在看什么', tone: 'ok' },
  optimistic: { label: '乐观推进中 · 待服务端确认', tone: 'faint' },
  stale: { label: '上下文已过期 · 请对齐最新', tone: 'warn' },
  retrieval_degraded: { label: '检索降级 · 证据可能不全', tone: 'warn' },
  hermes_read_only: { label: 'Hermes 只读 · 暂不可写入', tone: 'warn' },
  // U-001(2026-07-13)文案修正:①旧文案「记忆检索不可用」是错的——记忆检索走 scribe3
  // 后端 + SurrealDB,与 Hermes 无关,离线只影响主编对话/生成;②新增 hermes_degraded 黄字档,
  // 承接「网关在跑但周边检查降级(如磁盘)」——旧实现把它一并显示成红字「离线」,纯误报。
  hermes_degraded: { label: 'Hermes 降级 · 功能可用,建议查看运行状态', tone: 'warn' },
  hermes_offline: { label: 'Hermes 离线 · 主编对话不可用', tone: 'danger' },
}

// 降级状态判定(优先级从重到轻)。current/optimistic/stale 复用 Task 5 快照状态;
// retrieval_degraded 从 trace 拉取失败(非 404)判定;hermes_* 从 /ai/runtime-status 判定。
function deriveStatus({ runtime, error, restoring, hasSession, traceError }) {
  // 真契约:/ai/runtime-status 顶层无 degraded,降级在 summary.degraded
  // ({chat,read_tools,write_runs});顶层只有 ok。此前读 runtime.degraded 恒 {},
  // hermes_offline/hermes_read_only 真机永不触发(见 app._hermes_runtime_status)。
  const d = (runtime && runtime.summary && runtime.summary.degraded) || {}
  if (runtime && runtime.ok === false && d.chat) return 'hermes_offline'
  if (d.write_runs && !d.chat) return 'hermes_read_only'
  if (error && error.code === 'stale_context') return 'stale'
  if (traceError) return 'retrieval_degraded'
  // U-001:网关在跑但周边检查降级(磁盘/负载等)→ 黄字提示,不再谎报离线。
  // 任一 profile 的 probe 标了 degraded 即提示(后端 probe.degraded/degraded_reasons)。
  if ((runtime?.profiles || []).some((p) => p?.ok && p?.degraded)) return 'hermes_degraded'
  if (restoring || !hasSession) return 'optimistic'
  return 'current'
}

function focusLabel(focus) {
  if (!focus || typeof focus !== 'object') return '未选中'
  return String(focus.label || focus.id || '未选中')
}

// 时态标签:canonical 恒真(无时间戳);经验记忆带 observed_at(取日期段)。
function tenseLabel(item) {
  if (item.source_kind === 'canonical' || item.observed_at == null) return '正典 · 恒真'
  return `经验 · ${String(item.observed_at).slice(0, 10)}`
}

function confidenceLabel(conf) {
  if (typeof conf !== 'number') return '信心 —'
  return `信心 ${Math.round(conf * 100)}%`
}

function EvidenceRow({ item, kind }) {
  // 私密硬红线:secret/masked 为真时永不渲染 text,只显屏蔽语义(即便后端意外漏值,前端也不显)。
  const secret = !!(item.secret || item.masked)
  return (
    <div
      data-testid={`evidence-${kind}`}
      data-source-id={item.source_id}
      className="rounded-md border border-line bg-canvas px-2 py-1.5 text-meta leading-snug"
    >
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className={`inline-flex items-center rounded px-1 py-0.5 text-meta ${kind === 'selected' ? 'bg-ok/15 text-ok' : 'bg-faint/15 text-faint'}`}>
          {kind === 'selected' ? '选入' : '弃用'}
        </span>
        <span className="font-mono text-ink truncate">{item.source_id}</span>
        <span className="text-faint">· {tenseLabel(item)}</span>
        <span className="text-faint">· {confidenceLabel(item.confidence)}</span>
        <span data-testid={`evidence-reason-${kind}`} className="ml-auto text-brand">理由:{item.reason || '—'}</span>
      </div>
      <div className="mt-0.5">
        {secret ? (
          <span data-testid="evidence-secret-masked" className="inline-flex items-center gap-1 text-warn">
            <ShieldAlert size={11} />秘密事实已屏蔽
          </span>
        ) : (
          <span className="text-faint break-words">{item.text || ''}</span>
        )}
      </div>
    </div>
  )
}

export function ContextInspector() {
  const { snapshot, restoring, error } = useContextSnapshot()
  const sessionId = snapshot?.session_id || null
  const revision = snapshot?.revision ?? null
  const focus = snapshot?.focus || null

  const [open, setOpen] = useState(false)
  const [trace, setTrace] = useState(null)
  const [traceError, setTraceError] = useState(false)
  const [runtime, setRuntime] = useState(null)

  // 运行时降级状态(可选;api 无 aiRuntimeStatus / 拉取失败 → 跳过,fail-soft,绝不拖垮主编区)。
  useEffect(() => {
    if (typeof api?.aiRuntimeStatus !== 'function') return undefined
    let alive = true
    api.aiRuntimeStatus().then((r) => { if (alive) setRuntime(r) }).catch(() => {})
    return () => { alive = false }
  }, [])

  // 拉当前快照版本的记忆溯源(会话/版本齐备且有 getMemoryTrace 才拉)。
  // 404 = 该版本暂无溯源(检索接线待 Task 16)→ 非降级,只是"未检索到证据"。
  useEffect(() => {
    if (!sessionId || revision == null || typeof api?.getMemoryTrace !== 'function') {
      setTrace(null); setTraceError(false); return undefined
    }
    let alive = true
    api.getMemoryTrace(sessionId, revision)
      .then((t) => { if (alive) { setTrace(t); setTraceError(false) } })
      .catch((e) => {
        if (!alive) return
        setTrace(null)
        setTraceError(!!(e && e.status && e.status !== 404))
      })
    return () => { alive = false }
  }, [sessionId, revision])

  const status = deriveStatus({ runtime, error, restoring, hasSession: !!sessionId, traceError })
  const meta = STATUS_META[status] || STATUS_META.current
  const toneClass = { ok: 'text-ok', warn: 'text-warn', danger: 'text-danger', faint: 'text-faint' }[meta.tone]
  const selected = (trace && trace.selected) || []
  const rejected = (trace && trace.rejected) || []
  const hasEvidence = selected.length > 0 || rejected.length > 0

  return (
    <div data-testid="context-inspector" data-status={status} className="border-b border-line bg-surface/60">
      {/* 第1层:常显条 —— focus / revision / 状态 */}
      <button
        type="button"
        data-testid="context-inspector-toggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 text-meta text-left hover:bg-soft/40 transition-colors"
      >
        <Eye size={12} className="text-brand shrink-0" />
        <span data-testid="context-inspector-focus" className="text-ink font-medium truncate max-w-[40%]">{focusLabel(focus)}</span>
        {revision != null && (
          <span data-testid="context-inspector-revision" className="text-faint tabular-nums">rev {revision}</span>
        )}
        <span data-testid="context-inspector-status" data-status={status} className={`ml-auto truncate ${toneClass}`}>{meta.label}</span>
        <ChevronRight size={12} className={`shrink-0 text-faint transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open && (
        <div className="px-3 pb-2.5 space-y-2">
          {/* 第2层:六块 token + 来源数 */}
          <div data-testid="context-inspector-blocks" className="grid grid-cols-2 gap-1">
            {BLOCK_DEFS.map((b) => {
              const tokens = (trace && trace.block_tokens && trace.block_tokens[b.key]) || 0
              const count = selected.filter((s) => KIND_TO_BLOCK[s.source_kind] === b.key).length
              return (
                <div
                  key={b.key}
                  data-testid={`context-block-${b.key}`}
                  className="flex items-center justify-between rounded-md border border-line bg-canvas px-2 py-1 text-meta"
                >
                  <span className="text-ink">{b.label}</span>
                  <span className="text-faint tabular-nums">{tokens} tok · {count} 源</span>
                </div>
              )
            })}
          </div>

          {/* 第3层:证据。无溯源 → "未检索到证据"(不显"没有相关事实") */}
          {!hasEvidence ? (
            <div data-testid="context-inspector-no-evidence" className="rounded-md border border-line bg-canvas px-2 py-2 text-meta text-faint">
              未检索到证据{status === 'retrieval_degraded' ? '(检索降级)' : ''}
            </div>
          ) : (
            <div data-testid="context-inspector-evidence" className="space-y-1">
              {selected.map((s, i) => <EvidenceRow key={`sel-${i}`} item={s} kind="selected" />)}
              {rejected.map((r, i) => <EvidenceRow key={`rej-${i}`} item={r} kind="rejected" />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
