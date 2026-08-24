import { useEffect, useState } from 'react'
import { MessageSquare } from 'lucide-react'
import { api } from '../api'
import { Btn } from '../ui.jsx'
import { seedBookPortraitIntent } from '../lib/chiefSeed.js'

const FIELDS = [
  ['reader_feeling', '读者读完该留下'],
  ['emotional_arc', '情感怎么走'],
  ['red_lines', '不许写'],
  ['imagery', '这本书摸起来'],
]

export function SynopsisIntent({ workTitle }) {
  const [intent, setIntent] = useState(undefined)

  const reload = () => {
    api.intent().then(setIntent).catch(() => setIntent(null))
  }
  useEffect(() => { reload() }, [])
  useEffect(() => {
    const h = () => reload()
    window.addEventListener('s3:intent-changed', h)
    return () => window.removeEventListener('s3:intent-changed', h)
  }, [])

  if (intent === undefined) {
    return <div className="text-f13 text-faint">加载这本书是什么…</div>
  }
  if (intent === null) {
    return <div className="text-f13 text-faint">暂时读不到作品意图，不影响其他块</div>
  }

  const title = String(workTitle || '').trim() || '这本书'
  const north = String(intent.north_star || '').trim()
  const feeling = String(intent.reader_feeling || '').trim()
  const empty = !north && !FIELDS.some(([k]) => String(intent[k] || '').trim())

  return (
    <div data-testid="synopsis-intent-body">
      <div className="text-meta uppercase tracking-wider text-faint mb-1">这本书</div>
      <h2 className="type-section prose-serif text-ink" data-testid="synopsis-work-title">{title}</h2>
      {empty ? (
        <p className="mt-2 text-f14 text-ink" data-testid="synopsis-intent-empty">这本书还没说清自己是什么。</p>
      ) : (
        <>
          <p className="mt-2 text-f16 text-ink leading-snug" data-testid="synopsis-north-star">
            {north || feeling}
          </p>
          {!north && feeling ? (
            <p className="mt-1 text-meta text-faint">还没有一句话概括这本书。</p>
          ) : null}
          <dl className="mt-3 grid gap-2 sm:grid-cols-2">
            {FIELDS.map(([k, label]) => {
              const v = String(intent[k] || '').trim()
              if (!v) return null
              return (
                <div key={k} data-testid={`synopsis-intent-${k}`}>
                  <dt className="text-meta text-faint">{label}</dt>
                  <dd className="text-f13 text-ink leading-snug mt-0.5">{v}</dd>
                </div>
              )
            })}
          </dl>
        </>
      )}
      {empty ? (
        <div className="mt-3">
          <Btn variant="primary" size="sm" data-testid="synopsis-ask-chief" onClick={() => seedBookPortraitIntent()}>
            <MessageSquare size={13} />让主编写入
          </Btn>
        </div>
      ) : null}
    </div>
  )
}
