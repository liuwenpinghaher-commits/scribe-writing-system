import { characterWant, motifLine, openLedgerSummary, portraitCast, ruleLine } from './synopsisCast.js'

function BlockFail({ text }) {
  return <div className="text-f13 text-faint">{text}</div>
}

export function SynopsisCast({ entities, onNavigateToObject, onOpenView }) {
  if (entities === undefined) return <div className="text-f13 text-faint">加载这些人…</div>
  if (entities === null) return <BlockFail text="暂时读不到这些人，不影响其他块" />
  const { shown, hidden } = portraitCast(entities)
  if (!shown.length) return <BlockFail text="还没有人。" />
  return (
    <div data-testid="synopsis-cast">
      <ul className="space-y-1">
        {shown.map((e) => {
          const want = characterWant(e)
          return (
            <li key={e.id || e.name}>
              <button
                type="button"
                className="w-full text-left text-f13 py-0.5 hover:text-brand cursor-pointer"
                onClick={() => onNavigateToObject?.({ type: 'character', id: e.id, label: e.name })}
              >
                <span className="text-ink">{e.name}</span>
                {want ? <span className="ml-2 text-faint">· {want}</span> : null}
              </button>
            </li>
          )
        })}
      </ul>
      <div className="mt-2 flex flex-wrap gap-3 text-f12">
        <button type="button" className="text-brand hover:underline cursor-pointer" onClick={() => onOpenView?.('atlas')}>
          在图谱里看关系
        </button>
        {hidden > 0 ? (
          <button type="button" className="text-faint hover:text-ink cursor-pointer" onClick={() => onOpenView?.('atlas')}>
            还有 {hidden} 人，去设定库
          </button>
        ) : null}
      </div>
    </div>
  )
}

export function SynopsisWorld({ rules, onNavigateToObject }) {
  if (rules === undefined) return <div className="text-f13 text-faint">加载世界规矩…</div>
  if (rules === null) return <BlockFail text="暂时读不到世界规矩，不影响其他块" />
  const rows = (Array.isArray(rules) ? rules : []).slice(0, 8).map(ruleLine).filter((r) => r.name)
  if (!rows.length) return <BlockFail text="世界规矩还没写下。" />
  return (
    <ul className="space-y-1" data-testid="synopsis-world">
      {rows.map((r) => (
        <li key={r.name}>
          <button
            type="button"
            className="w-full text-left text-f13 py-0.5 hover:text-brand cursor-pointer"
            onClick={() => onNavigateToObject?.({ type: 'world_rule', id: r.name, label: r.name })}
          >
            <span className="text-ink">{r.name}</span>
            {r.detail ? <span className="ml-2 text-faint">{r.detail}</span> : null}
          </button>
        </li>
      ))}
    </ul>
  )
}

export function SynopsisMotifs({ motifs, onNavigateToObject }) {
  if (motifs === undefined) return <div className="text-f13 text-faint">加载母题…</div>
  if (motifs === null) return <BlockFail text="暂时读不到母题，不影响其他块" />
  const rows = (Array.isArray(motifs) ? motifs : []).map(motifLine).filter((m) => m.name)
  if (!rows.length) return <BlockFail text="还没立母题。" />
  return (
    <ul className="space-y-1" data-testid="synopsis-motifs">
      {rows.map((m) => (
        <li key={m.id || m.name}>
          <button
            type="button"
            className="w-full text-left text-f13 py-0.5 hover:text-brand cursor-pointer"
            onClick={() => onNavigateToObject?.({ type: 'motif', id: `motif:${m.id || m.name}`, label: m.name })}
          >
            <span className="text-ink">{m.name}</span>
            {m.one ? <span className="ml-2 text-faint">{m.one}</span> : null}
          </button>
        </li>
      ))}
    </ul>
  )
}

export function SynopsisPromises({ ledger, onOpenView }) {
  if (ledger === undefined) return <div className="text-f13 text-faint">加载还没收回的账…</div>
  if (ledger === null) return <BlockFail text="暂时读不到未收的账，不影响其他块" />
  const { n, overdueN, items } = openLedgerSummary(ledger)
  if (!n) return null
  return (
    <div data-testid="synopsis-promises">
      <p className="text-f13 text-ink">
        还没收回 {n} 笔
        {overdueN > 0 ? `，其中 ${overdueN} 笔埋了超过三章还没收回` : ''}
      </p>
      {items.length ? (
        <ul className="mt-1 space-y-0.5 text-f12 text-faint">
          {items.map((t) => <li key={t}>{t}</li>)}
        </ul>
      ) : null}
      <button
        type="button"
        className="mt-2 text-f12 text-brand hover:underline cursor-pointer"
        onClick={() => onOpenView?.('insight')}
      >
        看全部
      </button>
    </div>
  )
}
