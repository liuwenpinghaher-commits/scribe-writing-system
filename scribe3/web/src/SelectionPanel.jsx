// 选择环对比页(北极星方案任务11,蓝图 §4-①):关键章 3 候选 → 确定性过滤明细 →
// rubric 排序(折叠展示,防锚定软门禁)→ 人终选 + 强制一句理由(入 lesson 流)。
// 半盲设计(调研:Arena 先例):策略标签默认隐藏可揭示;rubric 意见折叠;
// "谁被杀、为什么"全部可见——作者在知情基础上给理由,理由质量更高。
import { useState } from 'react'
import { AlertTriangle, ChevronDown, Eye, GitCompare, Loader2, Shield, Trophy } from 'lucide-react'
import { api } from './api'
import { Btn, Empty, Tag, Textarea } from './ui'
import { useToast } from './ui/Toast.jsx'

const AXES = ['切入点', '节奏', '信息释放', '其他']

// P2审查 P2-5:chosen 比较须排除 null===null(留版失败候选曾开局即高亮"已选")
function CandidateCard({ c, revealed, chosen, onChoose }) {
  const [showRank, setShowRank] = useState(false)
  const [full, setFull] = useState(null)        // R1-7:全文(null=未展开,只显示 prose_head)
  const [loadingFull, setLoadingFull] = useState(false)
  const toggleFull = () => {
    if (full != null) { setFull(null); return }
    if (!c.version_id) return
    setLoadingFull(true)
    api.chapterVersion(c.version_id).then((v) => setFull(v?.prose || ''))
      .catch(() => setFull('')).finally(() => setLoadingFull(false))
  }
  return (
    <div className={`rounded-lg border p-2.5 mb-2 ${chosen ? 'border-brand bg-brand/5' : 'border-line bg-surface'} ${c.filtered ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <Tag tone={c.filtered ? 'danger' : 'brand'}>{revealed ? c.strategy : `候选 ${c._label}`}</Tag>
        {c.filtered
          ? <span className="inline-flex items-center gap-1 text-f11 text-danger"><Shield size={11} />确定性过滤击杀:{c.filter_reason}</span>
          : <span className="text-f11 text-faint">advisory {c.advisory_count ?? 0} 条</span>}
        {!c.filtered && showRank && c.rubric_rank != null && (
          <span className="inline-flex items-center gap-1 text-f11 text-faint"><Trophy size={11} />rubric 第 {c.rubric_rank}(仅参考)</span>
        )}
        <button className="ml-auto text-f11 text-faint hover:text-ink" onClick={() => setShowRank((v) => !v)}>
          <ChevronDown size={12} className={showRank ? 'rotate-180' : ''} />
        </button>
      </div>
      <div className={`text-f12 text-ink whitespace-pre-wrap leading-relaxed overflow-y-auto ${full != null ? 'max-h-[60vh]' : 'max-h-44'}`}>{full != null ? full : `${c.prose_head}…`}</div>
      {/* R1-7:展开全文——按 version_id 拉留版全稿(不重烧 LLM);三卡同页各自展开=并排读全文,
          终选不再被迫在 300 字头部上做(切走也不毁对比状态:候选正文在版本库) */}
      {c.version_id && (
        <button onClick={toggleFull} disabled={loadingFull}
          className="text-f11 text-brand hover:underline cursor-pointer mt-1 disabled:opacity-50">
          {loadingFull ? '加载中…' : full != null ? '收起' : '展开全文'}
        </button>
      )}
      {c.profile && showRank && (
        <div className="mt-1 text-f11 text-faint">
          句长CV {c.profile.sent_cv} · 对话占比 {Math.round((c.profile.dialogue_ratio || 0) * 100)}%
        </div>
      )}
      {!c.filtered && (
        <div className="mt-1.5">
          {c.version_id
            ? <Btn size="sm" variant={chosen ? 'primary' : 'ghost'} onClick={onChoose}>{chosen ? '已选此稿' : '选这稿'}</Btn>
            : <span className="text-f11 text-danger">留版失败,不可终选(可复制正文手工处理)</span>}
        </div>
      )}
    </div>
  )
}

export function SelectionPanel({ seq, onFinalized }) {
  const toast = useToast()
  const [state, setState] = useState('idle')   // idle|running|ready|finalizing|done
  const [res, setRes] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [pick, setPick] = useState(null)       // version_id
  const [axis, setAxis] = useState('切入点')
  const [reason, setReason] = useState('')

  const run = async (force = false) => {
    setState('running'); setRes(null); setPick(null); setRevealed(false)
    try {
      const r = await api.selectChapter(seq, force)
      r.candidates?.forEach((c, i) => { c._label = ['甲', '乙', '丙', '丁'][i] || i + 1 })
      setRes(r); setState('ready')
    } catch (e) {
      const detail = e?.body?.detail || ''
      if (e?.status === 422 && detail.includes('force')) {
        // P2审查 P3:force 有 UI 通道——非关键章确认后带 force 重发(作者主权)
        if (window.confirm('本章无关键章标注(高压/关系回收/反转)。仍要花 3 倍生成成本出候选吗?')) {
          return run(true)
        }
        setState('idle'); return
      }
      toast(detail || '候选生成失败(检查后端与 LLM 网关)', { tone: 'danger' })
      setState('idle')
    }
  }

  const finalize = async () => {
    if (!pick) return
    if (!reason.trim()) { toast('终选必须留一句理由——它是沉淀环最贵的输入', { tone: 'danger' }); return }
    setState('finalizing')
    try {
      await api.selectFinalize(seq, { version_id: pick, reason_axis: axis, reason_text: reason.trim() })
      toast('已定稿并落库,理由已入 lesson 流')
      onFinalized?.()   // P2审查 P1-2:通知编辑器重载(恢复语义),防 stale buffer 盖掉终选稿
      setState('done')
    } catch (e) {
      toast(e?.body?.detail || '终选落库失败', { tone: 'danger' })
      setState('ready')
    }
  }

  if (seq == null) return <Empty>未选章</Empty>
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <GitCompare size={14} className="text-brand" />
        <span className="text-f12 text-ink">关键章 3 候选(策略多样,生成需数分钟)</span>
        <Btn size="sm" variant="primary" className="ml-auto" disabled={state === 'running'} onClick={run}>
          {state === 'running' ? <><Loader2 size={12} className="animate-spin" />生成中…</> : '出 3 候选'}
        </Btn>
      </div>
      {state === 'idle' && <Empty>点「出 3 候选」:同一章级合同出 3 个策略不同的候选,确定性过滤后由你终选</Empty>}
      {state === 'running' && <Empty>三路真机生成+检测中,请稍候(约 2-5 分钟)…</Empty>}
      {res && (
        <>
          {res.consensus === false && (
            <div className="mb-2 flex items-center gap-1.5 rounded-md border border-amber-300/50 bg-amber-500/10 px-2 py-1 text-f11 text-amber-600">
              <AlertTriangle size={11} />rubric 评审无共识(循环偏好/位置分歧)——不提供排序,凭你判断
            </div>
          )}
          {res.pseudo_diversity_round && (
            <div className="mb-2 text-f11 text-faint">检测到伪多样,已换备用策略重生成一路。</div>
          )}
          <div className="mb-2">
            <Btn size="sm" variant="ghost" onClick={() => setRevealed((v) => !v)}>
              <Eye size={12} />{revealed ? '隐藏策略标签' : '揭示策略标签(半盲:先读后揭)'}
            </Btn>
          </div>
          {res.candidates?.map((c) => (
            <CandidateCard key={c.version_id || c.strategy} c={c} revealed={revealed}
                           chosen={pick != null && pick === c.version_id}
                           onChoose={() => setPick(c.version_id)} />
          ))}
          {state !== 'done' && (
            <div className="mt-2 rounded-lg border border-line p-2.5">
              <div className="text-f11 text-faint mb-1">终选理由(必填,入 lesson 流)</div>
              <div className="flex flex-wrap gap-1.5 mb-1.5">
                {AXES.map((a) => (
                  <button key={a} onClick={() => setAxis(a)}
                          className={`rounded px-1.5 py-0.5 text-f11 border ${axis === a ? 'border-brand text-brand bg-brand/10' : 'border-line text-faint'}`}>
                    胜在{a}
                  </button>
                ))}
              </div>
              <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder="一句话:为什么选它、弃掉的差在哪" className="px-2.5 py-1.5" />
              <div className="mt-1.5 flex justify-end">
                <Btn size="sm" variant="primary" disabled={!pick || state === 'finalizing'} onClick={finalize}>
                  {state === 'finalizing' ? <Loader2 size={12} className="animate-spin" /> : '定稿此候选'}
                </Btn>
              </div>
            </div>
          )}
          {state === 'done' && <div className="mt-2 text-f12 text-ok">已定稿。可在「存档」查看各候选版本;稍后可点「反哺设定库」。</div>}
        </>
      )}
    </div>
  )
}
