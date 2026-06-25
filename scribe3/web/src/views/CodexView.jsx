import { useEffect, useState, useRef } from 'react'
import { Users, Boxes, Bookmark, Flame, Search, Lock, Plus, Trash2, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, ArrowLeft, Check } from 'lucide-react'
import { api } from '../api'
import { Btn, Tag } from '../ui'

const TABS = [
  { key: 'overview', label: '概览', icon: PieChart },
  { key: 'chars', label: '角色', icon: Users },
  { key: 'facts', label: '设定·命题', icon: Boxes },
  { key: 'rules', label: '世界规则', icon: Shield },
  { key: 'factions', label: '势力', icon: Swords },
  { key: 'items', label: '物品', icon: MapPin },
  { key: 'terms', label: '术语', icon: Tags },
  { key: 'promises', label: '伏笔', icon: Bookmark },
  { key: 'motifs', label: '母题', icon: Flame },
  { key: 'timeline', label: '弧光', icon: GitBranch },
  { key: 'relations', label: '关系', icon: Heart },
]

const localOf = (row) => (row.id || '').includes(':') ? row.id.split(':').slice(1).join(':') : (row.id || row.name || '')

// ─── EditableField: Notion 式始终可编辑字段 ───
// 点击值 → 变成 input → 失焦自动保存
function EditableField({ label, value, onSave, area, num, options, placeholder }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')
  const ref = useRef(null)

  useEffect(() => { setVal(value ?? '') }, [value])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])

  const save = () => {
    setEditing(false)
    if (val !== (value ?? '')) onSave(val)
  }

  const display = value || placeholder || '—'

  if (editing) {
    return (
      <div className="flex items-start gap-3 py-1.5">
        <span className="text-[11px] text-faint uppercase tracking-wider min-w-[72px] pt-1.5">{label}</span>
        {area ? (
          <textarea ref={ref} value={val} onChange={(e) => setVal(e.target.value)} onBlur={save} rows={3}
            onKeyDown={(e) => { if (e.key === 'Escape') { setVal(value ?? ''); setEditing(false) } }}
            className="flex-1 rounded-md border border-brand/40 bg-canvas px-2 py-1.5 text-[13px] text-ink outline-none resize-y" />
        ) : options ? (
          <select ref={ref} value={val} onChange={(e) => { setVal(e.target.value); setTimeout(save, 0) }} onBlur={save}
            className="flex-1 h-8 rounded-md border border-brand/40 bg-canvas px-2 text-[13px] text-ink outline-none">
            {options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input ref={ref} type={num ? 'number' : 'text'} value={val} onChange={(e) => setVal(num ? Number(e.target.value) : e.target.value)}
            onBlur={save} onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { setVal(value ?? ''); setEditing(false) } }}
            className="flex-1 h-8 rounded-md border border-brand/40 bg-canvas px-2 text-[13px] text-ink outline-none" />
        )}
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 py-1.5 group/field cursor-text hover:bg-soft/40 rounded-md px-1 -mx-1 transition-colors"
      onClick={() => setEditing(true)}>
      <span className="text-[11px] text-faint uppercase tracking-wider min-w-[72px] pt-0.5">{label}</span>
      <span className={`flex-1 text-[13px] ${value ? 'text-ink' : 'text-faint/50'}`}>{display}</span>
    </div>
  )
}

// ─── EditableTags: 标签列表(点击添加/删除) ───
function EditableTags({ label, tags, onSave }) {
  const [input, setInput] = useState('')
  const add = () => { if (input.trim()) { onSave([...(tags || []), input.trim()]); setInput('') } }
  const remove = (i) => { onSave((tags || []).filter((_, idx) => idx !== i)) }
  return (
    <div className="flex items-start gap-3 py-1.5">
      <span className="text-[11px] text-faint uppercase tracking-wider min-w-[72px] pt-0.5">{label}</span>
      <div className="flex-1 flex flex-wrap items-center gap-1">
        {(tags || []).map((t, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-[12px] text-fore bg-fore/10 px-2 py-0.5 rounded">
            {t}
            <button onClick={() => remove(i)} className="text-faint hover:text-danger cursor-pointer">×</button>
          </span>
        ))}
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') add() }}
          placeholder="添加..." className="w-20 h-6 text-[12px] bg-transparent border-b border-line text-ink outline-none focus:border-brand placeholder:text-faint/50" />
      </div>
    </div>
  )
}

// ─── DetailView: Notion 式详情页(全字段始终可编辑) ───
function DetailView({ type, row, onBack, onUpdate, onDelete }) {
  const save = (key, val) => { onUpdate({ ...row, [key]: val }) }

  if (type === 'chars') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <button onClick={onBack} className="inline-flex items-center gap-1 text-[13px] text-faint hover:text-ink cursor-pointer"><ArrowLeft size={16}/>返回</button>
          <span className="text-[11px] text-faint/50">角色档案</span>
        </div>
        {/* 标题(名字) */}
        <h1 className="text-[24px] font-bold text-ink prose-serif mb-1">{row.name}</h1>
        {row.surface_goal && <div className="text-[14px] text-fore mb-4">{row.surface_goal}</div>}
        <div className="border-t border-line pt-3 space-y-0">
          <EditableField label="名字" value={row.name} onSave={(v) => save('name', v)} />
          <EditableField label="重要度" value={row.importance} options={['protagonist','major','minor','background']} onSave={(v) => save('importance', v)} />
          <EditableField label="外貌" value={row.appearance} area onSave={(v) => save('appearance', v)} />
          <EditableTags label="性格标签" tags={row.personality_tags} onSave={(v) => save('personality_tags', v)} />
          <EditableField label="性格深描" value={row.personality_detail} area onSave={(v) => save('personality_detail', v)} />
          <EditableField label="前史" value={row.backstory} area onSave={(v) => save('backstory', v)} />
          <EditableField label="能力" value={row.abilities} area onSave={(v) => save('abilities', v)} />
          <EditableTags label="弱点" tags={row.weaknesses} onSave={(v) => save('weaknesses', v)} />
          <div className="border-t border-line/60 mt-2 pt-2">
            <div className="text-[11px] text-faint uppercase tracking-wider mb-1">动机与冲突</div>
            <EditableField label="表面目标" value={row.surface_goal} onSave={(v) => save('surface_goal', v)} />
            <EditableField label="深层需求" value={row.deep_need} onSave={(v) => save('deep_need', v)} />
            <EditableField label="内在冲突" value={row.internal_conflict} onSave={(v) => save('internal_conflict', v)} />
            <EditableField label="恐惧" value={row.fear} onSave={(v) => save('fear', v)} />
            <EditableField label="首次出场" value={row.first_appearance} num onSave={(v) => save('first_appearance', v)} />
          </div>
        </div>
        <div className="mt-4 pt-3 border-t border-line">
          <button onClick={onDelete} className="text-[12px] text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1"><Trash2 size={13}/>删除角色</button>
        </div>
      </div>
    )
  }

  // 通用详情(facts/rules/factions/items/terms/promises/motifs)
  const fieldMap = {
    facts: [['entity','主体'],['attribute','属性'],['value','值',true],['valid_from','生效章',false,true],['secret','私密',false,false,true]],
    rules: [['name','规则名'],['category','类别'],['source','源头'],['cost','代价',true],['note','备注',true]],
    factions: [['name','势力名'],['ideology','意识形态',true],['leader','领袖'],['public_face','公开面目',true],['private_operation','私下运作',true]],
    items: [['name','物品名'],['category','类别'],['description','描述',true],['symbolic_state','状态'],['current_owner','持有者']],
    terms: [['name','术语名'],['category','类别'],['definition','定义',true]],
    promises: [['text','伏笔内容',true],['setup_chapter','埋于',false,true],['promise_kind','类型']],
    motifs: [['name','母题名'],['theme','绑定主题'],['unfolding','隐喻展开',true],['echoes','物质回声',true]],
  }
  const fields = fieldMap[type] || []
  const tabLabel = TABS.find((t) => t.key === type)?.label || type

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={onBack} className="inline-flex items-center gap-1 text-[13px] text-faint hover:text-ink cursor-pointer"><ArrowLeft size={16}/>返回</button>
        <span className="text-[11px] text-faint/50">{tabLabel}</span>
      </div>
      <h1 className="text-[20px] font-semibold text-ink mb-3">{row.name || row.text || row.id || ''}</h1>
      <div className="border-t border-line pt-3 space-y-0">
        {fields.map(([k, label, area, num, bool]) =>
          bool ? (
            <div key={k} className="flex items-start gap-3 py-1.5">
              <span className="text-[11px] text-faint uppercase tracking-wider min-w-[72px] pt-0.5">{label}</span>
              <span className="flex-1 text-[13px] text-ink">{row[k] ? '是' : '否'}</span>
            </div>
          ) : (
            <EditableField key={k} label={label} value={row[k]} area={area} num={num} onSave={(v) => save(k, v)} />
          )
        )}
      </div>
      <div className="mt-4 pt-3 border-t border-line">
        <button onClick={onDelete} className="text-[12px] text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1"><Trash2 size={13}/>删除</button>
      </div>
    </div>
  )
}

// ─── TimelineCard ───
function TimelineCard({ char }) {
  const [states, setStates] = useState(null)
  useEffect(() => {
    api.get(`/char-states?character_id=${encodeURIComponent(char.id)}`).then((r) => r.json()).then(setStates).catch(() => setStates([]))
  }, [char.id])
  if (!states || states.length === 0) return null
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[14px] font-semibold text-ink prose-serif">{char.name}</span>
        <span className="text-[11px] text-faint">{states.length}个弧光点</span>
      </div>
      <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
        {states.map((s, i) => (
          <div key={i} className="relative">
            <div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" />
            <div className="text-[11px] text-faint">第{s.chapter}章</div>
            <div className="text-[13px] text-ink">{s.summary}</div>
            {s.arc_phase && <div className="text-[12px] text-fore mt-0.5">{s.arc_phase}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── 主组件 ───
export function CodexView() {
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState({ chars: [], facts: [], rules: [], factions: [], items: [], terms: [], places: [], promises: [], motifs: [], completeness: null, relations: [] })
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null) // {type, row} → 打开详情页

  const reload = () => {
    api.entities().then((es) => { setData((d) => ({ ...d, chars: es.filter((e) => e.kind === 'character'), places: es.filter((e) => e.kind === 'place') })) })
    api.facts(99999).then((f) => setData((d) => ({ ...d, facts: f })))
    api.get('/world-rules').then((r) => r.json()).then((r) => setData((d) => ({ ...d, rules: r || [] }))).catch(() => {})
    api.get('/factions').then((r) => r.json()).then((r) => setData((d) => ({ ...d, factions: r || [] }))).catch(() => {})
    api.get('/items').then((r) => r.json()).then((r) => setData((d) => ({ ...d, items: r || [] }))).catch(() => {})
    api.get('/terms').then((r) => r.json()).then((r) => setData((d) => ({ ...d, terms: r || [] }))).catch(() => {})
    api.get('/setting-completeness').then((r) => r.json()).then((r) => setData((d) => ({ ...d, completeness: r }))).catch(() => {})
    api.get('/character-relations?chapter=9999').then((r) => r.json()).then((r) => setData((d) => ({ ...d, relations: r || [] }))).catch(() => {})
    api.promises().then((p) => setData((d) => ({ ...d, promises: p })))
    api.motifs().then((m) => setData((d) => ({ ...d, motifs: m })))
  }
  useEffect(() => { reload() }, [])
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setSelected(null) }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  }, [])

  const f = (s) => !q.trim() || (s || '').includes(q.trim())
  const Th = ({ children, w }) => <th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase tracking-wider" style={{ width: w }}>{children}</th>
  const rowCls = 'group border-b border-line/60 hover:bg-brand/[0.04] transition-colors cursor-pointer'

  const updateRow = async (type, updated) => {
    if (type === 'chars') await api.editChar(localOf(updated), updated)
    else if (type === 'facts') await api.editFact(localOf(updated), updated)
    else if (type === 'rules') await api.post('/world-rules', updated)
    else if (type === 'factions') await api.post('/factions', updated)
    else if (type === 'items') await api.post('/items', updated)
    else if (type === 'terms') await api.post('/terms', updated)
    else if (type === 'promises') await api.editPromise(updated.id, updated)
    else if (type === 'motifs') await api.editMotif(updated.id, updated)
    reload()
  }
  const deleteRow = async (type, row) => {
    if (!window.confirm('确认删除?不可撤销。')) return
    if (type === 'chars') await api.delChar(localOf(row))
    else if (type === 'facts') await api.delFact(localOf(row))
    else if (type === 'rules') await api.del(`/world-rules?name=${encodeURIComponent(row.name)}`)
    else if (type === 'factions') await api.del(`/factions?name=${encodeURIComponent(row.name)}`)
    else if (type === 'items') await api.del(`/items?name=${encodeURIComponent(row.name)}`)
    else if (type === 'terms') await api.del(`/terms?name=${encodeURIComponent(row.name)}`)
    else if (type === 'promises') await api.delPromise(row.id)
    else if (type === 'motifs') await api.delMotif(row.id)
    setSelected(null); reload()
  }
  const addNew = (type) => {
    const empty = { name: '', text: '', entity: '', attribute: '', value: '' }
    setSelected({ type, row: empty })
  }

  // ─── 详情页模式 ───
  if (selected) {
    return (
      <div className="h-full flex flex-col bg-canvas">
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="px-6 py-5">
            <DetailView type={selected.type} row={selected.row}
              onBack={() => setSelected(null)}
              onUpdate={(updated) => updateRow(selected.type, updated)}
              onDelete={() => deleteRow(selected.type, selected.row)} />
          </div>
        </div>
      </div>
    )
  }

  // ─── 列表模式 ───
  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-1 px-3">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setSelected(null) }}
            className={`inline-flex items-center gap-1.5 px-3 h-8 rounded-lg text-[13px] transition-colors cursor-pointer ${tab === t.key ? 'bg-soft text-ink font-medium' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <t.icon size={14} />{t.label}{t.key === 'overview' || t.key === 'timeline' || t.key === 'relations' ? '' : <span className="text-faint tnum">{data[t.key]?.length || 0}</span>}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 h-8 rounded-lg border border-line bg-canvas px-2.5 w-48">
            <Search size={14} className="text-faint" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索…" className="flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint/60" />
          </div>
          {['overview','timeline','relations'].indexOf(tab) < 0 && (
            <Btn variant="primary" size="sm" onClick={() => addNew(tab)}><Plus size={14} />新建</Btn>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">

          {/* 概览 */}
          {tab === 'overview' && data.completeness && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-[28px] font-bold text-ink">{data.completeness.completeness_score}</span>
                <span className="text-[14px] text-faint">设定完整度 / 100</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[['角色', data.completeness.total_chars, Users], ['世界规则', data.completeness.total_rules, Shield],
                  ['势力', data.completeness.total_factions, Swords], ['地点', data.completeness.total_places, MapPin],
                  ['事实/命题', data.completeness.total_facts, Boxes], ['物品', data.items?.length || 0, MapPin],
                  ['术语', data.terms?.length || 0, Tags], ['伏笔', data.promises?.length || 0, Bookmark],
                  ['母题', data.motifs?.length || 0, Flame],
                ].map(([label, count, Icon]) => (
                  <div key={label} className="rounded-xl border border-line bg-surface p-3">
                    <div className="flex items-center gap-2 text-[12px] text-faint mb-1"><Icon size={14}/>{label}</div>
                    <div className="text-[20px] font-semibold text-ink">{count}</div>
                  </div>
                ))}
              </div>
              {data.completeness.missing_dimensions?.length > 0 && (
                <div className="rounded-xl border border-danger/30 bg-danger/5 p-3">
                  <div className="text-[13px] text-danger font-medium mb-1">缺失维度</div>
                  <ul className="text-[12px] text-faint space-y-0.5">{data.completeness.missing_dimensions.map((m, i) => <li key={i}>· {m}</li>)}</ul>
                </div>
              )}
              {data.completeness.char_issues?.length > 0 && (
                <div className="rounded-xl border border-line bg-surface p-3">
                  <div className="text-[13px] text-ink font-medium mb-1">角色问题</div>
                  <div className="text-[12px] text-faint space-y-0.5">{data.completeness.char_issues.map((c, i) => <div key={i}>{c.name}: {c.issues.join(', ')}</div>)}</div>
                </div>
              )}
            </div>
          )}

          {/* 角色卡片列表 */}
          {tab === 'chars' && (
            <div className="space-y-3">
              {data.chars.filter((c) => f(c.name)).map((c) => (
                <div key={c.id} className="rounded-2xl border border-line bg-surface p-4 group cursor-pointer hover:border-brand/30 transition-colors"
                  onClick={() => setSelected({ type: 'chars', row: c })}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[16px] font-semibold text-ink prose-serif">{c.name}</span>
                        {c.importance && <Tag tone={c.importance === 'protagonist' ? 'fore' : c.importance === 'major' ? 'fore' : 'faint'}>{c.importance}</Tag>}
                      </div>
                      {c.surface_goal && <div className="text-[13px] text-fore mt-0.5">{c.surface_goal}</div>}
                    </div>
                  </div>
                  {c.appearance && <div className="text-[12px] text-faint mb-1 line-clamp-1">{c.appearance}</div>}
                  {c.personality_tags?.length > 0 && <div className="flex items-center gap-1 flex-wrap">{c.personality_tags.slice(0,4).map((t) => <Tag key={t} tone="fore">{t}</Tag>)}</div>}
                </div>
              ))}
            </div>
          )}

          {/* 通用表格(点击行打开详情) */}
          {['facts','rules','factions','items','terms','promises','motifs'].includes(tab) && (
            <table className="w-full text-[13px] border-collapse">
              <thead><tr>
                {tab === 'facts' && <><Th w="20%">主体</Th><Th w="18%">属性</Th><Th>值</Th><Th w="8%">私密</Th></>}
                {tab === 'rules' && <><Th w="22%">规则</Th><Th w="14%">类别</Th><Th>代价</Th></>}
                {tab === 'factions' && <><Th w="20%">势力</Th><Th w="24%">意识形态</Th><Th>领袖</Th></>}
                {tab === 'items' && <><Th w="18%">物品</Th><Th w="14%">类别</Th><Th w="16%">状态</Th><Th>描述</Th></>}
                {tab === 'terms' && <><Th w="18%">术语</Th><Th w="14%">类别</Th><Th>定义</Th></>}
                {tab === 'promises' && <><Th>伏笔</Th><Th w="12%">埋于</Th><Th w="14%">状态</Th></>}
                {tab === 'motifs' && <><Th w="20%">母题</Th><Th w="28%">绑定主题</Th><Th>隐喻展开</Th></>}
              </tr></thead>
              <tbody>
                {(data[tab] || []).filter((x) => f(x.value) || f(x.attribute) || f(x.text) || f(x.name) || f(x.category)).map((x) => (
                  <tr key={x.id || x.name} className={rowCls} onClick={() => setSelected({ type: tab, row: x })}>
                    {tab === 'facts' && <><td className="px-3 py-2.5 text-faint">{x.entity}</td><td className="px-3 py-2.5 text-ink">{x.attribute}</td><td className="px-3 py-2.5 text-ink">{x.value}</td><td className="px-3 py-2.5">{x.secret && <Lock size={13} className="text-secret" />}</td></>}
                    {tab === 'rules' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5"><Tag tone="fore">{x.category}</Tag></td><td className="px-3 py-2.5 text-faint">{x.cost || '—'}</td></>}
                    {tab === 'factions' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.ideology || '—'}</td><td className="px-3 py-2.5 text-ink">{x.leader || '—'}</td></>}
                    {tab === 'items' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.category || '—'}</td><td className="px-3 py-2.5"><Tag tone={x.symbolic_state==='active'?'ok':x.symbolic_state==='lost'?'fore':'faint'}>{x.symbolic_state}</Tag></td><td className="px-3 py-2.5 text-faint">{(x.description || '—').slice(0,40)}</td></>}
                    {tab === 'terms' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.category || '—'}</td><td className="px-3 py-2.5 text-faint">{x.definition || '—'}</td></>}
                    {tab === 'promises' && <><td className="px-3 py-2.5 text-ink">{x.text}</td><td className="px-3 py-2.5 text-faint tnum">第{x.setup_chapter}章</td><td className="px-3 py-2.5">{x.status === 'open' ? <Tag tone="fore">未回收</Tag> : <Tag tone="ok">已回收</Tag>}</td></>}
                    {tab === 'motifs' && <><td className="px-3 py-2.5 font-medium text-ink prose-serif text-[14px]">{x.name}</td><td className="px-3 py-2.5 text-fore">{x.theme}</td><td className="px-3 py-2.5 text-faint">{x.unfolding}</td></>}
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* 弧光 */}
          {tab === 'timeline' && <div className="space-y-4">{data.chars.filter((c) => f(c.name)).map((c) => <TimelineCard key={c.id} char={c} />)}</div>}

          {/* 关系 */}
          {tab === 'relations' && (
            <div className="space-y-3">
              {data.relations.length === 0 && <div className="text-[13px] text-faint p-4">无关系数据</div>}
              {(data.relations || []).map((r, i) => (
                <div key={i} className="rounded-xl border border-line bg-surface p-3 flex items-center gap-4">
                  <span className="text-[14px] font-medium text-ink prose-serif min-w-[80px]">{r.src?.split(':').pop() || r.src}</span>
                  <span className="flex-1 text-center"><Tag tone={['盟友','同门','熟人','夫妻'].includes(r.relation) ? 'ok' : ['利益对立','仇敌'].includes(r.relation) ? 'fore' : 'faint'}>{r.relation}</Tag></span>
                  <span className="text-[14px] font-medium text-ink prose-serif min-w-[80px] text-right">{r.dst?.split(':').pop() || r.dst}</span>
                  <span className="text-[11px] text-faint">第{r.since_chapter}章</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
