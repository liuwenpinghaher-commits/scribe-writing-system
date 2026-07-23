import { useEffect, useMemo, useRef, useState } from 'react'
import { BookOpen, Drama, Eye, FileSearch, Lock } from 'lucide-react'
import { api } from './api'
import { Empty } from './ui'
import { useSelection } from './selectionContext'

// 块三:帧行(知识帧/戏剧反讽的一条事实)→ 通用 focus。value 为 null 即私密(面板本身就打码)。
function factFocus(f, irony) {
  const secret = f.value == null
  const label = `${f.entity ? f.entity + '·' : ''}${f.attribute}${secret ? '' : ':' + f.value}`
  return { type: 'frame_fact', id: String(f.id), label, payload: { secret, irony: !!irony }, origin: 'panel' }
}

function factTitle(f) {
  if (f.titleText) return f.titleText
  return `${f.entity ? f.entity + ' · ' : ''}${f.attribute}`
}

function factValue(f) {
  if (f.valueText != null) return String(f.valueText)
  return f.value == null ? '私密/未知' : String(f.value)
}

function localEntityName(entity) {
  return String(entity || '').replace(/^[^:]+:/, '') || '未命名对象'
}

function materialAssociationRows(rows) {
  return (Array.isArray(rows) ? rows : []).map((row, index) => {
    const ref = row.material_id || row.id || row.ref || row.material || `material-${index}`
    const title = row.title || row.label || String(ref)
    const kind = row.kind || row.material_kind || row.type || '素材'
    const phase = row.phase ? ` · ${row.phase}` : ''
    return {
      id: `material:${ref}`,
      titleText: title,
      valueText: `${kind}${phase}`,
      entity: '素材库',
      attribute: title,
      value: kind,
      tone: 'brand',
      badge: '素材',
      targetNode: { id: `material:${ref}`, type: 'material', ref, label: title, meta: { kind } },
    }
  })
}

function factAssociationRows(rows) {
  return (Array.isArray(rows) ? rows : []).map((row, index) => {
    const entity = row.entity || row.entity_id || row.subject || ''
    const name = localEntityName(entity)
    const attr = row.attribute || row.predicate || '设定'
    const ref = row.id || row.local || `${name}:${attr}:${index}`
    const targetNode = String(entity).startsWith('role:')
      ? { id: `character:${name}`, type: 'character', ref: name, label: name }
      : { id: `proposition:${ref}`, type: 'proposition', ref, label: `${name} · ${attr}` }
    return {
      id: `codex:${ref}`,
      titleText: `${name} · ${attr}`,
      valueText: row.value == null ? '未显性落值' : String(row.value),
      entity: name,
      attribute: attr,
      value: row.value,
      chapter: row.chapter,
      tone: 'brand',
      badge: '设定',
      targetNode,
    }
  })
}

function relationAssociationRows(rows) {
  return (Array.isArray(rows) ? rows : []).map((row, index) => {
    const src = localEntityName(row.src || row.source || row.from || row.character_a)
    const dst = localEntityName(row.dst || row.target || row.to || row.character_b)
    const relation = row.relation || row.kind || row.label || '关系'
    return {
      id: `relation:${row.id || `${src}:${dst}:${relation}:${index}`}`,
      titleText: `${src} -> ${dst}`,
      valueText: relation,
      entity: src,
      attribute: relation,
      value: dst,
      chapter: row.chapter,
      tone: 'brand',
      badge: '关系',
      targetNode: { id: `character:${src}`, type: 'character', ref: src, label: src },
    }
  })
}

function motifAssociationRows(rows) {
  return (Array.isArray(rows) ? rows : []).map((row, index) => {
    const ref = row.motif_id || row.id || row.ref || `motif-${index}`
    const title = row.title || row.label || String(ref)
    return {
      id: `motif:${ref}:${row.chapter || ''}:${index}`,
      titleText: title,
      valueText: row.chapter != null ? `第 ${row.chapter} 章` : '本章母题',
      entity: '母题',
      attribute: title,
      value: row.chapter,
      tone: 'ok',
      badge: '母题',
      targetNode: { id: `motif:${ref}`, type: 'motif_view', ref, label: title },
    }
  })
}

function promiseAssociationRows(ledger, chapter) {
  const rows = []
  const add = (kind, label, items) => {
    ;(Array.isArray(items) ? items : []).forEach((row, index) => {
      const ref = row.id || row.promise_id || row.title || `${kind}-${index}`
      const title = row.title || row.label || row.text || String(ref)
      rows.push({
        id: `promise:${kind}:${ref}`,
        titleText: title,
        valueText: label,
        entity: '伏笔',
        attribute: title,
        value: label,
        chapter: row.chapter || row.plant_chapter || chapter,
        tone: kind === 'red_herring' ? 'warn' : 'brand',
        badge: label,
        targetNode: { id: `promise:${ref}`, type: 'promise_view', ref, label: title, meta: { kind } },
      })
    })
  }
  add('open', '未回收', ledger?.open)
  add('closed', '已回收', ledger?.closed)
  add('red_herring', '反讽/误导', ledger?.red_herring)
  return rows
}

function issueAssociationRows(payload) {
  const rows = Array.isArray(payload) ? payload : (Array.isArray(payload?.issues) ? payload.issues : [])
  return rows.map((row, index) => {
    const ref = row.id || row.code || row.title || `issue-${index}`
    const title = row.title || row.message || row.summary || String(ref)
    return {
      id: `issue:${ref}`,
      titleText: title,
      valueText: row.severity || row.tone || '待校验',
      entity: '校验',
      attribute: title,
      value: row.severity,
      tone: row.severity === 'error' ? 'danger' : 'warn',
      badge: '校验',
      targetNode: { id: `issue:${ref}`, type: 'review_issue', ref, label: title, payload: row },
    }
  })
}

function focalizerLabel(value, options) {
  return options.find((o) => o.value === value)?.label || String(value || '').replace(/^role:/, '') || '未设'
}

function normalizeFocalizers(options, current) {
  const rows = []
  const seen = new Set()
  const add = (value, label) => {
    if (!value || seen.has(value)) return
    seen.add(value)
    rows.push({ value, label: label || String(value).replace(/^role:/, '') })
  }
  add(current, String(current || '').replace(/^role:/, ''))
  ;(options || []).forEach((c) => {
    if (typeof c === 'string') add(c, c.replace(/^role:/, ''))
    else add(c.id || c.ref || c.local || c.name, c.name || c.label || c.local || c.id)
  })
  return rows
}

function toneBorder(tone) {
  if (tone === 'ok') return 'border-l-ok'
  if (tone === 'danger') return 'border-l-danger'
  if (tone === 'warn') return 'border-l-warn'
  if (tone === 'brand') return 'border-l-brand'
  return 'border-l-line'
}

function toneText(tone) {
  if (tone === 'ok') return 'text-ok'
  if (tone === 'danger') return 'text-danger'
  if (tone === 'warn') return 'text-warn'
  if (tone === 'brand') return 'text-brand'
  return 'text-ink'
}


// 详情正文:优先值 + 一行操作提示,不堆「分类含义/写作约束/当前范围」空话。
function compactDetailBody(section, fact) {
  if (!fact) return []
  const value = factValue(fact)
  const rows = []
  if (value && value !== '私密/未知') rows.push(['当前值', value])
  else if (value === '私密/未知') rows.push(['状态', '当前 POV 未知 / 私密'])
  if (section?.detailHint) rows.push(['提示', section.detailHint])
  return rows
}

function FactButton({ fact, onPick, active }) {
  const showBadge = fact.badge && (fact.tone === 'danger' || fact.tone === 'warn' || fact.badge === '反讽')
  return (
    <button type="button" onClick={onPick} data-testid="frame-fact-row"
      className={`w-full flex items-start gap-2 py-1.5 px-1 text-left cursor-pointer transition-colors rounded-md ${active ? 'bg-brand/10 text-brand' : 'text-ink hover:bg-soft/60'}`}>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-f13 font-medium leading-snug">{factTitle(fact)}</span>
          {showBadge && <span className={`shrink-0 text-meta ${toneText(fact.tone)}`}>{fact.badge}</span>}
        </div>
        <div className="mt-0.5 truncate text-meta text-faint leading-snug">{factValue(fact)}</div>
      </div>
      {fact.targetNode && <span className="shrink-0 text-meta text-faint mt-0.5" aria-hidden>→</span>}
    </button>
  )
}

function DetailStrip({ model, onOpenTarget }) {
  if (!model) return null
  return (
    <aside aria-label="关联详情" data-testid="frame-detail" className="mt-3 border-t border-line/40 pt-3">
      <div className="text-meta text-faint">{model.kicker}</div>
      <h3 className="mt-0.5 type-section text-ink leading-snug">{model.title}</h3>
      {model.value && <div className="mt-1 text-f13 text-ink">{model.value}</div>}
      {model.sub && <div className="mt-1 text-f12 text-faint leading-relaxed">{model.sub}</div>}
      {model.body?.length > 0 && (
        <div className="mt-2 space-y-1.5">
          {model.body.map(([label, value]) => (
            <div key={label} className="text-f12">
              <span className="text-faint">{label} · </span>
              <span className="text-ink">{value}</span>
            </div>
          ))}
        </div>
      )}
      {model.onOpen && (
        <button type="button" onClick={model.onOpen}
          className="mt-3 h-8 rounded-lg bg-brand px-3 text-f12 font-medium text-brandfg cursor-pointer">
          打开原详情
        </button>
      )}
    </aside>
  )
}

const ASSOC_KEYS = new Set(['codex', 'materials', 'promise', 'motif', 'review'])
const FRAME_KEYS = new Set(['write', 'forbid', 'irony', 'source'])

// 关联:章级设定/素材/伏笔/母题/校验 + 限知写作决策。默认单列 master–detail,无三列 min-width 横滚。
export function FramePanel({ work, meta, focalizer, chapter, focalizerOptions = [], onSelectNode }) {
  const { focus, setFocus } = useSelection()
  const [frame, setFrame] = useState([])
  const [irony, setIrony] = useState([])
  const [materialRefs, setMaterialRefs] = useState([])
  const [chapterFacts, setChapterFacts] = useState([])
  const [relations, setRelations] = useState([])
  const [motifs, setMotifs] = useState([])
  const [promiseLedger, setPromiseLedger] = useState(null)
  const [reviewIssues, setReviewIssues] = useState([])
  const [active, setActive] = useState('codex')
  const [picked, setPicked] = useState(null)
  const focusRef = useRef(focus)
  const options = useMemo(() => normalizeFocalizers(focalizerOptions, focalizer), [focalizerOptions, focalizer])
  const defaultFocalizer = focalizer || options[0]?.value || ''
  const [activeFocalizer, setActiveFocalizer] = useState(defaultFocalizer)

  useEffect(() => { focusRef.current = focus }, [focus])
  useEffect(() => { setActiveFocalizer(defaultFocalizer) }, [defaultFocalizer])

  const effectiveFocalizer = activeFocalizer || defaultFocalizer

  useEffect(() => {
    let alive = true
    setPicked(null)
    const currentFocus = focusRef.current
    if (currentFocus?.type === 'frame_fact' && currentFocus.origin === 'panel') setFocus(null)
    if (effectiveFocalizer) {
      api.frame(effectiveFocalizer, chapter).then((rows) => { if (alive) setFrame(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setFrame([]) })
      api.irony(effectiveFocalizer, chapter).then((rows) => { if (alive) setIrony(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setIrony([]) })
    } else { setFrame([]); setIrony([]) }
    return () => { alive = false }
  }, [effectiveFocalizer, chapter, setFocus])

  useEffect(() => {
    let alive = true
    setMaterialRefs([])
    setChapterFacts([])
    setRelations([])
    setMotifs([])
    setPromiseLedger(null)
    setReviewIssues([])
    if (chapter == null) return () => { alive = false }
    api.materialRefsByChapter(chapter).then((rows) => { if (alive) setMaterialRefs(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setMaterialRefs([]) })
    api.facts(chapter).then((rows) => { if (alive) setChapterFacts(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setChapterFacts([]) })
    api.characterRelations(chapter).then((rows) => { if (alive) setRelations(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setRelations([]) })
    api.motifInstances(chapter, work).then((rows) => { if (alive) setMotifs(Array.isArray(rows) ? rows : []) }).catch(() => { if (alive) setMotifs([]) })
    api.promisesLedger(work).then((rows) => { if (alive) setPromiseLedger(rows || {}) }).catch(() => { if (alive) setPromiseLedger({}) })
    api.issues(chapter).then((rows) => { if (alive) setReviewIssues(rows || {}) }).catch(() => { if (alive) setReviewIssues({ issues: [] }) })
    return () => { alive = false }
  }, [chapter, work])

  const writable = frame.filter((f) => f.value != null).map((f) => ({ ...f, tone: 'ok', badge: '可写' }))
  const forbidden = frame.filter((f) => f.value == null).map((f) => ({ ...f, tone: 'danger', badge: '禁写' }))
  const ironyRows = irony.map((f) => ({ ...f, tone: 'brand', badge: '反讽' }))
  const codexRows = [...factAssociationRows(chapterFacts), ...relationAssociationRows(relations)]
  const materialRows = materialAssociationRows(materialRefs)
  const motifRows = motifAssociationRows(motifs)
  const promiseRows = promiseAssociationRows(promiseLedger, chapter)
  const issueRows = issueAssociationRows(reviewIssues)
  const sourceRows = [
    ...frame.map((f) => ({ ...f, sourceKind: '知识帧', tone: f.value == null ? 'danger' : 'ok', badge: '来源' })),
    ...irony.map((f) => ({ ...f, sourceKind: '戏剧反讽', tone: 'brand', badge: '反讽' })),
  ]

  const sections = [
    { key: 'codex', label: '本章设定', domain: 'assoc', detailHint: '点击进入设定库原详情。', empty: '本章暂无设定', items: codexRows, tone: 'brand' },
    { key: 'materials', label: '本章素材', domain: 'assoc', detailHint: '点击进入素材详情。', empty: '本章暂无素材', items: materialRows, tone: 'brand' },
    { key: 'promise', label: '本章伏笔', domain: 'assoc', detailHint: '点击查看伏笔状态。', empty: '本章暂无伏笔', items: promiseRows, tone: 'brand' },
    { key: 'motif', label: '本章母题', domain: 'assoc', detailHint: '点击进入母题详情。', empty: '本章暂无母题', items: motifRows, tone: 'ok' },
    { key: 'review', label: '本章校验', domain: 'assoc', detailHint: '点击定位校验项。', empty: '本章暂无校验', items: issueRows, tone: 'warn' },
    { key: 'write', label: '可写事实', domain: 'frame', detailHint: '可从当前 POV 安全写入正文。', empty: '暂无可写事实', items: writable, tone: 'ok' },
    { key: 'forbid', label: '禁止泄露', domain: 'frame', detailHint: '当前 POV 不知道,直接写出有限知风险。', empty: '暂无禁写项', items: forbidden, tone: 'danger' },
    { key: 'irony', label: '戏剧反讽', domain: 'frame', detailHint: '读者可知而 POV 不能确认。', empty: '暂无反讽', items: ironyRows, tone: 'brand' },
    { key: 'source', label: '来源账本', domain: 'frame', detailHint: '知识帧与反讽来源合并账。', empty: '暂无来源', items: sourceRows, tone: 'muted' },
  ]

  const assocSections = sections.filter((s) => s.domain === 'assoc')
  const frameSections = sections.filter((s) => s.domain === 'frame')
  const activeSection = sections.find((s) => s.key === active) || sections[0]
  const pickedSection = picked ? (sections.find((s) => s.key === picked.sectionKey) || activeSection) : activeSection
  const focalizerName = focalizerLabel(effectiveFocalizer, options)

  const detailModel = picked ? {
    kind: 'fact',
    title: factTitle(picked.fact),
    kicker: `${picked.fact.targetNode ? '章级关联' : '限知'} · ${pickedSection.label}`,
    sub: pickedSection.detailHint,
    value: factValue(picked.fact),
    body: compactDetailBody(pickedSection, picked.fact),
    onOpen: picked.fact.targetNode ? () => onSelectNode?.(picked.fact.targetNode) : null,
  } : null

  const summaryChips = [
    ['设定', codexRows.length],
    ['素材', materialRows.length],
    ['伏笔', promiseRows.length],
    ['可写', writable.length],
    ['禁写', forbidden.length],
    ['反讽', ironyRows.length],
  ]

  const pickSection = (key) => {
    setActive(key)
    setPicked(null)
  }

  const pickFact = (sectionKey, fact) => {
    setActive(sectionKey)
    setPicked({ sectionKey, fact })
    if (fact.targetNode) {
      onSelectNode?.(fact.targetNode)
      setFocus({ type: 'chapter_association', id: fact.id, label: factTitle(fact), payload: { target: fact.targetNode }, origin: 'panel' })
      return
    }
    setFocus(factFocus(fact, sectionKey === 'irony' || fact.sourceKind === '戏剧反讽'))
  }

  const renderDomain = (title, domainSections) => (
    <section className="min-w-0" data-testid={title === '本章关联' ? 'frame-domain-assoc' : 'frame-domain-frame'}>
      <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">{title}</div>
      <div className="space-y-1">
        {domainSections.map((section) => {
          const expanded = active === section.key
          const n = section.items.length
          return (
            <div key={section.key}>
              <button
                type="button"
                aria-label={`${section.label} ${n}`}
                aria-expanded={expanded}
                onClick={() => pickSection(section.key)}
                className={`w-full flex items-center justify-between gap-2 py-1.5 px-1 text-left cursor-pointer rounded-md ${expanded ? 'text-brand' : 'text-ink hover:bg-soft/50'}`}
              >
                <span className="text-f13 font-medium">{section.label}</span>
                <span className={`text-meta tnum ${n ? toneText(section.tone) : 'text-faint'}`}>{n}</span>
              </button>
              {expanded && (
                <div className="ml-2 border-l border-line/40 pl-2 mb-2" data-testid={`frame-section-${section.key}`}>
                  {n === 0 ? (
                    <div className="py-1 text-meta text-faint">{section.empty}</div>
                  ) : (
                    section.items.map((f) => (
                      <FactButton
                        key={`${section.key}:${f.sourceKind || ''}:${f.id}`}
                        fact={f}
                        active={picked?.sectionKey === section.key && picked?.fact?.id === f.id}
                        onPick={() => pickFact(section.key, f)}
                      />
                    ))
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )

  return (
    <div className="h-full min-h-0 flex flex-col bg-canvas" data-testid="frame-panel-root">
      <div className="shrink-0 border-b border-line/40 px-4 py-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="type-section text-ink">第 {chapter} 章 · 关联</div>
          {options.length > 1 ? (
            <label className="flex items-center gap-1.5 text-f12 text-faint">
              <span>视角</span>
              <select
                aria-label="限知视角"
                value={effectiveFocalizer}
                onChange={(e) => { setActiveFocalizer(e.target.value); setActive('write'); setPicked(null) }}
                className="h-7 rounded-md border-0 bg-soft/80 px-2 text-f12 text-ink outline-none"
              >
                {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
          ) : (
            <div className="text-f12 text-faint">视角 · {focalizerName || '未设'}</div>
          )}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-meta text-faint" data-testid="frame-summary-chips">
          {summaryChips.map(([label, value]) => (
            <span key={label} className="tnum">{label} {value}</span>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-4 py-3" data-testid="frame-assoc-board">
        {/* 默认单列纵排,禁止 min-w 三列宽板 */}
        <nav aria-label="关联上下文树" className="max-w-[40rem] space-y-5">
          {renderDomain('本章关联', assocSections)}
          {effectiveFocalizer ? (
            renderDomain('限知边界', frameSections)
          ) : (
            <section data-testid="frame-domain-frame">
              <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">限知边界</div>
              <Empty>作者全知视角——暂无限知约束</Empty>
            </section>
          )}
          {picked && !picked.fact?.targetNode && <DetailStrip model={detailModel} />}
          {picked && picked.fact?.targetNode && (
            <DetailStrip model={detailModel} />
          )}
        </nav>
      </div>
    </div>
  )
}
