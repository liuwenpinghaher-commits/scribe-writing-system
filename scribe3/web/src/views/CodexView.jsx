import { useEffect, useState, useRef } from 'react'
import { Users, Boxes, Bookmark, Flame, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, ArrowLeft, Trash2 } from 'lucide-react'
import { api } from '../api'
import { Tag } from '../ui'

// 注:本文件仅导出 DetailView(被 CodexNew/CodexDetail 复用)。
// 原内置主组件 CodexView 及其专属子件(TimelineCard 弧光请求瀑布/EditorChat/UnverifiedPanel)
// 已无人 import,属死代码,已删除。活的弧光视图在 views/TimelineView(vis-timeline,批量拉取)。

// 后端对勾选私密的字段,GET(未 reveal)时把真值替换为此掩码占位符(app.py `_mask_field`,
// 常量语义 _SECRET_MASK)。若编辑其他字段时整行回传,该占位符会被写回、把真实私密值永久覆盖
// (codex 无版本史,不可恢复)——彻查 F-1/F-2。因此提交前必须把「值恰等于该占位符」的字段从
// payload 剔除:不发送 = 后端 PATCH 路径保留原值。前端硬编码,须与后端 `🔒 私密` 同源。
export const SECRET_MASK = '🔒 私密'
export const stripSecretMask = (obj) =>
  Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== SECRET_MASK))

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

// ═══ Field 组件(上下布局,label在上,全宽) ═══
function Field({ label, value, onSave, type = 'text', options, placeholder, section }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')
  const ref = useRef(null)
  // tags 类用 options 判空(value 恒为 undefined,否则已填标签永不显示、永远只见「+添加」)
  const isEmpty = type === 'tags' ? !(options && options.length) : !value

  useEffect(() => { if (!editing) setVal(value ?? '') }, [value, editing])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])

  const commit = () => { setEditing(false); const fv = type === 'number' ? (val === '' ? null : Number(val)) : val; if (fv !== (value ?? '')) onSave(fv) }
  const cancel = () => { setVal(value ?? ''); setEditing(false) }
  const inputBase = 'w-full rounded-md border border-brand/40 bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none focus:border-brand'

  if (isEmpty && !editing) {
    return (<div className={`py-1.5 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <button onClick={() => setEditing(true)} className="text-f12 text-faint/40 hover:text-brand cursor-pointer transition-colors duration-150">+ 添加{label}</button>
    </div>)
  }
  if (type === 'tags') return <TagsRow label={label} tags={options} onSave={onSave} section={section} />
  if (type === 'abilities') return <AbilitiesRow value={value} onSave={onSave} section={section} />

  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div>
      {editing ? (
        <div onClick={(e) => e.stopPropagation()}>
          {type === 'textarea' ? (
            <textarea ref={ref} value={val} onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Escape') cancel() }} rows={4}
              placeholder={placeholder || `输入${label}...`} className={inputBase + ' resize-y'} />
          ) : type === 'select' ? (
            <select ref={ref} value={val ?? ''} onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Escape') cancel() }} className={inputBase + ' h-9 cursor-pointer'}>
              <option value="">—</option>{(options || []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input ref={ref} type={type === 'number' ? 'number' : 'text'} value={val}
              onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') cancel() }}
              placeholder={placeholder || `输入${label}...`} className={inputBase + ' h-9'} />
          )}
          <div className="text-f10 text-faint/50 mt-0.5">失焦自动保存 · ESC 取消</div>
        </div>
      ) : (
        <div className="text-f13 text-ink leading-relaxed cursor-text hover:bg-soft/30 rounded-md px-2 py-1.5 -mx-1 transition-colors duration-150 whitespace-pre-wrap"
          onClick={() => setEditing(true)}>{value || placeholder || '—'}</div>
      )}
    </div>
  )
}

// ═══ TagsRow ═══
function TagsRow({ label, tags, onSave, section }) {
  const [editing, setEditing] = useState(false)
  const [input, setInput] = useState('')
  const inputRef = useRef(null)
  const list = tags || []
  useEffect(() => { if (editing && inputRef.current) inputRef.current.focus() }, [editing])
  const add = () => { if (input.trim()) { onSave([...list, input.trim()]); setInput('') } }
  const remove = (i) => { onSave(list.filter((_, idx) => idx !== i)) }
  const exitIfEmpty = () => { if (!input.trim()) setEditing(false) }

  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div>
      <div className="flex flex-wrap items-center gap-1" onClick={(e) => editing && e.stopPropagation()}>
        {list.map((t, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-f12 text-fore bg-fore/10 px-2 py-0.5 rounded">
            {t}{editing && <button onClick={() => remove(i)} className="text-faint hover:text-danger cursor-pointer ml-0.5">×</button>}
          </span>
        ))}
        {editing ? (
          <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() }; if (e.key === 'Escape') setEditing(false) }}
            onBlur={exitIfEmpty} placeholder="回车添加..." className="w-28 h-6 text-f12 bg-transparent border-b border-brand/40 text-ink outline-none placeholder:text-faint/40" />
        ) : (
          <button onClick={() => setEditing(true)} className="text-f12 text-faint/40 hover:text-brand cursor-pointer">{list.length === 0 ? '+ 添加' : '+'}</button>
        )}
      </div>
    </div>
  )
}

// ═══ AbilitiesRow ═══
function AbilitiesRow({ value, onSave, section }) {
  const parse = () => { if (!value) return []; try { return typeof value === 'string' ? JSON.parse(value) : value } catch { return [] } }
  const [abilities, setAbilities] = useState(parse)
  const [editingIdx, setEditingIdx] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ name: '', level: '', description: '', acquired_chapter: '' })
  useEffect(() => { setAbilities(parse()) }, [value])
  const commitAll = (nl) => { setAbilities(nl); onSave(JSON.stringify(nl)) }
  const saveForm = () => { if (!form.name) return; const nl = adding ? [...abilities, form] : abilities.map((a, i) => i === editingIdx ? form : a); commitAll(nl); setEditingIdx(null); setAdding(false); setForm({ name: '', level: '', description: '', acquired_chapter: '' }) }
  const remove = (i) => { commitAll(abilities.filter((_, idx) => idx !== i)) }
  const formEl = (
    <div className="p-2.5 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-1.5">
      <div className="flex gap-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="能力名称" autoFocus onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="flex-1 h-7 rounded border border-line bg-canvas px-2 text-f12 text-ink outline-none" />
        <input value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })} placeholder="等级" onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-24 h-7 rounded border border-line bg-canvas px-2 text-f12 text-ink outline-none" />
      </div>
      <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="描述" rows={2} onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-full rounded border border-line bg-canvas px-2 py-1 text-f12 text-ink outline-none resize-y" />
      <div className="flex items-center gap-2">
        <input type="number" value={form.acquired_chapter} onChange={(e) => setForm({ ...form, acquired_chapter: e.target.value })} placeholder="第几章习得" onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-28 h-7 rounded border border-line bg-canvas px-2 text-f12 text-ink outline-none" />
        <button onClick={saveForm} className="px-3 h-7 rounded bg-brand text-brandfg text-f12 cursor-pointer">保存</button>
        <button onClick={() => { setAdding(false); setEditingIdx(null) }} className="px-2 h-7 rounded text-faint text-f12 cursor-pointer">取消</button>
      </div>
    </div>
  )
  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="text-f11 text-faint uppercase tracking-wider mb-1">能力</div>
      <div className="space-y-1.5">
        {abilities.map((ab, i) => (
          <div key={i} className="group">
            {editingIdx === i ? formEl : (
              <div className="flex items-center gap-2 py-1 px-1 rounded hover:bg-soft/40 cursor-text transition-colors duration-150" onClick={() => { setEditingIdx(i); setForm(ab) }}>
                <span className="text-f13 font-medium text-ink">{ab.name}</span>
                <Tag tone={ab.level === '宗师级' || ab.level === '高' ? 'fore' : 'faint'}>{ab.level || '—'}</Tag>
                {ab.acquired_chapter && <span className="text-f10 text-faint">第{ab.acquired_chapter}章</span>}
                {ab.description && <span className="text-f11 text-faint/60 truncate flex-1">{ab.description}</span>}
                <button onClick={(e) => { e.stopPropagation(); remove(i) }} className="opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer text-f11 transition-opacity">删除</button>
              </div>
            )}
          </div>
        ))}
        {adding ? formEl : <button onClick={(e) => { e.stopPropagation(); setAdding(true); setForm({ name: '', level: '', description: '', acquired_chapter: '' }) }} className="text-f11 text-brand hover:text-brand/80 cursor-pointer">+ 添加能力</button>}
        {abilities.length === 0 && !adding && <span className="text-f13 text-faint/40">—</span>}
      </div>
    </div>
  )
}

// ═══ DynamicTimeline ═══
function DynamicTimeline({ characterId }) {
  const [states, setStates] = useState(null)
  const [adding, setAdding] = useState(false)
  const [snapCh, setSnapCh] = useState('')
  const [snapshot, setSnapshot] = useState(null)
  const [form, setForm] = useState({ chapter: '', change_type: 'ability', summary: '', arc_phase: '', trigger_event: '', confidence: 'confirmed', affects_voice: false })
  // after_state snapshot fields
  const [abilityRows, setAbilityRows] = useState([{ k: '', v: '' }])
  const [relationRows, setRelationRows] = useState([{ k: '', v: '' }])
  const [personality, setPersonality] = useState('')
  const resetSnapFields = () => { setAbilityRows([{ k: '', v: '' }]); setRelationRows([{ k: '', v: '' }]); setPersonality('') }
  useEffect(() => { api.get(`/char-states?character_id=${encodeURIComponent(characterId)}`).then(setStates).catch(() => setStates([])) }, [characterId])
  const reload = () => { api.get(`/char-states?character_id=${encodeURIComponent(characterId)}`).then(setStates) }
  const addState = async () => {
    if (!form.chapter || !form.summary) return
    const kv = (rows) => Object.fromEntries(rows.filter((r) => r.k.trim()).map((r) => [r.k.trim(), r.v]))
    const after = {}
    if (['ability', 'composite'].includes(form.change_type)) { const a = kv(abilityRows); if (Object.keys(a).length) after.ability_snapshot = a }
    if (['relation', 'composite'].includes(form.change_type)) { const r = kv(relationRows); if (Object.keys(r).length) after.relation_snapshot = r }
    if (['personality', 'composite'].includes(form.change_type) && personality.trim()) after.personality_snapshot = personality.trim()
    const body = { ...form, character_id: characterId, chapter: Number(form.chapter) }
    if (Object.keys(after).length) body.after_state = after
    await api.post('/char-states', body)
    setAdding(false)
    setForm({ chapter: '', change_type: 'ability', summary: '', arc_phase: '', trigger_event: '', confidence: 'confirmed', affects_voice: false })
    resetSnapFields()
    reload()
  }
  const querySnapshot = async () => { if (!snapCh) return; const data = await api.get(`/char-state-at?character_id=${encodeURIComponent(characterId)}&chapter=${snapCh}`); setSnapshot(data) }
  // helper: update a row field in an array
  const setRow = (setter, idx, field, val) => setter((rows) => rows.map((r, i) => i === idx ? { ...r, [field]: val } : r))
  const addRow = (setter) => setter((rows) => [...rows, { k: '', v: '' }])
  const removeRow = (setter, idx) => setter((rows) => rows.length > 1 ? rows.filter((_, i) => i !== idx) : [{ k: '', v: '' }])
  const inputSm = 'h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none'
  if (!states) return <div className="mt-4 text-f12 text-faint/50">加载中...</div>
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-f11 text-faint uppercase tracking-wider">弧光演进史</span><span className="text-f11 text-faint/50">{states.length}个质变点</span><button onClick={() => setAdding(!adding)} className="ml-auto text-f11 text-brand hover:text-brand/80 cursor-pointer">+ 记录质变</button></div>
      <div className="mb-3 flex items-center gap-2 p-2 rounded-lg bg-soft/30">
        <span className="text-f11 text-faint">查询第</span><input type="number" value={snapCh} onChange={(e) => setSnapCh(e.target.value)} placeholder="章" className="w-16 h-7 rounded border border-line bg-canvas px-1.5 text-f12 text-ink outline-none" />
        <button onClick={querySnapshot} className="px-2 h-7 rounded text-f11 bg-brand/10 text-brand cursor-pointer">查快照</button>
        {snapshot && (<div className="flex-1 text-f11 text-faint space-y-0.5"><div>能力: {Object.keys(snapshot.abilities || {}).length ? JSON.stringify(snapshot.abilities) : '—'}</div><div>关系: {Object.keys(snapshot.relations || {}).length ? JSON.stringify(snapshot.relations) : '—'}</div><div>性格: {snapshot.personality || '—'}</div></div>)}
      </div>
      {adding && (<div className="mb-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2" onClick={(e) => e.stopPropagation()}>
        <div className="flex gap-2"><input type="number" placeholder="第几章" value={form.chapter} onChange={(e) => setForm({ ...form, chapter: e.target.value })} className="w-20 h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none" /><select value={form.change_type} onChange={(e) => setForm({ ...form, change_type: e.target.value })} className="h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none cursor-pointer"><option value="ability">能力变化</option><option value="relation">关系质变</option><option value="personality">性格转折</option><option value="composite">综合</option></select><input placeholder="弧光阶段" value={form.arc_phase} onChange={(e) => setForm({ ...form, arc_phase: e.target.value })} className="flex-1 h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none" /></div>
        <textarea placeholder="发生了什么变化..." value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} rows={2} className="w-full rounded-md border border-line bg-canvas px-2 py-1.5 text-f12 text-ink outline-none resize-y" />
        <div className="flex gap-2 flex-wrap">
          <input placeholder="触发事件" value={form.trigger_event} onChange={(e) => setForm({ ...form, trigger_event: e.target.value })} className={`flex-1 min-w-[120px] ${inputSm}`} />
          <select value={form.confidence} onChange={(e) => setForm({ ...form, confidence: e.target.value })} className={`w-28 ${inputSm} cursor-pointer`}>
            <option value="confirmed">已确认</option>
            <option value="inferred">推断</option>
          </select>
          <label className="flex items-center gap-1.5 text-f12 text-faint cursor-pointer select-none">
            <input type="checkbox" checked={form.affects_voice} onChange={(e) => setForm({ ...form, affects_voice: e.target.checked })} className="w-3.5 h-3.5 accent-brand cursor-pointer" />影响声音
          </label>
        </div>
        {/* 能力快照 */}
        {['ability', 'composite'].includes(form.change_type) && (
          <div className="space-y-1">
            <div className="text-f11 text-faint uppercase tracking-wider">能力快照</div>
            {abilityRows.map((row, idx) => (
              <div key={idx} className="flex gap-1.5 items-center">
                <input value={row.k} onChange={(e) => setRow(setAbilityRows, idx, 'k', e.target.value)} placeholder="能力名" className={`w-24 ${inputSm}`} />
                <input value={row.v} onChange={(e) => setRow(setAbilityRows, idx, 'v', e.target.value)} placeholder="描述" className={`flex-1 ${inputSm}`} />
                <button onClick={() => removeRow(setAbilityRows, idx)} className="text-faint hover:text-danger text-f13 cursor-pointer leading-none">✕</button>
              </div>
            ))}
            <button onClick={() => addRow(setAbilityRows)} className="text-f11 text-brand hover:text-brand/80 cursor-pointer">＋ 添加行</button>
          </div>
        )}
        {/* 关系快照 */}
        {['relation', 'composite'].includes(form.change_type) && (
          <div className="space-y-1">
            <div className="text-f11 text-faint uppercase tracking-wider">关系快照</div>
            {relationRows.map((row, idx) => (
              <div key={idx} className="flex gap-1.5 items-center">
                <input value={row.k} onChange={(e) => setRow(setRelationRows, idx, 'k', e.target.value)} placeholder="对象" className={`w-24 ${inputSm}`} />
                <input value={row.v} onChange={(e) => setRow(setRelationRows, idx, 'v', e.target.value)} placeholder="关系" className={`flex-1 ${inputSm}`} />
                <button onClick={() => removeRow(setRelationRows, idx)} className="text-faint hover:text-danger text-f13 cursor-pointer leading-none">✕</button>
              </div>
            ))}
            <button onClick={() => addRow(setRelationRows)} className="text-f11 text-brand hover:text-brand/80 cursor-pointer">＋ 添加行</button>
          </div>
        )}
        {/* 性格快照 */}
        {['personality', 'composite'].includes(form.change_type) && (
          <div className="space-y-1">
            <div className="text-f11 text-faint uppercase tracking-wider">性格快照</div>
            <input value={personality} onChange={(e) => setPersonality(e.target.value)} placeholder="性格描述..." className={`w-full ${inputSm}`} />
          </div>
        )}
        <div className="flex gap-2"><button onClick={addState} className="px-3 h-7 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">保存</button><button onClick={() => { setAdding(false); resetSnapFields(); setForm({ chapter: '', change_type: 'ability', summary: '', arc_phase: '', trigger_event: '', confidence: 'confirmed', affects_voice: false }) }} className="px-3 h-7 rounded-lg text-faint text-f12 cursor-pointer">取消</button></div>
      </div>)}
      {states.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无弧光记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
          {states.map((s, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" /><div className="flex items-center gap-2 mb-0.5"><span className="text-f11 text-faint font-medium">第{s.chapter}章</span><Tag tone={s.change_type === 'ability' ? 'fore' : s.change_type === 'relation' ? 'ok' : 'faint'}>{s.change_type}</Tag>{s.arc_phase && <span className="text-f11 text-fore">{s.arc_phase}</span>}</div><div className="text-f13 text-ink">{s.summary}</div>{s.trigger_event && <div className="text-f11 text-faint/60 mt-0.5">触发: {s.trigger_event}</div>}</div>))}
        </div>
      )}
    </div>
  )
}

// ═══ DynamicRelations ═══
function DynamicRelations({ characterId }) {
  const [relations, setRelations] = useState(null)
  useEffect(() => { api.get('/character-relations?chapter=9999').then((all) => { setRelations((all || []).filter((r) => r.src === characterId || r.dst === characterId)) }).catch(() => setRelations([])) }, [characterId])
  if (!relations) return null
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-f11 text-faint uppercase tracking-wider">角色关系</span><span className="text-f11 text-faint/50">{relations.length}条</span></div>
      {relations.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无关系记录。</div> : (
        <div className="space-y-1">{relations.map((r, i) => { const oid = r.src === characterId ? r.dst : r.src; return (<div key={i} className="flex items-center gap-3 py-1 px-2 rounded hover:bg-soft/40 transition-colors duration-150"><span className="text-f14 font-medium text-ink prose-serif min-w-[60px]">{(oid || '').split(':').pop()}</span><Tag tone={['盟友','同门','熟人','夫妻'].includes(r.relation) ? 'ok' : ['利益对立','仇敌'].includes(r.relation) ? 'fore' : 'faint'}>{r.relation}</Tag><span className="text-f11 text-faint">第{r.since_chapter}章建立</span>{r.until_chapter && <span className="text-f11 text-danger">第{r.until_chapter}章结束</span>}</div>) })}</div>
      )}
    </div>
  )
}

// ═══ ItemStateHistory ═══
function ItemStateHistory({ item }) {
  const history = item.state_history || []
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-f11 text-faint uppercase tracking-wider">状态流转</span><span className="text-f11 text-faint/50">当前: {item.symbolic_state}</span></div>
      {history.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无状态变更记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-2">{history.map((h, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full border-2 border-surface" style={{ background: h.state === 'active' ? '#10b981' : h.state === 'lost' ? '#f59e0b' : '#ef4444' }} /><div className="flex items-center gap-2"><Tag tone={h.state === 'active' ? 'ok' : h.state === 'lost' ? 'fore' : 'faint'}>{h.state}</Tag>{h.chapter && <span className="text-f11 text-faint">第{h.chapter}章</span>}</div>{h.note && <div className="text-f12 text-faint mt-0.5">{h.note}</div>}</div>))}</div>
      )}
    </div>
  )
}

// ═══ DetailView ═══
export function DetailView({ type, row, isNew, onBack, onUpdate, onDelete }) {
  // 整行回传前剔除掩码占位符字段:角色(backstory)/势力(private_operation)勾私密后 GET 打码,
  // 编辑任一字段不得把 `🔒 私密` 写回销毁真值(F-1/F-2)。stripSecretMask 只按值匹配,故只影响被打码字段。
  const save = (key, val) => onUpdate(stripSecretMask({ ...row, [key]: val }))
  if (type === 'chars') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
          <span className="text-f11 text-faint/50">{isNew ? '新建角色' : '角色档案'}</span>
        </div>
        <div className="border-t border-line pt-3">
          <Field label="名字" value={row.name} placeholder="输入角色名" onSave={(v) => save('name', v)} />
          <Field label="重要度" value={row.importance} type="select" options={['protagonist','major','minor','background']} onSave={(v) => save('importance', v)} />
          <Field label="外貌" value={row.appearance} type="textarea" placeholder="描述外貌特征" onSave={(v) => save('appearance', v)} />
          <Field label="性格标签" type="tags" options={row.personality_tags} onSave={(v) => save('personality_tags', v)} />
          <Field label="性格深描" value={row.personality_detail} type="textarea" placeholder="深入描述性格" onSave={(v) => save('personality_detail', v)} />
          <Field label="前史" value={row.backstory} type="textarea" placeholder="角色背景故事" onSave={(v) => save('backstory', v)} />
          <div className="py-1.5 flex items-center gap-2">
            <input type="checkbox" id="backstory_secret_cb" checked={!!row.backstory_secret}
              onChange={(e) => save('backstory_secret', e.target.checked)}
              className="w-4 h-4 accent-brand cursor-pointer" />
            <label htmlFor="backstory_secret_cb" className="text-f12 text-faint cursor-pointer select-none">🔒 私密(默认屏蔽前史)</label>
          </div>
          <Field label="能力" type="abilities" value={row.abilities} onSave={(v) => save('abilities', v)} />
          <Field label="弱点" type="tags" options={row.weaknesses} onSave={(v) => save('weaknesses', v)} />
          <Field label="表面目标" value={row.surface_goal} placeholder="角色想要什么" onSave={(v) => save('surface_goal', v)} section />
          <Field label="深层需求" value={row.deep_need} placeholder="角色真正需要什么" onSave={(v) => save('deep_need', v)} />
          <Field label="内在冲突" value={row.internal_conflict} placeholder="目标与需求的矛盾" onSave={(v) => save('internal_conflict', v)} />
          <Field label="恐惧" value={row.fear} placeholder="角色最怕什么" onSave={(v) => save('fear', v)} />
          <Field label="首次出场" value={row.first_appearance} type="number" onSave={(v) => save('first_appearance', v)} />
        </div>
        {!isNew && <DynamicTimeline characterId={row.id} />}
        {!isNew && <DynamicRelations characterId={row.id} />}
        <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除角色</button></div>
      </div>
    )
  }
  const fieldMap = {
    facts: [['entity','主体','text'],['attribute','属性','text'],['value','值','textarea'],['valid_from','生效章','number'],['secret','私密','bool']],
    rules: [['name','规则名','text'],['category','类别','rule_cat'],['source','源头','text'],['cost','代价','textarea'],['scope','作用域','scope'],['established_chapter','确立章节','number'],['limitations','限制条件(逗号分隔)','array_csv'],['exceptions','例外情形(逗号分隔)','array_csv'],['capabilities','赋予能力(逗号分隔)','array_csv'],['note','备注','textarea']],
    factions: [['name','势力名','text'],['ideology','意识形态','textarea'],['leader','领袖','text'],['public_face','公开面目','textarea'],['private_operation','私下运作','textarea'],['known_members','已知成员(逗号分隔)','array_csv'],['private_operation_secret','🔒 私密(私下运作)','secret_flag']],
    items: [['name','物品名','text'],['category','类别','text'],['description','描述','textarea'],['symbolic_state','状态','select'],['current_owner','持有者','text'],['first_chapter','首次出场章','number'],['special_properties','特殊属性(逗号分隔)','array_csv']],
    terms: [['name','术语名','text'],['category','类别','text'],['definition','定义','textarea'],['first_mention_chapter','首次提及章','number']],
    promises: [['text','伏笔内容','textarea'],['setup_chapter','埋于','number'],['tier','兑现层级','tier_sel'],['promise_kind','类型','text']],
    motifs: [['name','母题名','text'],['theme','绑定主题','text'],['unfolding','隐喻展开','textarea'],['echoes','物质回声','textarea']],
  }
  const fields = fieldMap[type] || []
  const tabLabel = TABS.find((t) => t.key === type)?.label || type
  const stateOptions = ['active','lost','destroyed','unknown']
  const scopeOptions = ['global','local']
  const tierOptions = [
    { value: 'chapter', label: '章级（近场 +1~3 章内兑现）' },
    { value: 'arc',     label: '卷级（中程 +5~15 章内兑现）' },
    { value: 'book',    label: '书级（贯穿全书，永不超期）' },
  ]
  const ruleCatOptions = [
    { value: 'magic',      label: '魔法' },
    { value: 'technology', label: '科技' },
    { value: 'social',     label: '社会' },
    { value: 'physical',   label: '物理' },
    { value: 'economic',   label: '经济' },
    { value: 'political',  label: '政治' },
  ]
  // Helper: array ↔ comma-separated string
  const arrToCSV = (v) => Array.isArray(v) ? v.join(', ') : (v || '')
  const csvToArr = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)
  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
        <span className="text-f11 text-faint/50">{isNew ? `新建${tabLabel}` : tabLabel}</span>
      </div>
      <div className="border-t border-line pt-3">
        {fields.map(([k, label, ftype]) =>
          ftype === 'secret_flag' ? (
            <div key={k} className="py-1.5 flex items-center gap-2">
              <input type="checkbox" id={`sf_${k}`} checked={!!row[k]}
                onChange={(e) => save(k, e.target.checked)}
                className="w-4 h-4 accent-brand cursor-pointer" />
              <label htmlFor={`sf_${k}`} className="text-f12 text-faint cursor-pointer select-none">{label}</label>
            </div>
          ) :
          ftype === 'bool' ? (<div key={k} className="py-2"><div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div><div className="text-f13 text-ink">{row[k] ? '是' : '否'}</div></div>) :
          ftype === 'rule_cat' ? (
            <div key={k} className="py-2">
              <div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div>
              <select
                value={row[k] || 'magic'}
                onChange={(e) => save(k, e.target.value)}
                className="w-full rounded-md border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none focus:border-brand h-9 cursor-pointer"
              >
                {ruleCatOptions.map((o) => <option key={o.value} value={o.value}>{o.label}（{o.value}）</option>)}
              </select>
            </div>
          ) :
          ftype === 'scope' ? (
            <div key={k} className="py-2">
              <div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div>
              <select
                value={row[k] || ''}
                onChange={(e) => save(k, e.target.value || null)}
                className="w-full rounded-md border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none focus:border-brand h-9 cursor-pointer"
              >
                <option value="">—</option>
                {scopeOptions.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ) :
          ftype === 'tier_sel' ? (
            // 伏笔兑现层级(B-2):章级近场兑现 / 卷级中程 / 书级贯穿全书(书级永不超期)。
            <div key={k} className="py-2">
              <div className="text-f11 text-faint uppercase tracking-wider mb-1">{label}</div>
              <select
                value={row[k] || 'chapter'}
                onChange={(e) => save(k, e.target.value)}
                className="w-full rounded-md border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none focus:border-brand h-9 cursor-pointer"
              >
                {tierOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          ) :
          ftype === 'array_csv' ? (
            <Field key={k} label={label} value={arrToCSV(row[k])} type="text"
              placeholder="逗号分隔，留空即可"
              onSave={(v) => save(k, v ? csvToArr(v) : [])} />
          ) :
          ftype === 'select' ? <Field key={k} label={label} value={row[k]} type="select" options={stateOptions} onSave={(v) => save(k, v)} /> :
          <Field key={k} label={label} value={row[k]} type={ftype === 'textarea' ? 'textarea' : ftype === 'number' ? 'number' : 'text'} onSave={(v) => save(k, v)} />
        )}
      </div>
      {type === 'items' && !isNew && <ItemStateHistory item={row} />}
      <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除</button></div>
    </div>
  )
}

// 注:原主组件 CodexView（设定库整页:Shell + 左栏分类 + 中区列表/详情 + 右栏 EditorChat/检查）
// 已无人 import（设定库现由项目树 + DetailPane 承载,弧光由 views/TimelineView 承载),整段连同
// 其专属子件已删除。本文件只保留 DetailView 这一被复用的详情卡。
