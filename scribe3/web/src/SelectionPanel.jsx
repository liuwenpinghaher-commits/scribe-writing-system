// 选择环分层 UI:
// L0 默认写路径不在此(主编/Pilot);本面板提供
// L1 轻选择(2 策略短包·约 2 发 LLM) + L2 重环(关键章 3 整章·约 10 发·数分钟)。
// L2: 确定性过滤 + rubric 参考 + 人终选理由入 lesson。
// L1: 扫读点选 → 草稿种子,再扩写正文。
import { useEffect, useState } from 'react'
import { AlertTriangle, ChevronDown, Eye, GitCompare, Loader2, Shield, Trophy, Zap } from 'lucide-react'
import { api } from './api'
import { Btn, Empty, Tag, Textarea } from './ui'
import { useToast } from './ui/Toast.jsx'

const AXES = ['切入点', '节奏', '信息释放', '其他']

function decorateCandidates(r) {
  r?.candidates?.forEach((c, i) => { c._label = ['甲', '乙', '丙', '丁'][i] || i + 1 })
  return r
}

function decorateVariants(r) {
  r?.variants?.forEach((c, i) => { c._label = ['甲', '乙'][i] || i + 1 })
  return r
}

// P2审查 P2-5:chosen 比较须排除 null===null
function CandidateCard({ c, revealed, chosen, onChoose }) {
  const [showRank, setShowRank] = useState(false)
  const [full, setFull] = useState(null)
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
          ? <span className="inline-flex items-center gap-1 text-meta text-danger"><Shield size={11} />确定性过滤击杀:{c.filter_reason}</span>
          : <span className="text-meta text-faint">advisory {c.advisory_count ?? 0} 条</span>}
        {!c.filtered && showRank && c.rubric_rank != null && (
          <span className="inline-flex items-center gap-1 text-meta text-faint"><Trophy size={11} />rubric 第 {c.rubric_rank}(仅参考)</span>
        )}
        <button type="button" className="ml-auto text-meta text-faint hover:text-ink" onClick={() => setShowRank((v) => !v)}>
          <ChevronDown size={12} className={showRank ? 'rotate-180' : ''} />
        </button>
      </div>
      <div className={`text-f12 text-ink whitespace-pre-wrap leading-relaxed overflow-y-auto ${full != null ? 'max-h-[60vh]' : 'max-h-44'}`}>{full != null ? full : `${c.prose_head}…`}</div>
      {c.version_id && (
        <button type="button" onClick={toggleFull} disabled={loadingFull}
          className="text-meta text-brand hover:underline cursor-pointer mt-1 disabled:opacity-50">
          {loadingFull ? '加载中…' : full != null ? '收起' : '展开全文'}
        </button>
      )}
      {c.profile && showRank && (
        <div className="mt-1 text-meta text-faint">
          句长CV {c.profile.sent_cv} · 对话占比 {Math.round((c.profile.dialogue_ratio || 0) * 100)}%
        </div>
      )}
      {!c.filtered && (
        <div className="mt-1.5">
          {c.version_id
            ? <Btn size="sm" variant={chosen ? 'primary' : 'ghost'} onClick={onChoose}>{chosen ? '已选此稿' : '选这稿'}</Btn>
            : <span className="text-meta text-danger">留版失败,不可终选</span>}
        </div>
      )}
    </div>
  )
}

function LightVariantCard({ v, chosen, onChoose }) {
  return (
    <div
      className={`rounded-lg border p-2.5 mb-2 ${chosen ? 'border-brand bg-brand/5' : 'border-line bg-surface'}`}
      data-testid="selection-l1-card"
      data-strategy={v.strategy}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <Tag tone="brand">L1 · {v.strategy}</Tag>
        <span className="text-meta text-faint">{v.char_count ?? (v.text || '').length} 字</span>
      </div>
      {v.directive && (
        <div className="text-meta text-faint mb-1 line-clamp-2" title={v.directive}>{v.directive}</div>
      )}
      <div className="text-f12 text-ink whitespace-pre-wrap leading-relaxed max-h-44 overflow-y-auto">
        {v.text || v.text_head || '…'}
      </div>
      <div className="mt-1.5">
        <Btn size="sm" variant={chosen ? 'primary' : 'ghost'} onClick={onChoose} data-testid="selection-l1-pick">
          {chosen ? '已选此包' : '采用为草稿种子'}
        </Btn>
      </div>
    </div>
  )
}

export function SelectionPanel({ seq, onFinalized }) {
  const toast = useToast()
  // mode: l1 | l2 — 展示哪一层结果;按钮各自触发
  const [mode, setMode] = useState('l1')
  const [state, setState] = useState('idle')   // idle|running|ready|finalizing|done|picking
  const [res, setRes] = useState(null)         // L2 body
  const [l1, setL1] = useState(null)           // L1 body
  const [revealed, setRevealed] = useState(false)
  const [pick, setPick] = useState(null)       // L2 version_id
  const [l1Pick, setL1Pick] = useState(null)   // L1 version_id or strategy
  const [axis, setAxis] = useState('切入点')
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (seq == null) {
      setRes(null); setL1(null); setState('idle'); setPick(null); setL1Pick(null)
      return
    }
    let alive = true
    setRes(null); setL1(null); setPick(null); setL1Pick(null); setRevealed(false); setReason('')
    setState('idle'); setMode('l1')
    // 并行恢复 L1 / L2 历史;优先展示有结果的一层(L1 日常优先)
    Promise.all([
      api.selectLightLatest(seq).catch(() => null),
      api.selectLatest(seq).catch(() => null),
    ]).then(([light, heavy]) => {
      if (!alive) return
      if (light?.variants?.length) {
        decorateVariants(light)
        setL1(light)
        setMode('l1')
        setState(light.verdict === 'picked' ? 'done' : 'ready')
        if (light.picked?.version_id) setL1Pick(light.picked.version_id)
      }
      if (heavy?.candidates?.length) {
        decorateCandidates(heavy)
        setRes(heavy)
        if (!light?.variants?.length) {
          setMode('l2')
          setState('ready')
        }
      }
    })
    return () => { alive = false }
  }, [seq])

  const runL1 = async () => {
    setMode('l1')
    setState('running'); setL1(null); setL1Pick(null)
    try {
      const r = decorateVariants(await api.selectLight(seq))
      setL1(r); setState('ready')
    } catch (e) {
      const detail = e?.body?.detail || ''
      if (e?.status === 404) {
        toast(`第 ${seq} 章还没有正文——回到有内容的章再试`, { tone: 'danger' })
      } else if (e?.status === 409) {
        toast(detail || '本章已有生成在途', { tone: 'danger' })
      } else if (e?.status === 429) {
        toast(detail || 'LLM 日帽不足', { tone: 'danger' })
      } else {
        toast(detail || 'L1 轻选择请求失败,请刷新后重试', { tone: 'danger' })
      }
      setState('idle')
    }
  }

  const runL2 = async (force = false) => {
    setMode('l2')
    setState('running'); setRes(null); setPick(null); setRevealed(false)
    try {
      const r = decorateCandidates(await api.selectChapter(seq, force))
      setRes(r); setState('ready')
    } catch (e) {
      const detail = e?.body?.detail || ''
      if (e?.status === 422 && detail.includes('force')) {
        if (window.confirm('本章无关键章标注(高压/关系回收/反转)。仍要花约 10 发 LLM、数分钟出 3 整章候选吗?')) {
          return runL2(true)
        }
        setState('idle'); return
      }
      if (e?.status === 404) {
        toast(`第 ${seq} 章还没有正文(可能翻到了空章)——回到有内容的章再出候选`, { tone: 'danger' })
        setState('idle'); return
      }
      if (e?.status === 409) {
        toast(detail || '本章已有生成在途,请稍后再出候选', { tone: 'danger' })
        setState('idle'); return
      }
      if (e?.status === 429) {
        toast(detail || 'LLM 日帽不足,次日再试或调大日帽', { tone: 'danger' })
        setState('idle'); return
      }
      toast(detail || '请求未送达后端:可能网络异常或页面版本过期,请刷新后重试', { tone: 'danger' })
      setState('idle')
    }
  }

  const pickL1 = async (v) => {
    const key = v.version_id || v.strategy
    setL1Pick(key)
    setState('picking')
    try {
      const out = await api.selectLightPick(seq, {
        version_id: v.version_id || undefined,
        strategy: v.strategy || undefined,
      })
      setL1((prev) => prev ? { ...prev, picked: out.picked, verdict: 'picked' } : prev)
      onFinalized?.()  // restoreTick → DraftTab 重拉 /latest-draft
      // 切到草稿阶段,让作者立刻看到 stage=draft 种子(验收标准 2 端到端)
      try {
        window.dispatchEvent(new CustomEvent('s3-chapter-phase', {
          detail: { phase: 'draft', seq, reason: 'l1_pick' },
        }))
      } catch { /* */ }
      toast(out?.note || '已写入草稿种子并切到草稿阶段,可继续扩写')
      setState('done')
    } catch (e) {
      toast(e?.body?.detail || 'L1 点选失败', { tone: 'danger' })
      setState('ready')
    }
  }

  const finalize = async () => {
    if (!pick) return
    if (!reason.trim()) { toast('终选必须留一句理由——它是沉淀环最贵的输入', { tone: 'danger' }); return }
    const picked = res?.candidates?.find((c) => c.version_id === pick)
    if (picked?.filtered) {
      toast('不可定稿被确定性过滤击杀的候选', { tone: 'danger' }); return
    }
    setState('finalizing')
    try {
      const out = await api.selectFinalize(seq, { version_id: pick, reason_axis: axis, reason_text: reason.trim() })
      if (out?.lesson_saved === false) {
        toast(`已定稿落库,但终选理由未写入 lesson:${out.lesson_error || ''}`, { tone: 'warn' })
      } else {
        toast('已定稿并落库,理由已入 lesson 流')
      }
      onFinalized?.()
      setState('done')
    } catch (e) {
      toast(e?.body?.detail || '终选落库失败', { tone: 'danger' })
      setState('ready')
    }
  }

  const canFinalize = pick && state !== 'finalizing' && state !== 'done'
    && res?.verdict !== 'all_failed' && res?.verdict !== 'all_filtered'

  if (seq == null) return <Empty>未选章</Empty>
  const busy = state === 'running' || state === 'picking' || state === 'finalizing'

  return (
    <div data-testid="selection-panel">
      <div className="flex items-center gap-2 mb-1.5">
        <GitCompare size={14} className="text-brand shrink-0" />
        <span className="text-f12 text-ink font-medium truncate min-w-0">选择环 · 分层多路径</span>
      </div>
      {/* 档位说明:日常 L1;关键章 L2 */}
      <div className="mb-2 rounded-md border border-line/70 bg-soft/40 px-2 py-1.5 text-meta text-faint leading-snug"
        data-testid="selection-tier-copy">
        <div><strong className="text-ink">日常</strong>用「轻选 2 短包」(约 2 发 LLM),点选写入草稿种子再扩写。</div>
        <div><strong className="text-ink">关键章</strong>才用「出 3 候选」L2(约 10 发·数分钟整章),过滤后终选+理由。</div>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        <Btn size="sm" variant="primary" disabled={busy} onClick={runL1} data-testid="selection-l1-run"
          className="shrink-0 whitespace-nowrap">
          {state === 'running' && mode === 'l1'
            ? <><Loader2 size={12} className="animate-spin" />轻选生成中…</>
            : <><Zap size={12} />轻选 2 短包</>}
        </Btn>
        <Btn size="sm" variant="ghost" disabled={busy} onClick={() => runL2(false)} data-testid="selection-run"
          className="shrink-0 whitespace-nowrap" title="L2 重环:约 10 发 LLM、数分钟,关键章 3 整章候选">
          {state === 'running' && mode === 'l2'
            ? <><Loader2 size={12} className="animate-spin" />L2 生成中…</>
            : '出 3 候选(重)'}
        </Btn>
        {(l1 || res) && (
          <div className="ml-auto flex gap-1">
            {l1 && (
              <button type="button" data-testid="selection-tab-l1"
                className={`text-meta px-1.5 rounded ${mode === 'l1' ? 'bg-brand/10 text-brand' : 'text-faint'}`}
                onClick={() => setMode('l1')}>看 L1</button>
            )}
            {res && (
              <button type="button" data-testid="selection-tab-l2"
                className={`text-meta px-1.5 rounded ${mode === 'l2' ? 'bg-brand/10 text-brand' : 'text-faint'}`}
                onClick={() => setMode('l2')}>看 L2</button>
            )}
          </div>
        )}
      </div>

      {state === 'idle' && !l1 && !res && (
        <Empty>日常先点「轻选 2 短包」对比切入;关键章再用「出 3 候选」烧整章</Empty>
      )}
      {state === 'running' && (
        <Empty>{mode === 'l1' ? '两条策略短包生成中(约半分钟)…' : '三路整章生成+检测中(约 2-5 分钟)…'}</Empty>
      )}

      {/* ── L1 结果 ── */}
      {mode === 'l1' && l1 && (
        <div data-testid="selection-l1-panel">
          {l1.verdict === 'all_failed' && (
            <div className="mb-2 text-meta text-danger" data-testid="selection-l1-failed">
              L1 失败:{(l1.gen_errors || []).join('；') || '未知'}
            </div>
          )}
          {l1.tier_note && <div className="mb-2 text-meta text-faint">{l1.tier_note}</div>}
          {l1.note && l1.verdict !== 'all_failed' && (
            <div className="mb-2 text-meta text-faint">{l1.note}</div>
          )}
          {l1.variants?.map((v) => (
            <LightVariantCard
              key={v.version_id || v.strategy}
              v={v}
              chosen={l1Pick != null && (l1Pick === v.version_id || l1Pick === v.strategy
                || l1?.picked?.strategy === v.strategy)}
              onChoose={() => state !== 'done' && pickL1(v)}
            />
          ))}
          {state === 'done' && l1.verdict === 'picked' && (
            <div className="mt-2 text-f12 text-ok" data-testid="selection-l1-done">
              已采用策略 {l1.picked?.strategy || ''} 为草稿种子。可在正文编辑或主编槽继续扩写。
            </div>
          )}
        </div>
      )}

      {/* ── L2 结果 ── */}
      {mode === 'l2' && res && (
        <>
          {res.verdict === 'all_failed' && (
            <div className="mb-2 flex items-start gap-1.5 rounded-md border border-danger/40 bg-danger/8 px-2 py-1.5 text-meta text-danger leading-snug"
              data-testid="selection-all-failed">
              <AlertTriangle size={11} className="shrink-0 mt-0.5" />
              <span>所有候选生成失败(检查 LLM 网关 / 日帽):{(res.gen_errors || []).join('；') || '未知原因'}</span>
            </div>
          )}
          {res.verdict === 'all_filtered' && (
            <div className="mb-2 flex items-start gap-1.5 rounded-md border border-danger/40 bg-danger/8 px-2 py-1.5 text-meta text-danger leading-snug"
              data-testid="selection-all-filtered">
              <AlertTriangle size={11} className="shrink-0 mt-0.5" />
              <span>
                全部候选被确定性过滤击杀。击杀稿不可定稿。
                <button type="button" className="ml-1 underline cursor-pointer" onClick={() => runL2(true)}>强制重出</button>
              </span>
            </div>
          )}
          {res.gen_errors?.length > 0 && res.verdict !== 'all_failed' && (
            <div className="mb-2 text-meta text-warn leading-snug">
              {res.gen_errors.length} 个策略未出稿:{res.gen_errors.join('；')}
            </div>
          )}
          {res.consensus === false && res.verdict === 'awaiting_human' && (
            <div className="mb-2 flex items-center gap-1.5 rounded-md border border-amber-300/50 bg-amber-500/10 px-2 py-1 text-meta text-amber-600">
              <AlertTriangle size={11} />rubric 无共识——不提供排序,凭你判断
            </div>
          )}
          {res.pseudo_diversity_round && (
            <div className="mb-2 text-meta text-faint">检测到伪多样,已换备用策略重生成一路。</div>
          )}
          <div className="mb-2">
            <Btn size="sm" variant="ghost" onClick={() => setRevealed((v) => !v)}>
              <Eye size={12} />{revealed ? '隐藏策略标签' : '揭示策略标签(半盲)'}
            </Btn>
          </div>
          {res.candidates?.map((c) => (
            <CandidateCard key={c.version_id || c.strategy} c={c} revealed={revealed}
              chosen={pick != null && pick === c.version_id}
              onChoose={() => !c.filtered && c.version_id && setPick(c.version_id)} />
          ))}
          {state !== 'done' && res.verdict !== 'all_failed' && res.verdict !== 'all_filtered' && (
            <div className="mt-2 rounded-lg border border-line p-2.5">
              <div className="text-meta text-faint mb-1">L2 终选理由(必填,入 lesson 流)</div>
              <div className="flex flex-wrap gap-1.5 mb-1.5">
                {AXES.map((a) => (
                  <button key={a} type="button" onClick={() => setAxis(a)}
                    className={`rounded px-1.5 py-0.5 text-meta border ${axis === a ? 'border-brand text-brand bg-brand/10' : 'border-line text-faint'}`}>
                    胜在{a}
                  </button>
                ))}
              </div>
              <Textarea variant="bordered" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                placeholder="一句话:为什么选它、弃掉的差在哪" className="px-2.5 py-1.5" />
              <div className="mt-1.5 flex justify-end">
                <Btn size="sm" variant="primary" disabled={!canFinalize} onClick={finalize}
                  data-testid="selection-finalize">
                  {state === 'finalizing' ? <Loader2 size={12} className="animate-spin" /> : '定稿此候选'}
                </Btn>
              </div>
            </div>
          )}
          {state === 'done' && mode === 'l2' && (
            <div className="mt-2 text-f12 text-ok">已定稿。可在「存档」查看各候选版本。</div>
          )}
        </>
      )}
    </div>
  )
}
