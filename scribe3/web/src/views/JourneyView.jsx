import { useCallback, useEffect, useState } from 'react'
import { Compass, ArrowRight, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Btn } from '../ui.jsx'

/**
 * 写作导演 · 旅程状态页（P0 + 设定债）
 * 数据源：GET /workflow/snapshot — 与顶栏进度胶囊同源。
 */
export function JourneyView({ work, onContinue, onJumpChapter, onOpenView }) {
  const [snap, setSnap] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [motifBusy, setMotifBusy] = useState(false)
  const [motifMsg, setMotifMsg] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setErr('')
    api.workflowSnapshot()
      .then((s) => setSnap(s))
      .catch((e) => setErr(e?.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load, work])

  const openInbox = (seq) => {
    try {
      if (seq != null) sessionStorage.setItem('canon-inbox-seq', String(seq))
    } catch { /* */ }
    onOpenView?.('canon-inbox')
    try {
      window.dispatchEvent(new CustomEvent('s3-open-canon-inbox', { detail: { seq } }))
    } catch { /* */ }
  }

  const approveMotifSeeds = async () => {
    const prop = snap?.motif_seed_proposal
    if (!prop?.ops?.length) return
    setMotifBusy(true)
    setMotifMsg('')
    try {
      const res = await api.orchApplyProposal({
        proposal: prop,
        decision: 'approve',
        execute: true,
      })
      const st = res?.proposal?.status
      setMotifMsg(st === 'applied' || st === 'partial' ? '母题已写入设定库' : (res?.proposal?.note || '已提交'))
      load()
    } catch (e) {
      setMotifMsg(e?.message || '批准失败')
    } finally {
      setMotifBusy(false)
    }
  }

  if (loading && !snap) {
    return (
      <div className="h-full grid place-items-center text-f13 text-faint" data-testid="journey-loading">
        加载写作旅程…
      </div>
    )
  }

  if (err && !snap) {
    return (
      <div className="h-full grid place-items-center text-f13" data-testid="journey-error">
        <div className="text-center space-y-2">
          <div className="text-danger">{err}</div>
          <Btn size="sm" onClick={load}>重试</Btn>
        </div>
      </div>
    )
  }

  const stations = snap?.journey?.stations || []
  const lane = snap?.chapter_lane
  const next = snap?.next_step
  const blockers = snap?.blockers || []
  const debt = snap?.canon_debt || {}
  const motifGap = snap?.bible_motif_gap || null
  const motifProposal = snap?.motif_seed_proposal || null

  const handleContinue = () => {
    onContinue?.(snap)
  }

  return (
    <div className="h-full overflow-auto px-6 py-5" data-testid="journey-view">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-brand font-medium text-f14">
              <Compass size={18} />
              写作旅程
            </div>
            <p className="mt-1 text-meta text-faint leading-snug">
              你只做想象与裁决；系统告诉你做到哪、下一步聊什么。
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            className="h-8 w-8 rounded-md text-faint hover:text-ink hover:bg-soft inline-flex items-center justify-center cursor-pointer"
            title="刷新"
            aria-label="刷新旅程"
          >
            <RefreshCw size={15} />
          </button>
        </header>

        {/* 开书母题缺口 → 一键批准草案 */}
        {motifGap && !motifGap.ok && (
          <section
            className="rounded-lg border border-warn/40 bg-warn/[.08] p-3 flex flex-wrap items-center gap-3"
            data-testid="journey-bible-motifs"
          >
            <div className="min-w-0 flex-1">
              <div className="text-meta text-faint uppercase tracking-wider">圣经 · 母题</div>
              <div className="text-f14 text-ink mt-0.5">
                已有 <span className="font-semibold tnum">{motifGap.count ?? 0}</span>
                ，目标 ≥ <span className="tnum">{motifGap.min_required ?? 3}</span>
              </div>
              <p className="text-meta text-faint mt-1">
                母题须开书先立档：写作注入与正文触及只匹配已立母题，不会从正文自动新建。
              </p>
              {motifMsg && <p className="text-meta mt-1 text-ink">{motifMsg}</p>}
            </div>
            {motifProposal?.ops?.length > 0 && (
              <Btn
                size="sm"
                variant="primary"
                disabled={motifBusy}
                onClick={approveMotifSeeds}
                data-testid="journey-approve-motif-seeds"
              >
                {motifBusy ? '写入中…' : `批准 ${motifProposal.ops.length} 条母题草案`}
              </Btn>
            )}
          </section>
        )}

        {/* 设定债 → 收件箱 */}
        <section
          className="rounded-lg border border-line/60 bg-soft/40 p-3 flex flex-wrap items-center gap-3"
          data-testid="journey-canon-debt"
        >
          <div className="min-w-0 flex-1">
            <div className="text-meta text-faint uppercase tracking-wider">设定债</div>
            <div className="text-f14 text-ink mt-0.5">
              待确认 <span className="font-semibold tnum">{debt.total ?? 0}</span>
              {debt.high != null && debt.high > 0 && (
                <span className="ml-2 text-danger">高风险 {debt.high}</span>
              )}
              {debt.noise_count != null && debt.noise_count > 0 && (
                <span className="ml-2 text-faint">噪声约 {debt.noise_count}</span>
              )}
              {debt.suggested_priority_count != null && (
                <span className="ml-2 text-faint">建议优先 {debt.suggested_priority_count}</span>
              )}
            </div>
            <p className="text-meta text-faint mt-1">正文/讨论回写的设定须人批后才进 Codex。</p>
          </div>
          <Btn
            size="sm"
            variant={(debt.total || 0) > 0 ? 'primary' : 'ghost'}
            onClick={() => openInbox(lane?.seq)}
            data-testid="journey-open-canon-inbox"
          >
            打开设定收件箱
            <ArrowRight size={14} className="ml-1 inline" />
          </Btn>
        </section>

        {/* 书级 5 站 */}
        <section aria-labelledby="journey-stations-h">
          <h2 id="journey-stations-h" className="text-meta text-faint uppercase tracking-wider mb-2">
            全书站点
          </h2>
          <ol className="flex flex-wrap gap-2" data-testid="journey-stations">
            {stations.map((s) => (
              <li
                key={s.id}
                data-status={s.status}
                className={
                  s.status === 'current'
                    ? 'px-2.5 py-1 rounded-full text-meta bg-brand/15 text-brand font-medium'
                    : s.status === 'done'
                      ? 'px-2.5 py-1 rounded-full text-meta bg-soft text-faint'
                      : 'px-2.5 py-1 rounded-full text-meta text-faint/50 border border-line/40'
                }
              >
                {s.label}
              </li>
            ))}
          </ol>
        </section>

        {/* 章流水线 */}
        {lane && (
          <section aria-labelledby="journey-lane-h" className="rounded-lg border border-line/60 bg-soft/30 p-4">
            <h2 id="journey-lane-h" className="text-meta text-faint uppercase tracking-wider mb-2">
              当前章
            </h2>
            <div className="flex flex-wrap items-baseline gap-2 mb-3">
              <button
                type="button"
                className="text-f14 font-medium text-ink hover:text-brand cursor-pointer"
                onClick={() => onJumpChapter?.(lane.seq)}
              >
                第 {lane.seq} 章{lane.title ? ` · ${lane.title}` : ''}
              </button>
              <span className="px-2 py-0.5 rounded-full bg-brand/10 text-brand text-meta">
                {lane.pilot_state_label || lane.pilot_state}
              </span>
            </div>
            {lane.post_analysis?.present && lane.post_analysis?.fp_match !== false && (
              <p className="text-meta text-faint mb-2" data-testid="journey-post-analysis">
                章后分析缓存
                {lane.post_analysis.format ? ` · ${lane.post_analysis.format}` : ''}
                {lane.post_analysis.settings_count != null
                  ? ` · 设定增量 ${lane.post_analysis.settings_count}`
                  : ''}
                {lane.post_analysis.knowledge
                  ? ` · 知 ${lane.post_analysis.knowledge.learned ?? 0}/事 ${lane.post_analysis.knowledge.events ?? 0}`
                  : ''}
                {lane.post_analysis.events_backfilled ? ' · 事件已补枪' : ''}
                <span className="text-faint/80">（改稿后自动失效，反哺可复用免二调）</span>
              </p>
            )}
            {Array.isArray(lane.pipeline) && lane.pipeline.length > 0 && (
              <div className="flex flex-wrap gap-1" data-testid="journey-chapter-pipeline">
                {lane.pipeline.map((p) => (
                  <span
                    key={p.id}
                    data-status={p.status}
                    className={
                      p.status === 'current'
                        ? 'px-1.5 py-0.5 rounded text-meta bg-brand/15 text-brand font-medium'
                        : p.status === 'done'
                          ? 'px-1.5 py-0.5 rounded text-meta bg-soft text-faint'
                          : 'px-1.5 py-0.5 rounded text-meta text-faint/50'
                    }
                  >
                    {p.label}
                  </span>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 下一步 CTA */}
        <section
          className="rounded-lg border border-brand/30 bg-brand/5 p-4 space-y-3"
          data-testid="journey-next-step"
        >
          <div className="text-meta text-faint">下一步</div>
          <h3 className="text-f16 font-medium text-ink leading-snug">
            {next?.title || '暂无下一步'}
          </h3>
          {next?.why && (
            <p className="text-f13 text-faint leading-relaxed">{next.why}</p>
          )}
          {next?.how_chat && (
            <p className="text-meta text-ink/80 leading-relaxed">
              <span className="text-faint">怎么聊：</span>
              {next.how_chat}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <Btn
              variant="primary"
              onClick={handleContinue}
              data-testid="journey-continue"
            >
              继续（预填主编）
              <ArrowRight size={14} className="ml-1 inline" />
            </Btn>
          </div>
          {snap?.suggested_prompt && (
            <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap rounded border border-line/40 bg-canvas/80 p-2 text-meta text-faint leading-snug">
              {snap.suggested_prompt}
            </pre>
          )}
        </section>

        {!!blockers.length && (
          <section data-testid="journey-blockers">
            <h2 className="text-meta text-faint uppercase tracking-wider mb-2">需注意</h2>
            <ul className="space-y-1">
              {blockers.map((b, i) => (
                <li key={i} className="text-f13 text-warn leading-snug">
                  {b.message || b.code}
                </li>
              ))}
            </ul>
          </section>
        )}

        {snap?.note && (
          <p className="text-meta text-faint/70">{snap.note}</p>
        )}
      </div>
    </div>
  )
}
