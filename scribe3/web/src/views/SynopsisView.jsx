import { useCallback, useEffect, useRef, useState } from 'react'
import { BookText, FileText, Bookmark, Users, Shield, Swords, ArrowRight, Activity, MapPin, AlertTriangle, Compass, LayoutList, Gauge } from 'lucide-react'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'
import { liveTouchesTable } from '../lib/liveRefresh.js'
import { NorthStarBar } from '../NorthStarBar'
import { NorthStarPanel } from '../NorthStarPanel'

// 总纲：进入一本书后的门厅。只读汇总，不走新后端。
// 旧称 OverviewView /「概览」；顶栏 key=synopsis，overview 仍作别名。

function Stat({ icon: Icon, label, value, sub, tone = 'ink', onClick }) {
  const c = { ink: 'text-ink', brand: 'text-brand', fore: 'text-fore', danger: 'text-danger', ok: 'text-ok' }[tone]
  const inner = (
    <>
      <div className="flex items-center gap-1.5 text-faint text-meta uppercase tracking-wider mb-1.5"><Icon size={13} />{label}</div>
      <div className={`text-2xl font-semibold tnum ${c}`}>{value}</div>
      {sub && <div className="text-meta text-faint mt-0.5">{sub}</div>}
    </>
  )
  if (onClick) {
    return (
      <button onClick={onClick}
        className="w-full text-left py-2 pr-2 cursor-pointer rounded-lg hover:bg-soft/50 transition-colors">
        {inner}
      </button>
    )
  }
  return <div className="py-2 pr-2">{inner}</div>
}

function BlockFail({ text }) {
  return <div className="text-f13 text-faint">{text}</div>
}

function groupOutline(outline) {
  const vols = outline?.volumes || []
  const chs = outline?.chapters || []
  const byVol = new Map()
  for (const v of vols) {
    byVol.set(String(v.id), { volume: v, chapters: [] })
  }
  const unassigned = []
  for (const c of chs) {
    const vid = c.volume != null && c.volume !== '' ? String(c.volume) : ''
    if (vid && byVol.has(vid)) byVol.get(vid).chapters.push(c)
    else unassigned.push(c)
  }
  const lanes = [...byVol.values()]
  if (unassigned.length) {
    lanes.push({ volume: { id: '_none', title: '未分卷' }, chapters: unassigned })
  }
  return lanes
}

const LIVE_TABLES = [
  'chapter', 'promise', 'foreshadow', 'intent', 'motif', 'volume',
  'chapter_scorecard', '_reconnect',
]

export function SynopsisView({ onJumpChapter, onOpenView }) {
  const [q, setQ] = useState(undefined)
  const [comp, setComp] = useState(undefined)
  const [led, setLed] = useState(undefined)
  const [snap, setSnap] = useState(undefined)
  const [outline, setOutline] = useState(undefined)
  const [scoreOpen, setScoreOpen] = useState(false)
  const liveTimer = useRef(null)

  const loadLight = useCallback(() => {
    api.quality().then(setQ).catch(() => setQ(null))
    api.get('/setting-completeness').then(setComp).catch(() => setComp(null))
    api.promisesLedger().then(setLed).catch(() => setLed(null))
    api.workflowSnapshot().then(setSnap).catch(() => setSnap(null))
    api.outline().then(setOutline).catch(() => setOutline(null))
  }, [])

  useEffect(() => { loadLight() }, [loadLight])

  useEffect(() => {
    const onLive = (e) => {
      if (!liveTouchesTable(e?.detail, LIVE_TABLES)) return
      clearTimeout(liveTimer.current)
      liveTimer.current = setTimeout(loadLight, 300)
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      clearTimeout(liveTimer.current)
      window.removeEventListener('s3-live', onLive)
    }
  }, [loadLight])

  const chs = q?.chapters || []
  const cacheStale = (q?.cache_stale_chapters || []).length > 0
  const totalWords = q?.total_words || 0
  const chCount = chs.length
  const qcTotal = !q || cacheStale ? null : chs.reduce((s, c) => s + (c.qc_issues || 0) + (c.causal || 0), 0)
  const weak = !q || cacheStale ? [] : [...chs].filter((c) => (c.qc_issues || 0) + (c.causal || 0) > 0)
    .sort((a, b) => (b.qc_issues + b.causal) - (a.qc_issues + a.causal)).slice(0, 6)
  const fs = q?.foreshadow || {}
  const audit = led?.audit || {}
  const stations = snap?.journey?.stations || []
  const motifGap = snap?.bible_motif_gap || null
  const motifNames = Array.isArray(motifGap?.names) ? motifGap.names : []
  const lanes = outline ? groupOutline(outline) : []

  return (
    <div className="h-full overflow-y-auto bg-canvas" data-testid="synopsis-view">
      <div className="max-w-5xl mx-auto px-6 py-6 md:px-8 md:py-8">
        <div className="flex items-center gap-2 mb-5 flex-wrap">
          <BookText size={18} className="text-brand" />
          <h1 className="type-page prose-serif text-ink">总纲</h1>
          <div className="ml-auto flex flex-wrap gap-2 text-f12">
            <button type="button" onClick={() => onOpenView?.('insight')}
              className="text-brand hover:underline cursor-pointer" data-testid="overview-open-storyline">
              仪表盘 · 规划看板
            </button>
            <button type="button" onClick={() => onOpenView?.('event-graph')}
              className="text-brand hover:underline cursor-pointer" data-testid="overview-open-event-graph">
              事件图
            </button>
            <button type="button" onClick={() => onOpenView?.('benchmarks')}
              className="text-brand hover:underline cursor-pointer" data-testid="overview-open-benchmarks">
              Benchmark 库
            </button>
          </div>
        </div>

        {/* 1. 作品意图（置顶） */}
        <section className="mb-5 rounded-lg overflow-hidden border border-line/50" data-testid="synopsis-intent">
          <NorthStarBar />
        </section>

        {/* 2. 旅程五站 */}
        <section className="mb-5 pb-5 border-b border-line/40" data-testid="synopsis-stations">
          <div className="flex items-center flex-wrap gap-2 mb-2">
            <Compass size={15} className="text-brand" />
            <div className="text-meta font-semibold uppercase tracking-wider text-faint">旅程五站</div>
            <button type="button" onClick={() => onOpenView?.('journey')}
              className="ml-auto inline-flex items-center gap-1 text-f12 text-brand hover:underline cursor-pointer"
              data-testid="synopsis-open-journey">
              打开旅程 <ArrowRight size={12} />
            </button>
          </div>
          {snap === undefined ? (
            <div className="text-f13 text-faint">加载旅程…</div>
          ) : snap === null ? (
            <BlockFail text="暂时读不到旅程，不影响其他块" />
          ) : stations.length === 0 ? (
            <BlockFail text="还没走出第一站" />
          ) : (
            <ol className="flex flex-wrap gap-2">
              {stations.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    data-status={s.status}
                    onClick={() => onOpenView?.('journey')}
                    className={
                      s.status === 'current'
                        ? 'px-2.5 py-1 rounded-full text-meta bg-brand/15 text-brand font-medium cursor-pointer'
                        : s.status === 'done'
                          ? 'px-2.5 py-1 rounded-full text-meta bg-soft text-faint cursor-pointer'
                          : 'px-2.5 py-1 rounded-full text-meta text-faint/50 border border-line/40 cursor-pointer'
                    }
                  >
                    {s.label}
                  </button>
                </li>
              ))}
            </ol>
          )}
        </section>

        {/* 规模 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4" data-testid="synopsis-scale">
          {q === undefined ? (
            <div className="col-span-2 lg:col-span-4 text-f13 text-faint">加载规模…</div>
          ) : q === null ? (
            <div className="col-span-2 lg:col-span-4"><BlockFail text="暂时读不到规模，不影响其他块" /></div>
          ) : (
            <>
              <Stat icon={FileText} label="规模" value={totalWords.toLocaleString()} sub={`${chCount} 章`} tone="brand" />
              <Stat icon={Bookmark} label="伏笔" value={fs.open ?? 0} sub={`未回收 · 已收 ${fs.closed ?? 0}`} tone="fore"
                onClick={() => onOpenView?.('insight')} />
              <Stat icon={Activity} label="质检问题" value={cacheStale ? '待刷新' : qcTotal} sub={cacheStale ? '缓存已过期' : 'QC + 因果'} tone={cacheStale || qcTotal ? 'danger' : 'ok'}
                onClick={() => onOpenView?.('insight')} />
              <Stat icon={Bookmark} label="伏笔超期" value={fs.overdue ?? 0} sub="埋下 >3 章未回收" tone={fs.overdue ? 'danger' : 'ok'} />
            </>
          )}
        </div>

        <div className="space-y-6">
          {/* 3. 卷纲与结构速览 */}
          <section className="pb-5 border-b border-line/40" data-testid="synopsis-outline">
            <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">卷纲与结构</div>
            {outline === undefined ? (
              <div className="text-f13 text-faint">加载卷纲…</div>
            ) : outline === null ? (
              <BlockFail text="暂时读不到卷纲，不影响其他块" />
            ) : lanes.length === 0 ? (
              <BlockFail text="还没有卷和章。去旅程里立结构。" />
            ) : (
              <div className="space-y-2">
                {lanes.map((lane, i) => {
                  const title = lane.volume?.title || lane.volume?.name || '未命名卷'
                  const intro = (lane.volume?.intro || '').trim()
                  return (
                    <details key={lane.volume?.id || title} className="rounded-md border border-line/40 bg-surface/40 px-3 py-2" open={i === 0}>
                      <summary className="cursor-pointer text-f13 text-ink font-medium">
                        {title}
                        <span className="ml-2 text-meta text-faint font-normal">{lane.chapters.length} 章</span>
                      </summary>
                      {intro ? <p className="mt-1.5 text-f12 text-faint leading-snug">{intro}</p> : null}
                      <ul className="mt-2 space-y-1">
                        {lane.chapters.map((c) => (
                          <li key={c.seq}>
                            <button
                              type="button"
                              onClick={() => onJumpChapter?.(c.seq)}
                              className="w-full text-left text-f13 py-0.5 hover:text-brand cursor-pointer"
                            >
                              <span className="text-ink">{chapterLabel(c.seq, c.title)}</span>
                              {c.synopsis ? (
                                <span className="ml-2 text-faint text-f12">{c.synopsis}</span>
                              ) : (
                                <span className="ml-2 text-faint/60 text-f12">还没写摘要</span>
                              )}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )
                })}
              </div>
            )}
          </section>

          {/* 4. 核心母题 */}
          <section className="pb-5 border-b border-line/40" data-testid="synopsis-motifs">
            <div className="flex items-center flex-wrap gap-2 mb-2">
              <LayoutList size={15} className="text-brand" />
              <div className="text-meta font-semibold uppercase tracking-wider text-faint">核心母题</div>
            </div>
            {snap === undefined ? (
              <div className="text-f13 text-faint">加载母题…</div>
            ) : snap === null ? (
              <BlockFail text="暂时读不到母题，不影响其他块" />
            ) : (
              <>
                <div className="text-f13 text-ink mb-2">
                  已立 <span className="font-semibold tnum">{motifGap?.count ?? motifNames.length}</span>
                  {motifGap?.min_required != null && (
                    <>，目标 ≥ <span className="tnum">{motifGap.min_required}</span></>
                  )}
                  {motifGap && motifGap.ok === false && (
                    <span className="ml-2 text-fore">还差 {motifGap.deficit ?? Math.max(0, (motifGap.min_required || 0) - (motifGap.count || 0))} 条</span>
                  )}
                </div>
                {motifNames.length === 0 ? (
                  <BlockFail text="还没立核心母题。去旅程里先立档，再写回响。" />
                ) : (
                  <ul className="flex flex-wrap gap-1.5">
                    {motifNames.map((name) => (
                      <li key={name} className="px-2 py-0.5 rounded-full bg-soft text-f12 text-ink" data-testid="synopsis-motif-chip">
                        {name}
                        <span className="ml-1 text-ok">已立档</span>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>

          {/* 设定统计 */}
          <div className="pb-5 border-b border-line/40" data-testid="synopsis-codex">
            <div className="flex items-center gap-2 mb-3">
              <div className="text-meta font-semibold uppercase tracking-wider text-faint">设定库</div>
              {comp && comp.completeness_score != null && (
                <span className="text-meta text-faint">完整度 {comp.completeness_score}/100</span>
              )}
            </div>
            {comp === undefined ? (
              <div className="text-f13 text-faint">加载设定…</div>
            ) : comp === null ? (
              <BlockFail text="暂时读不到设定库，不影响其他块" />
            ) : (
              <>
                <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
                  {[
                    ['角色', comp.total_chars, Users],
                    ['世界规则', comp.total_rules, Shield],
                    ['势力', comp.total_factions, Swords],
                    ['地点', comp.total_places, MapPin],
                    ['事实/命题', comp.total_facts, BookText],
                  ].map(([label, count, Icon]) => (
                    <div key={label} className="py-1">
                      <div className="flex items-center gap-1.5 text-meta text-faint mb-1"><Icon size={12} />{label}</div>
                      <div className="type-section text-ink tnum">{count ?? 0}</div>
                    </div>
                  ))}
                </div>
                {comp.missing_dimensions?.length > 0 && (
                  <div className="mt-3 text-f12 text-danger">缺失维度:{comp.missing_dimensions.join('、')}</div>
                )}
              </>
            )}
          </div>

          {/* 伏笔平衡速览 */}
          <div className="pb-5 border-b border-line/50" data-testid="synopsis-promises">
            <div className="flex items-center flex-wrap gap-2 mb-2">
              <Bookmark size={15} className="text-fore" />
              <div className="text-meta font-semibold uppercase tracking-wider text-faint">伏笔平衡</div>
              {led && (
                <span className={`text-meta inline-flex items-center gap-1 ${audit.balanced ? 'text-ok' : 'text-danger'}`}>
                  {audit.balanced ? '✓ 已平衡' : <><AlertTriangle size={11} />未平衡</>}
                </span>
              )}
              <button onClick={() => onOpenView?.('insight')}
                className="ml-auto inline-flex items-center gap-1 text-f12 text-brand hover:underline cursor-pointer">
                打开伏笔台账 <ArrowRight size={12} />
              </button>
            </div>
            {led === undefined ? (
              <div className="text-f13 text-faint">加载伏笔…</div>
            ) : led === null ? (
              <BlockFail text="暂时读不到伏笔，不影响其他块" />
            ) : (
              <div className="text-f12 text-faint">
                已埋未收 {(led.open || []).length} · 已回收 {(led.closed || []).length} · 障眼法 {(led.red_herring || []).length}
                · 超期 {audit.overdue_count ?? 0} · 契诃夫 {audit.never_paid ?? 0} 把枪没响
              </div>
            )}
          </div>

          {/* 弱章诊断 */}
          <div data-testid="synopsis-weak">
            <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">最需关注的章</div>
            {q === undefined ? (
              <div className="text-f13 text-faint">加载质检…</div>
            ) : q === null ? (
              <BlockFail text="暂时读不到质检，不影响其他块" />
            ) : cacheStale ? (
              <div className="text-f13 text-fore">质量缓存已过期，请到质量仪表盘刷新后查看诊断。</div>
            ) : weak.length === 0 ? (
              <div className="text-f13 text-ok">✓ 各章质检干净</div>
            ) : weak.map((c) => (
              <button key={c.seq} onClick={() => onJumpChapter?.(c.seq)}
                className="w-full flex items-center gap-2 py-1.5 border-b border-line/40 last:border-0 text-f13 text-left hover:bg-soft/60 rounded-lg px-1.5 -mx-1 transition-colors cursor-pointer">
                <span className="text-ink flex-1 truncate">{chapterLabel(c.seq, c.title)}</span>
                {c.qc_issues > 0 && <span className="text-danger text-f12">QC {c.qc_issues}</span>}
                {c.causal > 0 && <span className="text-fore text-f12">因果 {c.causal}</span>}
              </button>
            ))}
          </div>

          {/* 书级评分卡：懒加载，首屏不请求 northStarBook */}
          <section className="pt-1" data-testid="synopsis-scorecard">
            <div className="flex items-center flex-wrap gap-2 mb-2">
              <Gauge size={15} className="text-brand" />
              <div className="text-meta font-semibold uppercase tracking-wider text-faint">书级评分卡</div>
              <span className="text-meta text-faint">机器只读参考，不是作品意图</span>
            </div>
            <button
              type="button"
              data-testid="synopsis-scorecard-toggle"
              aria-expanded={scoreOpen}
              onClick={() => setScoreOpen((v) => !v)}
              className="text-f12 text-brand hover:underline cursor-pointer"
            >
              {scoreOpen ? '收起评分卡' : '展开书级评分卡'}
            </button>
            {scoreOpen && (
              <div className="mt-3" data-testid="synopsis-scorecard-body">
                <NorthStarPanel scope="book" />
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

export function OverviewView(props) {
  return <SynopsisView {...props} />
}
