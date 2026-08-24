import { useCallback, useEffect, useRef, useState } from 'react'
import { liveTouchesTable } from '../lib/liveRefresh.js'
import { maybeToastRollback } from '../lib/pilotRollback.js'
import { Compass, ArrowRight, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Btn } from '../ui.jsx'
import { StorylineHub } from './StorylineHub'

const STAGE_ZH = {
  idle: '待开写',
  outline_proposed: '大纲待放行',
  beats_ready: '节拍就绪',
  deduced: '演绎就绪',
  drafting: '草稿中',
  checked: '体检过',
  delivered: '待终选',
  finalized: '已定稿',
  outline: '大纲',
  beats: '节拍',
  design: '章设计',
  deduce: '演绎',
  draft: '草稿',
  final: '正文',
}

/**
 * 写作导演 · 旅程状态页（P0 + 设定债）
 * 数据源：GET /workflow/snapshot — 与顶栏进度胶囊同源。
 */
export function JourneyView({ work, onContinue, onJumpChapter, onOpenView, focusArcs = false }) {
  const [snap, setSnap] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [analyzeMsg, setAnalyzeMsg] = useState('')
  const [dash, setDash] = useState(null)
  const [dashOpen, setDashOpen] = useState(false)
  const [dashBusy, setDashBusy] = useState(false)
  const [pulse, setPulse] = useState(null)
  const [pilot, setPilot] = useState(null)
  const [stageInfo, setStageInfo] = useState(null)
  const [ledger, setLedger] = useState(null)
  const [extraOpen, setExtraOpen] = useState(false)
  const [arcsOpen, setArcsOpen] = useState(!!focusArcs)
  const arcsRef = useRef(null)

  const load = useCallback(() => {
    setLoading(true)
    setErr('')
    api.workflowSnapshot()
      .then((s) => { setSnap(s); maybeToastRollback(s) })
      .catch((e) => setErr(e?.message || '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load, work])

  useEffect(() => {
    if (!focusArcs) return undefined
    setArcsOpen(true)
    const t = setTimeout(() => arcsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
    return () => clearTimeout(t)
  }, [focusArcs])

  const seqNow = snap?.chapter_lane?.seq
  useEffect(() => {
    if (seqNow == null) return
    let dead = false
    api.chapterPulse?.(seqNow)?.then((p) => { if (!dead) setPulse(p) }).catch(() => {})
    api.pilotStatus?.(seqNow)?.then((p) => { if (!dead) setPilot(p) }).catch(() => {})
    api.chapterStage?.(seqNow)?.then((p) => { if (!dead) setStageInfo(p) }).catch(() => {})
    api.promisesLedger?.()?.then((p) => { if (!dead) setLedger(p) }).catch(() => {})
    return () => { dead = true }
  }, [seqNow, work])

  const liveTimer = useRef(null)
  useEffect(() => {
    const refreshExtras = () => {
      load()
      if (seqNow != null) {
        api.chapterPulse?.(seqNow)?.then(setPulse).catch(() => {})
        api.pilotStatus?.(seqNow)?.then(setPilot).catch(() => {})
        api.chapterStage?.(seqNow)?.then(setStageInfo).catch(() => {})
        api.promisesLedger?.()?.then(setLedger).catch(() => {})
      }
    }
    const onLive = (e) => {
      if (liveTouchesTable(e?.detail, ['chapter', 'promise', 'foreshadow', 'pilot_state', '_reconnect'])) {
        clearTimeout(liveTimer.current)
        liveTimer.current = setTimeout(refreshExtras, 300)
      }
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      clearTimeout(liveTimer.current)
      window.removeEventListener('s3-live', onLive)
    }
  }, [load, seqNow])

  const openInbox = (seq) => {
    try {
      if (seq != null) sessionStorage.setItem('canon-inbox-seq', String(seq))
    } catch { /* */ }
    onOpenView?.('canon-inbox')
    try {
      window.dispatchEvent(new CustomEvent('s3-open-canon-inbox', { detail: { seq } }))
    } catch { /* */ }
  }

  const loadAnalysisDash = async () => {
    const seq = snap?.chapter_lane?.seq
    if (seq == null || typeof api.canonAnalysisSummary !== 'function') return
    setDashBusy(true)
    try {
      const d = await api.canonAnalysisSummary(seq, true)
      setDash(d)
      setDashOpen(true)
    } catch (e) {
      setAnalyzeMsg(e?.message || '加载分析摘要失败')
    } finally {
      setDashBusy(false)
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
  const creativeSuggestions = Array.isArray(snap?.creative_suggestions)
    ? snap.creative_suggestions
    : (Array.isArray(next?.creative_suggestions) ? next.creative_suggestions : [])

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
              旅程
            </div>
            <p className="mt-1 text-meta text-faint leading-snug">
              现在该干什么：这一站、下一步、卡住的地方。
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

        {/* 导演 store-grounded 创意建议 */}
        {creativeSuggestions.length > 0 && (
          <section
            className="rounded-lg border border-line bg-soft/40 p-3 space-y-2"
            data-testid="journey-creative-suggestions"
          >
            <div className="text-meta text-faint uppercase tracking-wider">创意建议</div>
            <ul className="space-y-2">
              {creativeSuggestions.slice(0, 3).map((s, i) => (
                <li key={s.kind || i} className="text-f13 text-ink">
                  <span className="font-medium">{s.title || s.kind}</span>
                  {s.detail && (
                    <p className="text-meta text-faint mt-0.5 leading-snug">{s.detail}</p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

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
            </div>
            <Btn
              size="sm"
              variant="primary"
              onClick={() => openInbox(lane?.seq)}
              data-testid="journey-open-inbox-motifs"
            >
              去设定收件箱处理
              <ArrowRight size={14} className="ml-1 inline" />
            </Btn>
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

        {(snap?.stall_level === 'critical' || lane?.stall_level === 'critical') ? (
          <section
            className="rounded-lg border border-danger/40 bg-danger/[.08] p-3"
            data-testid="journey-stall-critical"
          >
            <div className="text-f14 font-medium text-ink">这一章停了超过两小时</div>
            <p className="mt-1 text-meta text-faint">自动步没再往前走。请你看一眼，或手动推进一步。</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Btn
                size="sm"
                variant="primary"
                data-testid="journey-stall-open-inbox"
                onClick={() => {
                  try {
                    window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'inbox' }))
                  } catch { /* */ }
                }}
              >
                查看收件箱
              </Btn>
            </div>
          </section>
        ) : (snap?.stall_level === 'warning' || lane?.stall_level === 'warning' || snap?.quality_stalled || lane?.quality_stalled) ? (
          <section
            className="rounded-lg border border-warn/40 bg-warn/[.08] p-3"
            data-testid="journey-quality-stalled"
          >
            <div className="text-f14 font-medium text-ink">这一章停了半小时以上</div>
            <p className="mt-1 text-meta text-faint">自动步超时未推进。不是你主动停靠，请检查或手动推进一步。</p>
          </section>
        ) : null}

        {(lane?.parked || snap?.chapter_lane?.parked) ? (
          <section
            className="rounded-lg border border-line/60 bg-soft/40 p-3"
            data-testid="journey-parked"
          >
            <div className="text-f14 font-medium text-ink">已主动停靠</div>
            <p className="mt-1 text-meta text-faint">{lane?.parked || snap?.chapter_lane?.parked}</p>
          </section>
        ) : null}

        {(pulse || pilot || stageInfo || ledger) && (
          <section className="rounded-lg border border-line/60 bg-soft/30 p-3 space-y-2" data-testid="journey-live-extra">
            <button
              type="button"
              className="text-meta text-faint uppercase tracking-wider cursor-pointer"
              onClick={() => setExtraOpen((v) => !v)}
              aria-expanded={extraOpen}
            >
              {extraOpen ? '收起本章信号' : '展开本章信号'}
            </button>
            <div className={`grid transition-all duration-200 ${extraOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
              <div className="overflow-hidden">
              <div className="space-y-1 text-f13 text-ink">
                {pilot && (
                  <div data-testid="journey-pilot-status">
                    写作状态：{pilot.state || pilot.pilot_state || 'idle'}
                  </div>
                )}
                {stageInfo && (
                  <div data-testid="journey-stage">
                    本章阶段：{stageInfo.label || STAGE_ZH[stageInfo.stage || stageInfo.current || stageInfo.phase] || stageInfo.stage || stageInfo.current || stageInfo.phase || '—'}
                  </div>
                )}
                {pulse && (
                  <div data-testid="journey-pulse">
                    本章节奏：{(pulse.summary || pulse.pressure || pulse.checks?.length != null)
                      ? (pulse.summary || `检查 ${pulse.checks?.length ?? 0} 项`)
                      : '已接入脉搏'}
                  </div>
                )}
                {ledger && (
                  <div data-testid="journey-promise-debt">
                    未兑现伏笔 {(ledger.open || []).length} 条
                    {ledger.audit?.overdue_count ? ` · 超期 ${ledger.audit.overdue_count}` : ''}
                  </div>
                )}
              </div>
              </div>
            </div>
          </section>
        )}

        {snap?.ledger?.congrats ? (
          <section
            className="rounded-lg border border-brand/30 bg-brand/10 p-4"
            data-testid="journey-ledger-complete"
          >
            <div className="text-f14 font-medium text-brand">{snap.ledger.congrats}</div>
            <p className="mt-1 text-meta text-ink/80">
              已定稿 {snap.ledger.finalized_count}/{snap.ledger.chapter_count} 章。
              {snap.ledger.quality_note ? ` ${snap.ledger.quality_note}` : ''}
            </p>
          </section>
        ) : null}

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
              {(lane.waiting_approval || snap?.waiting_approval) && (
                <span
                  data-testid="journey-waiting-approval"
                  className="px-2 py-0.5 rounded-full bg-warn/15 text-warn text-meta font-medium"
                >
                  等待你审批
                </span>
              )}
            </div>
            <div className="mb-2 flex flex-wrap items-center gap-2" data-testid="journey-post-analysis-row">
              {lane.post_analysis?.present && lane.post_analysis?.fp_match !== false ? (
                <p className="text-meta text-faint min-w-0 flex-1" data-testid="journey-post-analysis">
                  章后分析缓存
                  {lane.post_analysis.format ? ` · ${lane.post_analysis.format}` : ''}
                  {lane.post_analysis.settings_count != null
                    ? ` · 设定增量 ${lane.post_analysis.settings_count}`
                    : ''}
                  {lane.post_analysis.knowledge
                    ? ` · 知 ${lane.post_analysis.knowledge.learned ?? 0}/事 ${lane.post_analysis.knowledge.events ?? 0}`
                    : ''}
                  {lane.post_analysis.events_backfilled ? ' · 事件已补枪' : ''}
                  {lane.post_analysis.has_discipline
                    ? (lane.post_analysis.discipline_violations?.length
                      ? ` · 纪律违规 ${lane.post_analysis.discipline_violations.length}`
                      : ' · 纪律已缓存')
                    : ''}
                  {lane.post_analysis.has_tension ? ' · 张力已缓存' : ''}
                  <span className="text-faint/80"> · 改稿失效</span>
                </p>
              ) : (
                <p className="text-meta text-faint min-w-0 flex-1">尚无章后分析缓存（终选或点右侧重抽）</p>
              )}
              <Btn
                size="sm"
                variant="ghost"
                disabled={dashBusy}
                onClick={loadAnalysisDash}
                data-testid="journey-analysis-dash"
              >
                {dashBusy ? '加载…' : '分析摘要'}
              </Btn>
            </div>
            {analyzeMsg && <p className="text-meta text-ink mb-2">{analyzeMsg}</p>}
            {dashOpen && dash && (
              <div
                className="mb-3 rounded-md border border-line/50 bg-canvas px-3 py-2 text-meta text-ink space-y-1"
                data-testid="journey-analysis-dashboard"
              >
                <div className="flex justify-between gap-2">
                  <span className="font-medium">章后分析面板</span>
                  <button type="button" className="text-faint hover:text-ink cursor-pointer" onClick={() => setDashOpen(false)}>收起</button>
                </div>
                <div>
                  QC：{dash.qc_quick?.grade || '—'}
                  {(dash.qc_quick?.gates_hit || []).length
                    ? ` · gates ${dash.qc_quick.gates_hit.slice(0, 4).join('/')}`
                    : ''}
                  {dash.qc_quick?.word_count != null ? ` · ${dash.qc_quick.word_count} 字` : ''}
                </div>
                <div>
                  设定/知识缓存：
                  {dash.has_settings ? '设定✓' : '设定—'}
                  {' · '}
                  {dash.has_knowledge ? '知识✓' : '知识—'}
                  {dash.summary?.settings_count != null ? ` · 设定增量 ${dash.summary.settings_count}` : ''}
                </div>
                <div>
                  纪律：
                  {dash.has_discipline
                    ? (dash.discipline?.violations?.length
                      ? `违规 ${dash.discipline.violations.join('、')}`
                      : '已缓存·守纪')
                    : '未跑（可先体检）'}
                </div>
                <div>
                  张力：
                  {dash.has_tension
                    ? (dash.tension?.rubric_failed
                      ? 'rubric 失败'
                      : `已缓存${dash.tension?.hook?.present != null ? (dash.tension.hook.present ? '·有钩' : '·弱钩') : ''}`)
                    : '未跑（可跑张力检查）'}
                </div>
              </div>
            )}
            {Array.isArray(lane.pipeline) && lane.pipeline.length > 0 && (
              <div className="flex flex-wrap gap-1" data-testid="journey-chapter-pipeline">
                {lane.pipeline.map((p) => (
                  <span
                    key={p.id}
                    data-status={p.status}
                    data-needs-author={p.needs_author ? '1' : undefined}
                    className={
                      p.status === 'current' && p.needs_author
                        ? 'px-1.5 py-0.5 rounded text-meta bg-warn/15 text-warn font-medium'
                        : p.status === 'current'
                          ? 'px-1.5 py-0.5 rounded text-meta bg-brand/15 text-brand font-medium'
                          : p.status === 'done'
                            ? 'px-1.5 py-0.5 rounded text-meta bg-soft text-faint'
                            : 'px-1.5 py-0.5 rounded text-meta text-faint/50'
                    }
                  >
                    {p.label}{p.status === 'current' && p.needs_author ? ' · 等你' : ''}
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

        <section
          ref={arcsRef}
          className="rounded-lg border border-line/60 bg-soft/20 p-3 space-y-2"
          data-testid="journey-arcs"
        >
          <button
            type="button"
            className="w-full flex items-center justify-between text-left cursor-pointer"
            onClick={() => setArcsOpen((v) => !v)}
            aria-expanded={arcsOpen}
            data-testid="journey-arcs-toggle"
          >
            <span className="text-f14 font-medium text-ink">跨章弧（参考）</span>
            <span className="text-meta text-faint">{arcsOpen ? '收起' : '展开'}</span>
          </button>
          <p className="text-meta text-faint leading-snug">
            给主线/副线起名。不替代总纲、大纲或伏笔。勾了「写入生成提示」才进写作提示。
          </p>
          {arcsOpen && (
            <StorylineHub
              work={work}
              onJumpChapter={onJumpChapter}
              embedded
            />
          )}
        </section>
      </div>
    </div>
  )
}
