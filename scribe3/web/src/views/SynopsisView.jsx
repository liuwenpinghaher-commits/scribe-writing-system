import { useCallback, useEffect, useRef, useState } from 'react'
import { BookText, ArrowRight, Gauge } from 'lucide-react'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel.js'
import { liveTouchesTable } from '../lib/liveRefresh.js'
import { NorthStarPanel } from '../NorthStarPanel'
import { chapterOneLine, progressLineFromOutline } from './synopsisCopy.js'
import { SynopsisIntent } from './SynopsisIntent.jsx'
import { SynopsisCast, SynopsisMotifs, SynopsisPromises, SynopsisWorld } from './SynopsisPortraitBlocks.jsx'

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
  'chapter', 'intent', 'volume', 'chapter_scorecard',
  'character', 'world_rule', 'motif', 'promise', 'foreshadow', '_reconnect',
]

export function SynopsisView({
  workTitle,
  onJumpChapter,
  onOpenView,
  onSelectNode,
  onNavigateToObject,
}) {
  const [outline, setOutline] = useState(undefined)
  const [entities, setEntities] = useState(undefined)
  const [rules, setRules] = useState(undefined)
  const [motifs, setMotifs] = useState(undefined)
  const [ledger, setLedger] = useState(undefined)
  const [scoreOpen, setScoreOpen] = useState(false)
  const liveTimer = useRef(null)

  const loadOutline = useCallback(() => {
    api.outline().then(setOutline).catch(() => setOutline(null))
  }, [])
  const loadCast = useCallback(() => {
    api.entities().then(setEntities).catch(() => setEntities(null))
  }, [])
  const loadWorld = useCallback(() => {
    api.get('/world-rules').then(setRules).catch(() => setRules(null))
  }, [])
  const loadMotifs = useCallback(() => {
    api.motifs().then(setMotifs).catch(() => setMotifs(null))
  }, [])
  const loadLedger = useCallback(() => {
    api.promisesLedger().then(setLedger).catch(() => setLedger(null))
  }, [])

  useEffect(() => {
    loadOutline()
    loadCast()
    loadWorld()
    loadMotifs()
    loadLedger()
  }, [loadOutline, loadCast, loadWorld, loadMotifs, loadLedger])

  useEffect(() => {
    const onLive = (e) => {
      const d = e?.detail
      if (!liveTouchesTable(d, LIVE_TABLES)) return
      clearTimeout(liveTimer.current)
      liveTimer.current = setTimeout(() => {
        if (liveTouchesTable(d, ['chapter', 'volume', 'intent', '_reconnect'])) loadOutline()
        if (liveTouchesTable(d, ['character', '_reconnect'])) loadCast()
        if (liveTouchesTable(d, ['world_rule', '_reconnect'])) loadWorld()
        if (liveTouchesTable(d, ['motif', '_reconnect'])) loadMotifs()
        if (liveTouchesTable(d, ['promise', 'foreshadow', '_reconnect'])) loadLedger()
      }, 300)
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      clearTimeout(liveTimer.current)
      window.removeEventListener('s3-live', onLive)
    }
  }, [loadOutline, loadCast, loadWorld, loadMotifs, loadLedger])

  const lanes = outline ? groupOutline(outline) : []
  const progress = outline ? progressLineFromOutline(outline) : ''

  return (
    <div className="h-full overflow-y-auto bg-canvas" data-testid="synopsis-view">
      <div className="max-w-5xl mx-auto px-6 py-6 md:px-8 md:py-8">
        <div className="flex items-start gap-2 mb-5">
          <BookText size={18} className="text-brand shrink-0 mt-0.5" />
          <div className="min-w-0">
            <h1 className="type-page prose-serif text-ink">总纲</h1>
            <p className="mt-1 text-meta text-faint leading-snug">
              把这本书当一本书来读。不催你写下一笔。
            </p>
          </div>
        </div>

        <section className="mb-5" data-testid="synopsis-intent">
          <SynopsisIntent workTitle={workTitle} />
        </section>

        <section className="mb-5 pb-5 border-b border-line/40" data-testid="synopsis-progress">
          {outline === undefined ? (
            <div className="text-f13 text-faint">加载卷纲…</div>
          ) : outline === null ? (
            <BlockFail text="暂时读不到卷纲，不影响其他块" />
          ) : (
            <div className="flex items-start gap-3">
              <p className="flex-1 min-w-0 text-f13 text-ink leading-snug" data-testid="synopsis-progress-line">
                {progress}
              </p>
              <button
                type="button"
                onClick={() => onOpenView?.('journey')}
                className="shrink-0 inline-flex items-center gap-1 text-f12 text-brand hover:underline cursor-pointer"
                data-testid="synopsis-open-journey"
              >
                去旅程 <ArrowRight size={12} />
              </button>
            </div>
          )}
        </section>

        <section className="pb-5 border-b border-line/40" data-testid="synopsis-outline">
          <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">卷与章</div>
          {outline === undefined || outline === null || lanes.length === 0 ? null : (
            <div className="space-y-2">
              {lanes.map((lane, i) => {
                const title = lane.volume?.title || lane.volume?.name || '未命名卷'
                const intro = (lane.volume?.intro || '').trim()
                const vid = lane.volume?.id
                const introShown = intro.length > 160 ? `${intro.slice(0, 160)}…` : intro
                return (
                  <details key={vid || title} className="rounded-md border border-line/40 bg-surface/40 px-3 py-2" open={i === 0}>
                    <summary
                      className="cursor-pointer text-f13 text-ink font-medium"
                      onClick={(e) => {
                        if (!vid || vid === '_none') return
                        e.preventDefault()
                        onSelectNode?.({ id: `vol:${vid}`, type: 'volume', ref: vid, label: title })
                      }}
                    >
                      {title}
                      <span className="ml-2 text-meta text-faint font-normal">{lane.chapters.length} 章</span>
                    </summary>
                    {introShown ? <p className="mt-1.5 text-f12 text-faint leading-snug">{introShown}</p> : null}
                    <ul className="mt-2 space-y-1">
                      {lane.chapters.map((c) => (
                        <li key={c.seq}>
                          <button
                            type="button"
                            onClick={() => onJumpChapter?.(c.seq)}
                            className="w-full text-left text-f13 py-0.5 hover:text-brand cursor-pointer"
                          >
                            <span className="text-ink">{chapterLabel(c.seq, c.title)}</span>
                            <span className="ml-2 text-faint text-f12">{chapterOneLine(c)}</span>
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

        <section className="py-5 border-b border-line/40">
          <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">这些人</div>
          <SynopsisCast entities={entities} onNavigateToObject={onNavigateToObject} onOpenView={onOpenView} />
        </section>

        <section className="py-5 border-b border-line/40">
          <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">世界怎么运转</div>
          <SynopsisWorld rules={rules} onNavigateToObject={onNavigateToObject} />
        </section>

        <section className="py-5 border-b border-line/40">
          <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">母题</div>
          <SynopsisMotifs motifs={motifs} onNavigateToObject={onNavigateToObject} />
        </section>

        <section className="py-5 border-b border-line/40">
          <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">还没收回的账</div>
          <SynopsisPromises ledger={ledger} onOpenView={onOpenView} />
        </section>

        <section className="pt-5" data-testid="synopsis-scorecard">
          <div className="flex items-center flex-wrap gap-2 mb-2">
            <Gauge size={15} className="text-brand" />
            <div className="text-meta font-semibold uppercase tracking-wider text-faint">书级评分卡</div>
            <span className="text-meta text-faint">机器看这本书的参考，不是作品意图</span>
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
              <NorthStarPanel scope="book" intentHint="synopsis" />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export function OverviewView(props) {
  return <SynopsisView {...props} />
}
