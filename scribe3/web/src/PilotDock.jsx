import { useEffect, useState } from 'react'
import { Bot, Loader2 } from 'lucide-react'
import { api } from './api'
import { Empty, SectionTitle } from './ui'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot } from './ChiefSlotContext'

const PILOT_STATE_LABEL = {
  idle: '未启动', outline_proposed: '大纲待放行', beats_ready: '节拍就绪', deduced: '演绎就绪',
  drafting: '草稿生成中', checked: '体检通过', delivered: '已交付 · 待终选', finalized: '已定稿',
}

/** 主编驾驶作业条。逻辑与旧右栏 PilotDock 相同，挂在主编模式条内。 */
export function PilotDock({ seq }) {
  const [st, setSt] = useState(undefined)
  const [run, setRun] = useState(null)
  const [until, setUntil] = useState('')
  const [steer, setSteer] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmFinalize, setConfirmFinalize] = useState(false)
  const toast = useToast()
  const { setJobBusy } = useChiefSlot()
  const running = !!run?.running

  useEffect(() => {
    setJobBusy?.(!!(busy || running))
    return () => setJobBusy?.(false)
  }, [busy, running, setJobBusy])

  useEffect(() => {
    if (seq == null) return undefined
    let dead = false
    setSt(undefined)
    const tick = () => {
      if (dead) return
      api.pilotStatus(seq)
        .then((s) => { if (!dead) setSt(s && typeof s === 'object' ? s : null) })
        .catch(() => { if (!dead) setSt(null) })
      api.pilotRunStatus().then((r) => { if (!dead) setRun(r) }).catch(() => {})
    }
    tick()
    const t = setInterval(tick, 3500)
    return () => { dead = true; clearInterval(t) }
  }, [seq])
  if (seq == null) return <Empty>选一章后可用主编驾驶驱动写作</Empty>
  const refresh = () => {
    api.pilotStatus(seq).then(setSt).catch(() => setSt(null))
    api.pilotRunStatus().then(setRun).catch(() => {})
  }
  const act = (fn, okMsg, opts = {}) => {
    setBusy(true)
    return fn().then((res) => {
      const rep = res?.artifact?.post_finalize_report
        || res?.post_finalize_report
        || res?.canon_loop?.post_finalize_report
      const l1 = rep?.sections?.l1_requires_approval?.items
      const l1n = Array.isArray(l1) ? l1.length : (rep?.change_pack?.l1_count ?? 0)
      const mods = rep?.sections?.l1_requires_approval?.modules || []
      if (opts.afterFinalize && (l1n > 0 || (rep && rep.silent_l1_write === false))) {
        const modHint = mods.length ? `（${mods.slice(0, 4).join('·')}）` : ''
        const uni = rep?.unified_analysis
        const ing = rep?.ingest
        const qc = rep?.qc_quick
        const srcHint = uni
          ? (ing?.source === 'unified_finalize'
            ? ' · 一次模型：设定+知识'
            : ' · 模型设定抽取')
          : ''
        const knHint = (ing && typeof ing.applied === 'number' && ing.applied >= 0)
          ? ` · 知识回写 ${ing.applied} 条`
          : ''
        const qcHint = (qc && qc.grade && !qc.empty)
          ? ` · 质检 ${qc.grade}${(qc.gates_hit || []).length ? `(${qc.gates_hit.slice(0, 3).join('/')})` : ''}`
          : ''
        toast(
          l1n > 0
            ? `已终选 · ${l1n} 条设定待确认${modHint}${srcHint}${knHint}${qcHint}。点「设定收件箱」批/拒。`
            : `${okMsg || '已终选定稿'}${srcHint}${knHint}${qcHint}`,
          { tone: 'ok', duration: 9000 },
        )
        try {
          if (seq != null) sessionStorage.setItem('canon-inbox-seq', String(seq))
          window.dispatchEvent(new CustomEvent('s3-open-canon-inbox', { detail: { seq, l1n, modules: mods } }))
        } catch { /* */ }
      } else {
        toast(okMsg, { tone: 'ok' })
      }
      refresh()
      try { window.dispatchEvent(new CustomEvent('s3-live', { detail: { table: 'chapter' } })) } catch { /* */ }
      return res
    })
      .catch((e) => {
        const d = e?.body?.detail
        const msg = (d && typeof d === 'object' && d.message) ? d.message : (d || e?.message || '操作失败')
        toast(msg, { tone: 'danger' })
        if (d && typeof d === 'object' && d.code === 'canon_debt_high') {
          try { window.dispatchEvent(new CustomEvent('s3-open-canon-inbox', { detail: {} })) } catch { /* */ }
        }
      })
      .finally(() => setBusy(false))
  }
  if (st === undefined) {
    return (
      <div className="space-y-3" data-testid="chief-pilot-strip">
        <SectionTitle icon={Bot}>主编驾驶</SectionTitle>
        <div className="text-meta text-faint">加载驾驶状态…</div>
      </div>
    )
  }
  if (st === null) {
    return (
      <div className="space-y-3" data-testid="chief-pilot-strip">
        <SectionTitle icon={Bot}>主编驾驶</SectionTitle>
        <div role="alert" className="text-meta text-danger bg-danger/8 rounded px-2 py-1.5">
          主编驾驶状态加载失败（不是「未启动」）。
          <button type="button" className="ml-2 underline cursor-pointer" onClick={refresh}>重试</button>
        </div>
      </div>
    )
  }
  const state = st?.state || 'idle'
  const stateLabel = st?.state_label || PILOT_STATE_LABEL[state] || state
  const untilN = Number(until)
  const pipeline = Array.isArray(st?.pipeline) ? st.pipeline : []
  const canStep = st?.can_step !== false && !running && state !== 'finalized' && !st?.parked
    && state !== 'outline_proposed' && state !== 'delivered'
  const canApprove = !!st?.can_approve && !running && !st?.parked
  const nextLabel = st?.next_action_label || st?.next_action
  const doApprove = () => {
    if (state === 'delivered') {
      setConfirmFinalize(true)
      return
    }
    act(() => api.pilotApprove(seq, state), state === 'outline_proposed' ? '大纲已确认,继续推进' : '已放行')
  }
  return (
    <div className="space-y-3" data-testid="chief-pilot-strip">
      <SectionTitle icon={Bot}>主编驾驶</SectionTitle>
      <div className="text-meta text-faint leading-snug">
        作者=创意总监 · 主编按阶段执行。大纲与终选须你放行;连写不自动定稿。
      </div>
      {pipeline.length > 0 && (
        <div className="flex flex-wrap gap-1" data-testid="pilot-pipeline">
          {pipeline.map((p) => (
            <span
              key={p.id}
              data-status={p.status}
              className={
                p.status === 'current' ? 'px-1.5 py-0.5 rounded text-meta bg-brand/15 text-brand font-medium'
                  : p.status === 'done' ? 'px-1.5 py-0.5 rounded text-meta bg-soft text-faint'
                    : 'px-1.5 py-0.5 rounded text-meta text-faint/60'
              }
            >
              {p.label}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="px-2 py-0.5 rounded-full bg-brand/10 text-brand text-meta font-medium">{stateLabel}</span>
        {st?.stalled && <span className="px-2 py-0.5 rounded-full bg-danger/10 text-danger text-meta">卡住 · 超 30 分未推进</span>}
        {nextLabel && !st?.parked && !running && (
          <span className="text-meta text-faint">下一步:{nextLabel}</span>
        )}
      </div>
      {st?.parked && <div className="text-meta text-danger bg-danger/8 rounded px-2 py-1.5 leading-snug">停靠:{st.parked}</div>}
      <div className="space-y-1">
        <label className="text-meta text-faint" htmlFor={`pilot-steer-${seq}`}>本章意图 / 禁忌(可选)</label>
        <textarea
          id={`pilot-steer-${seq}`}
          value={steer}
          onChange={(e) => setSteer(e.target.value)}
          placeholder="例:别煽情;章末落铃响;压住老范的戏份"
          rows={2}
          className="w-full px-2 py-1.5 rounded-lg border border-line bg-canvas text-meta text-ink resize-y min-h-[2.5rem]"
        />
      </div>
      <div className="flex gap-2 flex-wrap">
        <button
          type="button"
          disabled={busy || running || !canStep}
          onClick={() => act(() => api.pilotStep(seq, 'manual', steer.trim()), '已推进一步')}
          className="h-7 px-2.5 rounded-lg text-meta bg-brand text-brandfg disabled:opacity-40 cursor-pointer"
        >
          推进一步 →
        </button>
        {canApprove && (
          <button
            type="button"
            disabled={busy || running}
            onClick={doApprove}
            data-testid="pilot-approve-btn"
            className="h-7 px-2.5 rounded-lg text-meta bg-brand/90 text-brandfg disabled:opacity-40 cursor-pointer"
          >
            {state === 'outline_proposed' ? '确认大纲并继续 →' : '终选定稿 →'}
          </button>
        )}
        {(st?.parked || st?.stalled) && (
          <button type="button" disabled={busy} onClick={() => act(() => api.pilotResetStep(seq), '已解卡,可重跑当前步')}
            className="h-7 px-2.5 rounded-lg text-meta bg-soft border border-line text-ink cursor-pointer">解卡</button>
        )}
        {state !== 'idle' && state !== 'finalized' && (
          <button type="button" disabled={busy}
            onClick={() => { if (window.confirm('退出主编驾驶编排？不动正文/草料，想再用从头推进即可。')) act(() => api.pilotDismiss(seq), '已退出主编驾驶') }}
            className="h-7 px-2.5 rounded-lg text-meta text-faint hover:text-danger cursor-pointer">退出</button>
        )}
      </div>
      {state === 'outline_proposed' && !st?.parked && (
        <div className="text-meta text-faint leading-snug">
          大纲是品味检查点:可先在中区改大纲,再点「确认大纲并继续」(不可用「推进一步」硬闯)。
        </div>
      )}
      <div className="border-t border-line pt-2.5">
        {running ? (
          <div className="space-y-1.5">
            <div className="text-meta text-brand inline-flex items-center gap-1.5">
              <Loader2 size={12} className="animate-spin" />连写中 · 第 {run.cur_seq ?? '?'} 章(目标第 {run.until ?? '?'} 章)
            </div>
            <button type="button" disabled={busy} onClick={() => act(() => api.pilotPause(), '已暂停(步边界生效)')}
              className="h-7 px-2.5 rounded-lg text-meta bg-soft border border-line text-ink cursor-pointer">暂停连写</button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-meta text-faint">连写到第</span>
            <input value={until} onChange={(e) => setUntil(e.target.value.replace(/\D/g, ''))} placeholder={String((seq ?? 0) + 3)}
              className="w-14 h-7 px-2 rounded-lg border border-line bg-canvas text-meta text-center" />
            <span className="text-meta text-faint">章(终选留你;大纲在连写中自动越过)</span>
            <button type="button" disabled={busy || !until || untilN < seq}
              onClick={() => act(() => api.pilotRun(seq, untilN), '连写已启动')}
              className="h-7 px-2.5 rounded-lg text-meta bg-brand text-brandfg disabled:opacity-40 cursor-pointer">开始连写</button>
          </div>
        )}
        {run?.stopped && !running && <div className="text-meta text-faint mt-1.5 leading-snug">上次连写:{run.stopped}</div>}
      </div>
      <ConfirmDialog
        open={confirmFinalize}
        title="终选定稿这一章?"
        body="将执行 finalize(宪法级终选背书)。确认这就是你要定的稿?"
        confirmText="终选定稿"
        onConfirm={() => {
          setConfirmFinalize(false)
          act(() => api.pilotApprove(seq, 'delivered'), '已终选定稿', { afterFinalize: true })
        }}
        onClose={() => setConfirmFinalize(false)}
      />
    </div>
  )
}
