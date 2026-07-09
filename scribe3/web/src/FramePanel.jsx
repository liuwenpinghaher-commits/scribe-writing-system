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

function factRows(section, fact) {
  const title = factTitle(fact)
  const value = factValue(fact)
  if (section.key === 'write') {
    return [
      ['为什么可写', '这是当前 POV 已经知道、看见或能直接感到的信息。'],
      ['写法', value === '私密/未知' ? `只写 ${title} 的外在痕迹。` : `可以把“${value}”进入动作、判断或正文细节。`],
      ['边界', '仍然不要替角色解释他尚未掌握的机制或幕后因果。'],
    ]
  }
  if (section.key === 'forbid') {
    return [
      ['为什么禁写', '当前 POV 不知道这条信息,直接写出会造成限知泄露。'],
      ['可写替代', `把“${title}”改写成痕迹、误读、停顿、遮掩动作或后续回收点。`],
      ['戏剧价值', '读者能感觉背后有规则在运转,角色仍只能把它当成怪事。'],
    ]
  }
  if (section.key === 'irony') {
    return [
      ['张力', '读者知道或能猜到,但当前 POV 不能确认。'],
      ['写法', `保留“${title}”的线索,让角色做出有限、甚至错误的判断。`],
      ['边界', '不要让角色替读者总结真相,把信息差留在动作和环境里。'],
    ]
  }
  if (section.key === 'blind') {
    return [
      ['章内作用', '这是当前 POV 的合理误判,用于保护限知并制造后续翻转。'],
      ['写法', '让错误解释看起来成立,同时留一个小缺口。'],
      ['后续', '等新事实出现时再推翻这个判断。'],
    ]
  }
  return [
    ['来源用途', '这条记录用于反查知识帧或戏剧反讽的来源。'],
    ['命中值', value],
    ['下一步', '需要进入设定、素材或正文详情时,先聚焦给主编接手。'],
  ]
}

function relatedRows(section, fact) {
  if (fact.targetNode) {
    const rows = [[section.label, factTitle(fact)], ['打开详情', fact.targetNode.label || fact.targetNode.ref || fact.targetNode.id]]
    if (fact.chapter != null) rows.push(['正文证据', `第 ${fact.chapter} 章`])
    rows.push(['详情类型', fact.targetNode.type])
    return rows
  }
  const entity = String(fact.entity || '').replace(/^role:/, '') || '本章事实'
  const rows = [[section.label, factTitle(fact)], ['设定库', entity]]
  if (fact.chapter != null) rows.push(['正文证据', `第 ${fact.chapter} 章`])
  if (section.key === 'irony') rows.push(['禁写', '当前 POV 不能确认'])
  return rows
}

function groupRows(section, focalizerName) {
  if (section.key === 'codex') {
    return [
      ['分类含义', '本章正文、简报或推演已经引用到的设定库对象。'],
      ['写作约束', '点击条目进入原设定详情,不在关联页复制第二套编辑表单。'],
      ['当前范围', `本章设定有 ${section.items.length} 条,用于核对角色、命题和关系是否闭环。`],
    ]
  }
  if (section.key === 'materials') {
    return [
      ['分类含义', '本章引用过或可追溯到的素材库材料。'],
      ['写作约束', '素材是参考与来源,进入详情后再决定是否吸收为设定或正文证据。'],
      ['当前范围', `本章素材有 ${section.items.length} 条,点击可回到素材库完整详情。`],
    ]
  }
  if (section.key === 'promise') {
    return [
      ['分类含义', '本章相关的伏笔、误导与回收状态。'],
      ['写作约束', '伏笔只给结构提示,正文仍要靠场景动作落地。'],
      ['当前范围', `本章伏笔有 ${section.items.length} 条。`],
    ]
  }
  if (section.key === 'motif') {
    return [
      ['分类含义', '本章出现的母题实例与主题回声。'],
      ['写作约束', '母题用于统一意象和价值判断,避免只堆符号。'],
      ['当前范围', `本章母题有 ${section.items.length} 条。`],
    ]
  }
  if (section.key === 'review') {
    return [
      ['分类含义', '本章校验、搜索或一致性检查命中的待处理项。'],
      ['写作约束', '先定位真实问题,再决定修改正文、设定还是素材。'],
      ['当前范围', `本章校验有 ${section.items.length} 条。`],
    ]
  }
  if (section.key === 'write') {
    return [
      ['分类含义', '这类事实可以进入当前 POV 的感知、行动和判断。'],
      ['写作约束', '写作时仍要保留角色表达方式,不要替作者解释世界观。'],
      ['当前范围', `${focalizerName} 的可写事实中有 ${section.items.length} 条,先用于判断本章能不能写、怎么写。`],
    ]
  }
  if (section.key === 'forbid') {
    return [
      ['分类含义', '这类事实不应进入当前 POV 的内心、判断或直接叙述。'],
      ['写作约束', '适合转成痕迹、动作、错觉或后文回收点。'],
      ['当前范围', `${focalizerName} 的禁写事实中有 ${section.items.length} 条,重点防止本章提前说破。`],
    ]
  }
  if (section.key === 'irony') {
    return [
      ['分类含义', '这类信息读者可以察觉,但当前 POV 不能确认。'],
      ['写作约束', '重点是制造信息差,不要让角色替读者总结真相。'],
      ['当前范围', `${focalizerName} 的反讽线索中有 ${section.items.length} 条,用于制造悬念和误读。`],
    ]
  }
  if (section.key === 'blind') {
    return [
      ['分类含义', '这类内容是当前 POV 的合理误判。'],
      ['写作约束', '盲区要可理解,后续被事实推翻时才有说服力。'],
      ['当前范围', `${focalizerName} 的盲区暂未由接口返回,这里保留真实入口。`],
    ]
  }
  return [
    ['分类含义', '这类对象把知识帧和戏剧反讽合并成可追溯账本。'],
    ['写作约束', '来源账本用于查证,不等同于正文可以直接写出的内容。'],
    ['当前范围', `${focalizerName} 的来源账本中有 ${section.items.length} 条记录。`],
  ]
}

function FactButton({ fact, icon: Icon, onPick, active }) {
  return (
    <button type="button" onClick={onPick}
      className={`group w-full rounded-lg border border-transparent border-l-4 ${toneBorder(fact.tone)} bg-surface px-3 py-2 text-left transition-colors cursor-pointer ${active ? 'border-line bg-brand/10 text-brand shadow-sm' : 'hover:border-line hover:bg-soft/70 text-ink'}`}>
      <div className="flex min-w-0 items-start gap-2">
        {Icon && <Icon size={14} className="mt-0.5 shrink-0 text-faint" />}
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <div className="truncate text-f12 font-semibold leading-snug">{factTitle(fact)}</div>
            <span className="shrink-0 rounded-full bg-soft px-2 py-0.5 text-f10 text-faint">{fact.badge}</span>
          </div>
          <div className="mt-0.5 truncate text-f11 text-faint leading-snug">{factValue(fact)}</div>
        </div>
      </div>
    </button>
  )
}

function DetailArticle({ model, compact = false, onFull }) {
  if (!model) return null
  return (
    <article aria-label={model.kind === 'fact' ? '事实详情' : '分类总览'}
      className="grid min-h-0 overflow-hidden rounded-lg border border-line bg-surface shadow-[0_10px_30px_rgba(38,36,31,.06)]">
      <div className="border-b border-line/70 bg-brand/5 px-4 py-3">
        <div className="text-f11 font-semibold text-faint">{model.kind === 'fact' ? '事实详情' : '分类总览'}</div>
        <div className="text-f11 font-semibold text-faint">{model.kicker}</div>
        <h3 className="mt-1 text-f20 font-semibold leading-tight text-ink">{model.title}</h3>
        <div className="mt-1 text-f12 leading-relaxed text-faint">{model.sub}</div>
        {model.value && <div className="mt-2 inline-flex rounded-md bg-surface px-2 py-1 text-f12 font-medium text-ink">{model.value}</div>}
      </div>
      <div className="min-h-0 overflow-y-auto px-4 py-3">
        <div className="grid gap-3">
          {model.body.map(([label, value], index) => (
            <section key={label}>
              <div className="mb-1 text-f11 font-semibold tracking-wide text-faint">{label}</div>
              <div className={`text-f13 leading-relaxed text-ink ${index === 1 ? 'rounded-r-lg border-l-2 border-brand bg-canvas px-3 py-2' : ''}`}>{value}</div>
            </section>
          ))}
          {!compact && model.kind === 'fact' && (
            <section>
              <div className="mb-1 text-f11 font-semibold tracking-wide text-faint">关联跳转</div>
              <div className="grid gap-1.5">
                {model.related.map(([label, value]) => (
                  <div key={`${label}:${value}`} className="rounded-md border border-line/70 bg-canvas px-2 py-1.5">
                    <div className="text-f12 font-medium text-ink">{label}</div>
                    <div className="text-f11 text-faint">{value}</div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t border-line/70 bg-canvas/70 px-4 py-3">
        {model.kind === 'fact' && <button type="button" onClick={onFull} className="h-8 rounded-md bg-brand px-3 text-f12 font-medium text-brandfg">打开完整详情</button>}
        <button type="button" className="h-8 rounded-md border border-line bg-surface px-3 text-f12 text-ink">固定到本章</button>
        <button type="button" className="h-8 rounded-md px-3 text-f12 text-faint hover:bg-soft">问主编</button>
      </div>
    </article>
  )
}

function FullDetail({ model, path, onBack }) {
  if (!model) return null
  return (
    <section aria-label="完整限知详情" className="min-h-0 overflow-y-auto px-4 py-4">
      <div className="sticky top-0 z-10 mb-3 flex items-center justify-between gap-3 rounded-lg border border-brand/20 bg-brand/10 px-3 py-2 text-brand shadow-sm">
        <button type="button" onClick={onBack} className="h-8 rounded-md border border-line bg-surface px-3 text-f12 text-ink">返回上下文树</button>
        <span className="min-w-0 truncate text-f12">{path}</span>
      </div>
      <div className="grid overflow-hidden rounded-lg border border-line bg-surface shadow-[0_10px_30px_rgba(38,36,31,.06)] lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="min-w-0 px-5 py-5">
          <div className="text-f11 font-semibold text-faint">{model.kicker}</div>
          <h3 className="mt-1 text-f24 font-semibold leading-tight text-ink">{model.title}</h3>
          <div className="mt-2 text-f13 leading-relaxed text-faint">{model.sub}</div>
          <div className="mt-5 grid gap-4">
            {model.body.map(([label, value], index) => (
              <section key={label}>
                <div className="mb-1 text-f11 font-semibold tracking-wide text-faint">{label}</div>
                <div className={`text-f13 leading-relaxed text-ink ${index === 1 ? 'rounded-r-lg border-l-2 border-brand bg-canvas px-3 py-2' : ''}`}>{value}</div>
              </section>
            ))}
            <section>
              <div className="mb-1 text-f11 font-semibold tracking-wide text-faint">返回机制</div>
              <div className="grid grid-cols-[4.5rem_1fr] gap-2 text-f12">
                <span className="text-faint">返回</span><span>点击顶部返回条,回到上下文树并保留选中的分组和对象。</span>
                <span className="text-faint">跳转</span><span>后续可复用设定库、素材库、伏笔或正文的详情页,不复制一套详情 UI。</span>
                <span className="text-faint">定位</span><span>返回后路径仍停在当前限知事实。</span>
              </div>
            </section>
          </div>
        </div>
        <aside className="border-t border-line bg-canvas px-4 py-4 lg:border-l lg:border-t-0">
          <div className="mb-2 text-f11 font-semibold tracking-wide text-faint">来源路径</div>
          <div className="grid gap-2 text-f12">
            {model.related.map(([label, value]) => (
              <div key={`${label}:${value}`} className="rounded-md border border-line/70 bg-surface px-2 py-1.5">
                <div className="font-medium text-ink">{label}</div>
                <div className="text-faint">{value}</div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  )
}

// 关联:章级设定/素材/伏笔/母题/校验 + 限知写作决策面板。
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
  const [active, setActive] = useState('write')
  const [picked, setPicked] = useState(null)
  const [orientation, setOrientation] = useState('wide')
  const [fullOpen, setFullOpen] = useState(false)
  const focusRef = useRef(focus)
  const options = useMemo(() => normalizeFocalizers(focalizerOptions, focalizer), [focalizerOptions, focalizer])
  const defaultFocalizer = focalizer || options[0]?.value || ''
  const [activeFocalizer, setActiveFocalizer] = useState(defaultFocalizer)

  useEffect(() => { focusRef.current = focus }, [focus])

  useEffect(() => {
    setActiveFocalizer(defaultFocalizer)
  }, [defaultFocalizer])

  const effectiveFocalizer = activeFocalizer || defaultFocalizer

  useEffect(() => {
    let alive = true
    setPicked(null)
    setFullOpen(false)
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
  const forbidden = frame.filter((f) => f.value == null).map((f) => ({ ...f, tone: 'danger', badge: '风险' }))
  const ironyRows = irony.map((f) => ({ ...f, tone: 'brand', badge: '反讽' }))
  const codexRows = [...factAssociationRows(chapterFacts), ...relationAssociationRows(relations)]
  const materialRows = materialAssociationRows(materialRefs)
  const motifRows = motifAssociationRows(motifs)
  const promiseRows = promiseAssociationRows(promiseLedger, chapter)
  const issueRows = issueAssociationRows(reviewIssues)
  const sourceRows = [
    ...frame.map((f) => ({ ...f, sourceKind: '知识帧', tone: f.value == null ? 'danger' : 'ok', badge: '来源' })),
    ...irony.map((f) => ({ ...f, sourceKind: '戏剧反讽', tone: 'brand', badge: '来源' })),
  ]
  const sections = [
    {
      key: 'codex', label: '本章设定', title: '本章设定',
      description: '本章已经牵连到的角色、命题和关系,点击进入设定库原详情。',
      detailHint: '用于核对本章设定闭环；点击条目会跳到既有三栏设定详情。',
      empty: '本章暂无设定条目', icon: BookOpen, items: codexRows, countTone: codexRows.length ? 'text-brand' : 'text-faint', tone: 'brand',
    },
    {
      key: 'materials', label: '本章素材', title: '本章素材',
      description: '本章引用或召回过的素材库材料,点击进入素材详情。',
      detailHint: '用于追溯本章来源和参考,不替代素材库自身能力。',
      empty: '本章暂无素材条目', icon: FileSearch, items: materialRows, countTone: materialRows.length ? 'text-brand' : 'text-faint', tone: 'brand',
    },
    {
      key: 'promise', label: '本章伏笔', title: '本章伏笔',
      description: '本章关联的伏笔、误导和回收账本。',
      detailHint: '点击后进入伏笔详情,用于检查种下、推进和回收是否闭环。',
      empty: '本章暂无伏笔条目', icon: Eye, items: promiseRows, countTone: promiseRows.length ? 'text-brand' : 'text-faint', tone: 'brand',
    },
    {
      key: 'motif', label: '本章母题', title: '本章母题',
      description: '本章出现的母题实例和主题回声。',
      detailHint: '点击后进入母题详情,用于检查意象和主题是否持续。',
      empty: '本章暂无母题条目', icon: Drama, items: motifRows, countTone: motifRows.length ? 'text-ok' : 'text-faint', tone: 'ok',
    },
    {
      key: 'review', label: '本章校验', title: '本章校验',
      description: '本章校验或一致性检查命中的待处理项。',
      detailHint: '点击后进入校验详情,用于定位正文、设定或素材的冲突。',
      empty: '本章暂无校验条目', icon: Lock, items: issueRows, countTone: issueRows.length ? 'text-warn' : 'text-faint', tone: 'warn',
    },
    {
      key: 'write', label: '可写事实', title: '可写事实',
      description: '当前视角已经知道、可以安全进入正文的信息。',
      detailHint: '可从当前 POV 安全写入正文；点击后主编会围绕这条事实展开讨论。',
      empty: '该角色此章暂无可写事实', icon: BookOpen, items: writable, countTone: 'text-ok', tone: 'ok',
    },
    {
      key: 'forbid', label: '禁止泄露', title: '禁止泄露',
      description: '当前 POV 不知道，直接写出会造成限知泄露。',
      detailHint: '这条信息不能从当前 POV 直接写出。可以改成感官误读、他人暗示或延后揭露。',
      empty: '暂无禁写风险', icon: Lock, items: forbidden, countTone: forbidden.length ? 'text-danger' : 'text-faint', tone: 'danger',
    },
    {
      key: 'irony', label: '戏剧反讽', title: '戏剧反讽',
      description: '读者知道、当前 POV 不知道，适合制造悬念和误判。',
      detailHint: '可让角色说出与事实相反的判断，或把读者知道的信息压进动作和环境。',
      empty: '暂无戏剧反讽', icon: Drama, items: ironyRows, countTone: ironyRows.length ? 'text-brand' : 'text-faint', tone: 'brand',
    },
    {
      key: 'blind', label: '误判盲区', title: '误判盲区',
      description: '当前 POV 的合理误判或自我保护性解释。',
      detailHint: '盲区要能成立,后续被事实推翻时才有力量。',
      empty: '暂无误判盲区', icon: Eye, items: [], countTone: 'text-faint', tone: 'warn',
    },
    {
      key: 'source', label: '来源账本', title: '来源账本',
      description: '把知识帧和反讽来源合并成一张账，方便追溯信息从哪里来。',
      detailHint: '来源账本用于回查事实归属；需要进入设定或素材详情时，可先聚焦给主编接手。',
      empty: '暂无来源账本', icon: FileSearch, items: sourceRows, countTone: 'text-ink', tone: 'source',
    },
  ]
  const activeSection = sections.find((s) => s.key === active) || sections[0]
  const pickedSection = picked ? (sections.find((s) => s.key === picked.sectionKey) || activeSection) : activeSection
  const focalizerName = focalizerLabel(effectiveFocalizer, options)
  const detailModel = picked ? {
    kind: 'fact',
    title: factTitle(picked.fact),
    kicker: `${picked.fact.targetNode ? '章级关联' : '限知帧'} · ${pickedSection.label}`,
    sub: picked.fact.targetNode ? pickedSection.detailHint : (picked.fact.value == null ? '当前 POV 不知道；只能写痕迹、误读或延后揭露。' : `当前值:${factValue(picked.fact)}`),
    value: factValue(picked.fact),
    body: factRows(pickedSection, picked.fact),
    related: relatedRows(pickedSection, picked.fact),
  } : {
    kind: 'group',
    title: `${pickedSection.title}总览`,
    kicker: `关联分类 · ${focalizerName}`,
    sub: `${pickedSection.description} · ${pickedSection.items.length}项`,
    body: groupRows(pickedSection, focalizerName),
    related: pickedSection.items.length ? pickedSection.items.slice(0, 4).map((f) => [pickedSection.label, factTitle(f)]) : [['本章', `第 ${chapter} 章`]],
  }
  const detailPath = `第 ${chapter} 章 / ${focalizerName} / ${pickedSection.label}${picked ? ' / ' + factTitle(picked.fact) : ''}`
  const summaryStats = [
    ['设定', codexRows.length, codexRows.length ? 'brand' : 'muted'],
    ['素材', materialRows.length, materialRows.length ? 'brand' : 'muted'],
    ['可写', writable.length, 'ok'],
    ['禁写', forbidden.length, forbidden.length ? 'danger' : 'muted'],
    ['反讽', ironyRows.length, ironyRows.length ? 'brand' : 'muted'],
    ['风险', forbidden.length, forbidden.length ? 'danger' : 'muted'],
  ]

  const pickSection = (key) => {
    setActive(key)
    setPicked(null)
    setFullOpen(false)
  }
  const pickFact = (sectionKey, fact) => {
    const section = sections.find((s) => s.key === sectionKey) || activeSection
    setActive(sectionKey)
    setPicked({ sectionKey, fact })
    setFullOpen(false)
    if (fact.targetNode) {
      onSelectNode?.(fact.targetNode)
      setFocus({ type: 'chapter_association', id: fact.id, label: factTitle(fact), payload: { target: fact.targetNode }, origin: 'panel' })
      return
    }
    setFocus(factFocus(fact, sectionKey === 'irony' || fact.sourceKind === '戏剧反讽'))
  }

  const renderGroupButtons = () => sections.map((section) => {
    const Icon = section.icon
    const on = active === section.key
    return (
      <button key={section.key} type="button" aria-label={`${section.label} ${section.items.length}`} onClick={() => pickSection(section.key)}
        className={`relative w-full rounded-lg border border-transparent border-l-4 ${toneBorder(section.tone)} bg-surface px-3 py-2 text-left transition-colors cursor-pointer ${on ? 'border-line bg-brand/10 shadow-sm after:absolute after:right-[-13px] after:top-1/2 after:w-3 after:border-t after:border-brand/40' : 'hover:border-line hover:bg-soft/70'}`}>
        <div className="text-f11 text-faint">{section.description}</div>
        <div className="mt-1 flex min-w-0 items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-2 text-f13 font-semibold text-ink"><Icon size={14} className={on ? 'text-brand' : 'text-faint'} />{section.label}</span>
          <span className={`text-f12 tnum ${section.countTone}`}>{section.items.length}</span>
        </div>
      </button>
    )
  })

  const renderItemButtons = (compact = false) => (
    activeSection.items.length === 0 ? (
      <Empty>{activeSection.empty}</Empty>
    ) : (
      <div className="grid gap-1.5">
        {activeSection.items.map((f) => (
          <FactButton
            key={`${activeSection.key}:${f.sourceKind || ''}:${f.id}`}
            fact={f}
            icon={activeSection.icon}
            active={picked?.sectionKey === activeSection.key && picked?.fact?.id === f.id}
            onPick={() => pickFact(activeSection.key, f)}
          />
        ))}
        {compact && !picked && <DetailArticle model={detailModel} compact onFull={() => setFullOpen(true)} />}
      </div>
    )
  )

  const renderWideBoard = () => (
    <div className="min-w-[720px] grid grid-cols-[minmax(12rem,0.8fr)_minmax(14rem,0.95fr)_minmax(17rem,1.15fr)] items-start gap-4">
      <section className="min-w-0">
        <div className="mb-2 flex h-6 items-center justify-between px-0.5 text-f11 tracking-wide text-faint">
          <span>分组</span><span>{sections.length}类</span>
        </div>
        <div className="grid gap-1.5">{renderGroupButtons()}</div>
      </section>
      <section className="min-w-0">
        <div className="mb-2 flex h-6 items-center justify-between px-0.5 text-f11 tracking-wide text-faint">
          <span>当前分类</span><span>{activeSection.items.length}项</span>
        </div>
        <div className="grid gap-1.5">{renderItemButtons(false)}</div>
      </section>
      <section aria-label="关联详情" className="min-w-0">
        <div className="mb-2 flex h-6 items-center justify-between px-0.5 text-f11 tracking-wide text-faint">
          <span>就地详情</span><span>随路径更新</span>
        </div>
        <DetailArticle model={detailModel} onFull={() => setFullOpen(true)} />
      </section>
    </div>
  )

  const renderDownBoard = () => (
    <div className="max-w-[62rem] grid gap-2">
      {sections.map((section) => {
        const Icon = section.icon
        const expanded = active === section.key
        return (
          <section key={section.key} className="grid gap-1.5">
            <button type="button" aria-label={`${section.label} ${section.items.length}`} onClick={() => pickSection(section.key)}
              className={`w-full rounded-lg border border-transparent border-l-4 ${toneBorder(section.tone)} bg-surface px-3 py-2 text-left transition-colors cursor-pointer ${expanded ? 'border-line bg-brand/10 shadow-sm' : 'hover:border-line hover:bg-soft/70'}`}>
              <div className="flex min-w-0 items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2 text-f13 font-semibold text-ink"><Icon size={14} className={expanded ? 'text-brand' : 'text-faint'} />{section.label}</span>
                <span className={`text-f12 tnum ${section.countTone}`}>{section.items.length}</span>
              </div>
              <div className="mt-0.5 text-f11 text-faint">{section.description}</div>
            </button>
            {expanded && (
              <div className="ml-6 grid gap-1.5">
                {renderItemButtons(true)}
                {picked && <DetailArticle model={detailModel} compact onFull={() => setFullOpen(true)} />}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )

  return (
    <div className="h-full min-h-0 flex flex-col bg-canvas">
      <div className="shrink-0 border-b border-line/70 bg-surface/70 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Eye size={17} className="text-brand" />
            <div>
              <div className="text-f20 font-semibold leading-tight text-ink">第 {chapter} 章关联树</div>
              <div className="text-f12 text-faint">把设定、素材、伏笔、母题、校验和限知边界放在同一条章级路径上。</div>
            </div>
          </div>
          {options.length > 1 ? (
            <label className="flex h-9 items-center gap-2 rounded-lg border border-line bg-surface px-2 text-f12 text-faint">
              <span>视角</span>
              <select
                aria-label="限知视角"
                value={effectiveFocalizer}
                onChange={(e) => { setActiveFocalizer(e.target.value); setActive('write'); setPicked(null); setFullOpen(false) }}
                className="h-7 border-0 bg-transparent px-1 text-f12 text-ink outline-none"
              >
                {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
          ) : (
            <div className="rounded-md bg-soft px-2 py-1 text-f12 text-faint">视角 · {focalizerName}</div>
          )}
        </div>
      </div>
      <div className="grid shrink-0 grid-cols-3 border-b border-line/70 bg-line/40 md:grid-cols-6">
        {summaryStats.map(([label, value, tone]) => (
          <div key={label} className="min-w-0 bg-surface/80 px-4 py-2">
            <div className="text-f11 text-faint">{label}</div>
            <div className={`text-f20 font-semibold leading-tight tnum ${toneText(tone)}`}>{value}</div>
          </div>
        ))}
      </div>

      {!effectiveFocalizer ? (
        <Empty>作者全知视角——暂无限知约束</Empty>
      ) : fullOpen ? (
        <FullDetail model={detailModel} path={detailPath} onBack={() => setFullOpen(false)} />
      ) : (
        <section aria-label="关联画布" className="tree-shell flex-1 min-h-0 grid grid-rows-[auto_minmax(0,1fr)]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/70 bg-surface px-4 py-2">
            <div className="min-w-0 truncate text-f12 text-faint">
              <span>第 {chapter} 章</span><span className="mx-2">/</span><span>{focalizerName}</span><span className="mx-2">/</span><span className="font-medium text-ink">{pickedSection.label}</span>{picked && <><span className="mx-2">/</span><span className="font-medium text-ink">{factTitle(picked.fact)}</span></>}
            </div>
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-lg bg-soft p-0.5">
                {[
                  ['wide', '向右延展'],
                  ['down', '向下压缩'],
                ].map(([key, label]) => (
                  <button key={key} type="button" onClick={() => setOrientation(key)}
                    className={`h-7 rounded-md px-2.5 text-f12 ${orientation === key ? 'bg-surface text-brand shadow-sm' : 'text-faint hover:text-ink'}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="min-h-0 overflow-auto px-4 py-4">
            <nav aria-label="关联上下文树">
              {orientation === 'wide' ? renderWideBoard() : renderDownBoard()}
            </nav>
          </div>
        </section>
      )}
    </div>
  )
}
