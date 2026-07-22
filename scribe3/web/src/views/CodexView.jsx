import { useEffect, useState, useRef, useId } from 'react'
import { Users, Boxes, Bookmark, Flame, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, ArrowLeft, Trash2, Plus, Lock, X } from 'lucide-react'
import { api } from '../api'
import { Tag, Input, Textarea } from '../ui'
import { Field as UIField } from '../ui/Field.jsx'
import { showToast } from '../ui/Toast'
import { isChapterNum } from '../lib/utils'

// 注:本文件仅导出 DetailView(被 CodexNew/CodexDetail 复用)。
// 原内置主组件 CodexView 及其专属子件(TimelineCard 弧光请求瀑布/EditorChat/UnverifiedPanel)
// 已无人 import,属死代码,已删除。活的弧光视图在 views/TimelineView(vis-timeline,批量拉取)。

// 后端对勾选私密的字段,GET(未 reveal)时把真值替换为此掩码占位符(app.py `_mask_field`,
// 常量语义 _SECRET_MASK)。若编辑其他字段时整行回传,该占位符会被写回、把真实私密值永久覆盖
// (codex 无版本史,不可恢复)——彻查 F-1/F-2。因此提交前必须把「值恰等于该占位符」的字段从
// payload 剔除:不发送 = 后端 PATCH 路径保留原值。前端硬编码,须与后端 _SECRET_MASK 逐字节同源。
// 注:掩码值含锁形符号(U+1F512 + " 私密"),此处用 \u 转义写字面量——runtime 与后端完全一致,
// 但源码不出现结构性 Emoji(过 PC UI 静态合同);切勿改为普通文本,否则打码值不匹配 → 掩码被写回销毁真值。
export const SECRET_MASK = '\u{1F512} 私密'
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

// 把当前设定对象的补全/更正意图种子到主编对话(禁止表单直填 → 对话审批写)。
export function seedChiefCodexWrite(type, row = {}) {
  const name = row.name || row.text || row.id || type
  const lines = type === 'chars'
    ? [
      `请更新/更正角色「${name}」的档案并写入落库(需我审批):`,
      '可补全或修正:外貌/性格/前史/目标/恐惧/首次出场等。',
      '必须先用只读工具核实,再用 s3_patch_character(或对应写工具)写入。',
      '未获批准不得声称已落库。',
    ]
    : [
      `请根据本书上下文补全/更正设定「${name}」(类型:${type})并提交写入提案供我批准。`,
      '先只读核实当前库内事实,再调用对应 s3_ 写工具;未获批准不得声称已落库。',
    ]
  const text = lines.join('\n')
  try { sessionStorage.setItem('s3.chief.seed', text) } catch { /* */ }
  try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: text })) } catch { /* */ }
  return text
}

function ReadOnlyField({ label, value, section, testId }) {
  const display = Array.isArray(value)
    ? value.join('、')
    : (value == null || value === '' ? null : String(value))
  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`} data-testid={testId || undefined}>
      <div className="text-meta text-faint uppercase tracking-wider mb-1">{label}</div>
      <div className="text-f13 text-ink leading-relaxed whitespace-pre-wrap rounded-lg border border-line bg-surface px-2.5 py-1.5 min-h-[2rem]">
        {display || <span className="text-faint">（空 · 由主编审批写入）</span>}
      </div>
    </div>
  )
}

// ═══ Field 组件(上下布局,label在上,全宽) ═══
// immediate(新建表单):点击编辑模式在空草稿下只渲染「+ 添加」按钮,屏读/键盘用户发现不了字段;
// 直填模式用 ui/Field 建立 label↔控件关联(htmlFor/id + required/aria),每键上抛草稿。
// readOnly:已存在设定只读检视,禁止失焦保存(产品铁律:对话审批写)。
function Field({ label, value, onSave, type = 'text', options, placeholder, section, immediate = false, required = false, description, readOnly = false }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')
  const ref = useRef(null)
  const id = useId()
  // tags 类用 options 判空(value 恒为 undefined,否则已填标签永不显示、永远只见「+添加」)
  const isEmpty = type === 'tags' ? !(options && options.length) : !value

  // immediate 模式显示值完全由本地 val 驱动(外部回灌会把 array_csv 等往返规范化、打断输入)
  useEffect(() => { if (!editing && !immediate) setVal(value ?? '') }, [value, editing, immediate])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])

  if (readOnly) {
    if (type === 'tags') {
      return <ReadOnlyField label={label} value={options} section={section} />
    }
    if (type === 'abilities') {
      let ab = value
      try { if (typeof ab === 'string' && ab.trim()) ab = JSON.parse(ab) } catch { /* */ }
      const text = Array.isArray(ab)
        ? ab.map((a) => (typeof a === 'string' ? a : (a?.name || JSON.stringify(a)))).join('、')
        : (value || '')
      return <ReadOnlyField label={label} value={text} section={section} />
    }
    return <ReadOnlyField label={label} value={value} section={section} />
  }

  if (immediate && type !== 'tags' && type !== 'abilities') {
    const set = (v) => { setVal(v); onSave(type === 'number' ? (v === '' ? null : Number(v)) : v) }
    return (
      <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
        <UIField label={label} required={required} description={description}>
          {type === 'textarea' ? (
            <Textarea rows={3} value={val} onChange={(e) => set(e.target.value)} placeholder={placeholder || `输入${label}...`} />
          ) : type === 'select' ? (
            <select value={val ?? ''} onChange={(e) => set(e.target.value)}
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-f13 text-ink outline-none transition-colors focus:border-brand cursor-pointer">
              <option value="">—</option>{(options || []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <Input type={type === 'number' ? 'number' : 'text'} value={val}
              onChange={(e) => set(e.target.value)} placeholder={placeholder || `输入${label}...`} />
          )}
        </UIField>
      </div>
    )
  }

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
    <div className={`group py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      {editing ? (
        <div onClick={(e) => e.stopPropagation()}>
          {/* label 关联编辑控件(htmlFor/id):点击编辑模式此前 label 只是视觉文本 */}
          <label htmlFor={id} className="block text-meta text-faint uppercase tracking-wider mb-1">{label}</label>
          {/* CX-Task 7:注册表 desc 说明文本(仅编辑态显示,不挤占只读态排版) */}
          {description && <div className="text-meta text-faint/60 mb-1.5">{description}</div>}
          {type === 'textarea' ? (
            <textarea ref={ref} id={id} value={val} onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Escape') cancel() }} rows={4}
              placeholder={placeholder || `输入${label}...`} className={inputBase + ' resize-y'} />
          ) : type === 'select' ? (
            <select ref={ref} id={id} value={val ?? ''} onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Escape') cancel() }} className={inputBase + ' h-9 cursor-pointer'}>
              <option value="">—</option>{(options || []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input ref={ref} id={id} type={type === 'number' ? 'number' : 'text'} value={val}
              onChange={(e) => setVal(e.target.value)} onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') cancel() }}
              placeholder={placeholder || `输入${label}...`} className={inputBase + ' h-9'} />
          )}
          <div className="text-meta text-faint/50 mt-0.5">失焦自动保存 · ESC 取消</div>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-meta text-faint uppercase tracking-wider">{label}</span>
            {/* 明确的进入编辑按钮:值区域 div onClick 键盘不可达,只读语义文本保持不变 */}
            <button type="button" onClick={() => setEditing(true)} aria-label={`编辑${label}`}
              className="text-meta text-brand opacity-0 group-hover:opacity-100 focus-visible:opacity-100 cursor-pointer transition-opacity">编辑</button>
          </div>
          <div className="text-f13 text-ink leading-relaxed cursor-text hover:bg-soft/30 rounded-md px-2 py-1.5 -mx-1 transition-colors duration-150 whitespace-pre-wrap"
            onClick={() => setEditing(true)}>{value || placeholder || '—'}</div>
        </>
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
      <div className="text-meta text-faint uppercase tracking-wider mb-1">{label}</div>
      <div className="flex flex-wrap items-center gap-1" onClick={(e) => editing && e.stopPropagation()}>
        {list.map((t, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-f12 text-fore bg-fore/10 px-2 py-0.5 rounded">
            {t}{editing && <button onClick={() => remove(i)} aria-label={`删除${t}`} className="text-faint hover:text-danger cursor-pointer ml-0.5 inline-flex items-center"><X size={11} /></button>}
          </span>
        ))}
        {editing ? (
          <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} aria-label={`添加${label}`}
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
      <div className="text-meta text-faint uppercase tracking-wider mb-1">能力</div>
      <div className="space-y-1.5">
        {abilities.map((ab, i) => (
          <div key={i} className="group">
            {editingIdx === i ? formEl : (
              <div className="flex items-center gap-2 py-1 px-1 rounded hover:bg-soft/40 cursor-text transition-colors duration-150" onClick={() => { setEditingIdx(i); setForm(ab) }}>
                <span className="text-f13 font-medium text-ink">{ab.name}</span>
                <Tag tone={ab.level === '宗师级' || ab.level === '高' ? 'fore' : 'faint'}>{ab.level || '—'}</Tag>
                {ab.acquired_chapter && <span className="text-meta text-faint">第{ab.acquired_chapter}章</span>}
                {ab.description && <span className="text-meta text-faint/60 truncate flex-1">{ab.description}</span>}
                <button onClick={(e) => { e.stopPropagation(); remove(i) }} className="opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer text-meta transition-opacity">删除</button>
              </div>
            )}
          </div>
        ))}
        {adding ? formEl : <button onClick={(e) => { e.stopPropagation(); setAdding(true); setForm({ name: '', level: '', description: '', acquired_chapter: '' }) }} className="text-meta text-brand hover:text-brand/80 cursor-pointer">+ 添加能力</button>}
        {abilities.length === 0 && !adding && <span className="text-f13 text-faint/40">—</span>}
      </div>
    </div>
  )
}

// ═══ DynamicTimeline ═══
function DynamicTimeline({ characterId, onStateAdded }) {
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
    onStateAdded?.()
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
      <div className="flex items-center gap-2 mb-2"><span className="text-meta text-faint uppercase tracking-wider">弧光演进史</span><span className="text-meta text-faint/50">{states.length}个质变点</span><button onClick={() => setAdding(!adding)} className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer">+ 记录质变</button></div>
      <div className="mb-3 flex items-center gap-2 p-2 rounded-lg bg-soft/30">
        <span className="text-meta text-faint">查询第</span><input type="number" value={snapCh} onChange={(e) => setSnapCh(e.target.value)} placeholder="章" className="w-16 h-7 rounded border border-line bg-canvas px-1.5 text-f12 text-ink outline-none" />
        <button onClick={querySnapshot} className="px-2 h-7 rounded text-meta bg-brand/10 text-brand cursor-pointer">查快照</button>
        {snapshot && (<div className="flex-1 text-meta text-faint space-y-0.5"><div>能力: {Object.keys(snapshot.abilities || {}).length ? JSON.stringify(snapshot.abilities) : '—'}</div><div>关系: {Object.keys(snapshot.relations || {}).length ? JSON.stringify(snapshot.relations) : '—'}</div><div>性格: {snapshot.personality || '—'}</div></div>)}
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
            <div className="text-meta text-faint uppercase tracking-wider">能力快照</div>
            {abilityRows.map((row, idx) => (
              <div key={idx} className="flex gap-1.5 items-center">
                <input value={row.k} onChange={(e) => setRow(setAbilityRows, idx, 'k', e.target.value)} placeholder="能力名" className={`w-24 ${inputSm}`} />
                <input value={row.v} onChange={(e) => setRow(setAbilityRows, idx, 'v', e.target.value)} placeholder="描述" className={`flex-1 ${inputSm}`} />
                <button onClick={() => removeRow(setAbilityRows, idx)} aria-label="删除此行" className="text-faint hover:text-danger cursor-pointer leading-none inline-flex items-center"><X size={13} /></button>
              </div>
            ))}
            <button onClick={() => addRow(setAbilityRows)} className="text-meta text-brand hover:text-brand/80 cursor-pointer">＋ 添加行</button>
          </div>
        )}
        {/* 关系快照 */}
        {['relation', 'composite'].includes(form.change_type) && (
          <div className="space-y-1">
            <div className="text-meta text-faint uppercase tracking-wider">关系快照</div>
            {relationRows.map((row, idx) => (
              <div key={idx} className="flex gap-1.5 items-center">
                <input value={row.k} onChange={(e) => setRow(setRelationRows, idx, 'k', e.target.value)} placeholder="对象" className={`w-24 ${inputSm}`} />
                <input value={row.v} onChange={(e) => setRow(setRelationRows, idx, 'v', e.target.value)} placeholder="关系" className={`flex-1 ${inputSm}`} />
                <button onClick={() => removeRow(setRelationRows, idx)} aria-label="删除此行" className="text-faint hover:text-danger cursor-pointer leading-none inline-flex items-center"><X size={13} /></button>
              </div>
            ))}
            <button onClick={() => addRow(setRelationRows)} className="text-meta text-brand hover:text-brand/80 cursor-pointer">＋ 添加行</button>
          </div>
        )}
        {/* 性格快照 */}
        {['personality', 'composite'].includes(form.change_type) && (
          <div className="space-y-1">
            <div className="text-meta text-faint uppercase tracking-wider">性格快照</div>
            <input value={personality} onChange={(e) => setPersonality(e.target.value)} placeholder="性格描述..." className={`w-full ${inputSm}`} />
          </div>
        )}
        <div className="flex gap-2"><button onClick={addState} className="px-3 h-7 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">保存</button><button onClick={() => { setAdding(false); resetSnapFields(); setForm({ chapter: '', change_type: 'ability', summary: '', arc_phase: '', trigger_event: '', confidence: 'confirmed', affects_voice: false }) }} className="px-3 h-7 rounded-lg text-faint text-f12 cursor-pointer">取消</button></div>
      </div>)}
      {states.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无弧光记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
          {states.map((s, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" /><div className="flex items-center gap-2 mb-0.5"><span className="text-meta text-faint font-medium">第{s.chapter}章</span><Tag tone={s.change_type === 'ability' ? 'fore' : s.change_type === 'relation' ? 'ok' : 'faint'}>{s.change_type}</Tag>{s.arc_phase && <span className="text-meta text-fore">{s.arc_phase}</span>}</div><div className="text-f13 text-ink">{s.summary}</div>{s.trigger_event && <div className="text-meta text-faint/60 mt-0.5">触发: {s.trigger_event}</div>}</div>))}
        </div>
      )}
    </div>
  )
}

// ═══ DynamicRelations(批D 件2:角色关系生产入口)═══
// relations_at 返回【裸 local】src/dst(meta::id),而 characterId 是全 oid(role:名);
// 旧版 `r.src === characterId` 恒不匹配(裸名 ≠ role:名)→ 关系恒空(限知关系图黑洞根因之一)。
// 修:按裸 local 比较展示;建立/演变/结束用全 oid(后端 _split/entity 依赖冒号前缀)。
// relation 受控词表须与 migration 029 的 DB ASSERT 一致(越界值 500)。
// 注意 批D Minor②:后端 ASSERT 只收下列固定词 + 字面量 'custom';任何自由文本自定义词都会 500。
// 故不提供「custom + 自由文本框」(输入真实自定义词必 500),也不留死字面量 'custom'(选它=写入
// 无意义的 'custom' 且显示为 'custom')—— 直接移除 custom 选项,每个下拉项都映射到后端确收的真实关系词。
export const REL_VOCAB = [
  ['亲属', ['父子', '母子', '兄弟', '姐妹', '夫妻', '师徒', '养父子']],
  ['正面', ['知己', '战友', '盟友', '同门', '恩人']],
  ['中性', ['同行', '熟人', '上下级', '雇主雇员']],
  ['对立', ['仇敌', '宿敌', '竞争者', '利益对立']],
  ['复杂', ['爱恨交织', '前恋人', '背叛者']],
]
const REL_TONE = (rel) =>
  ['知己', '战友', '盟友', '同门', '恩人', '夫妻', '师徒', '父子', '母子', '兄弟', '姐妹', '养父子', '同行', '熟人'].includes(rel) ? 'ok'
    : ['仇敌', '宿敌', '竞争者', '利益对立', '背叛者'].includes(rel) ? 'fore' : 'faint'

// 受控词表下拉(optgroup 分组)
function RelSelect({ value, onChange, className }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={`${className} cursor-pointer`}>
      {REL_VOCAB.map(([grp, items]) => (
        <optgroup key={grp} label={grp}>
          {items.map((it) => <option key={it} value={it}>{it}</option>)}
        </optgroup>
      ))}
    </select>
  )
}

function DynamicRelations({ characterId }) {
  const meLocal = String(characterId || '').split(':').pop()
  const [relations, setRelations] = useState(null)
  const [chars, setChars] = useState([])
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ dst: '', relation: '同门', since_chapter: '', note: '' })
  const [actOn, setActOn] = useState(null)   // 当前展开动作面板的行 key
  const [act, setAct] = useState({ mode: '', relation: '同门', chapter: '' })

  const reload = () => api.characterRelations(9999)
    .then((all) => setRelations((all || []).filter((r) => r.src === meLocal || r.dst === meLocal)))
    .catch(() => setRelations([]))
  useEffect(() => { reload() }, [characterId])   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    api.entities()
      .then((es) => setChars((es || []).filter((e) => e.kind === 'character' && e.id !== characterId)))
      .catch(() => setChars([]))
  }, [characterId])

  const submitAdd = async () => {
    // 批D Minor①:建立章须 ≥1(旧 === '' 守卫漏拦 0/负数 → 后端 since_chapter ASSERT >=1 报 500)。
    if (!form.dst || !form.relation || !isChapterNum(form.since_chapter)) { showToast('对象、关系必填,建立章须为 ≥1 的章号', { tone: 'danger' }); return }
    try {
      await api.addCharacterRelation({ src: characterId, dst: form.dst, relation: form.relation, since_chapter: Number(form.since_chapter), note: form.note || null })
      showToast('关系已建立', { tone: 'ok' })
      setAdding(false); setForm({ dst: '', relation: '同门', since_chapter: '', note: '' })
      reload()
    } catch (e) { showToast(e?.body?.detail || e?.message || '建立失败', { tone: 'danger' }) }
  }

  const rowKey = (r) => `${r.src}->${r.dst}`
  const submitAct = async (r) => {
    const srcOid = `role:${r.src}`, dstOid = `role:${r.dst}`
    try {
      if (act.mode === 'evolve') {
        // 批D Minor①:演变章须 ≥1(演变新建关系边,同样撞 since_chapter ASSERT >=1)。
        if (!act.relation || !isChapterNum(act.chapter)) { showToast('新关系必填,演变章须为 ≥1 的章号', { tone: 'danger' }); return }
        await api.evolveRelation({ src: srcOid, dst: dstOid, relation: act.relation, since_chapter: Number(act.chapter) })
        showToast('关系已演变', { tone: 'ok' })
      } else if (act.mode === 'end') {
        // until_chapter 后端无 ASSERT,但章号 1-based,0/负数无意义,一并拦(与建立/演变一致)。
        if (!isChapterNum(act.chapter)) { showToast('结束章须为 ≥1 的章号', { tone: 'danger' }); return }
        await api.endRelation({ src: srcOid, dst: dstOid, until_chapter: Number(act.chapter) })
        showToast('关系已结束', { tone: 'ok' })
      }
      setActOn(null); reload()
    } catch (e) { showToast(e?.body?.detail || e?.message || '操作失败', { tone: 'danger' }) }
  }

  const inp = 'h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand'
  if (!relations) return null
  return (
    <div className="mt-4" data-testid="dynamic-relations">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-meta text-faint uppercase tracking-wider">角色关系</span>
        <span className="text-meta text-faint/50">{relations.length}条</span>
        <button onClick={() => setAdding(!adding)} className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5"><Plus size={12} />建立关系</button>
      </div>

      {adding && (
        <div className="mb-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2" onClick={(e) => e.stopPropagation()}>
          <div className="flex gap-2 flex-wrap">
            <select value={form.dst} onChange={(e) => setForm({ ...form, dst: e.target.value })} className={`min-w-[120px] ${inp} cursor-pointer`}>
              <option value="">选择对象角色…</option>
              {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <RelSelect value={form.relation} onChange={(v) => setForm({ ...form, relation: v })} className={inp} />
            <input type="number" value={form.since_chapter} onChange={(e) => setForm({ ...form, since_chapter: e.target.value })} placeholder="建立章" className={`w-20 ${inp}`} />
          </div>
          <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="备注(可选)" className={`w-full ${inp}`} />
          <div className="flex gap-2">
            <button onClick={submitAdd} className="px-3 h-7 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">保存</button>
            <button onClick={() => setAdding(false)} className="px-3 h-7 rounded-lg text-faint text-f12 cursor-pointer">取消</button>
          </div>
        </div>
      )}

      {relations.length === 0 && !adding ? <div className="text-f12 text-faint/50 py-2">尚无关系记录。</div> : (
        <div className="space-y-1">{relations.map((r) => {
          const otherLocal = r.src === meLocal ? r.dst : r.src
          const dir = r.src === meLocal ? '→' : '←'
          const k = rowKey(r)
          return (
            <div key={k} className="group py-1 px-2 rounded hover:bg-soft/40 transition-colors duration-150">
              <div className="flex items-center gap-3">
                <span className="text-meta text-faint/60 w-3 text-center" title={r.src === meLocal ? '本角色 → 对方' : '对方 → 本角色'}>{dir}</span>
                <span className="text-f14 font-medium text-ink prose-serif min-w-[60px]">{otherLocal}</span>
                <Tag tone={REL_TONE(r.relation)}>{r.relation}</Tag>
                <span className="text-meta text-faint">第{r.since_chapter}章建立</span>
                {r.until_chapter && <span className="text-meta text-danger">第{r.until_chapter}章结束</span>}
                {r.note && <span className="text-meta text-faint/60 truncate">· {r.note}</span>}
                {!r.until_chapter && (
                  <span className="ml-auto opacity-0 group-hover:opacity-100 flex items-center gap-2 transition-opacity">
                    <button onClick={() => { setActOn(k); setAct({ mode: 'evolve', relation: r.relation, chapter: '' }) }} className="text-meta text-brand hover:text-brand/80 cursor-pointer">演变</button>
                    <button onClick={() => { setActOn(k); setAct({ mode: 'end', relation: r.relation, chapter: '' }) }} className="text-meta text-faint hover:text-danger cursor-pointer">结束</button>
                  </span>
                )}
              </div>
              {actOn === k && (
                <div className="mt-1.5 ml-6 p-2 rounded-md border border-brand/30 bg-brand/[0.02] flex items-center gap-2 flex-wrap" onClick={(e) => e.stopPropagation()}>
                  {act.mode === 'evolve' ? (<>
                    <span className="text-meta text-faint">演变为</span>
                    <RelSelect value={act.relation} onChange={(v) => setAct({ ...act, relation: v })} className={inp} />
                    <input type="number" value={act.chapter} onChange={(e) => setAct({ ...act, chapter: e.target.value })} placeholder="第几章" className={`w-20 ${inp}`} />
                  </>) : (<>
                    <span className="text-meta text-faint">结束于第</span>
                    <input type="number" value={act.chapter} onChange={(e) => setAct({ ...act, chapter: e.target.value })} placeholder="章" className={`w-16 ${inp}`} />
                    <span className="text-meta text-faint">章</span>
                  </>)}
                  <button onClick={() => submitAct(r)} className="px-2.5 h-7 rounded-md bg-brand text-brandfg text-meta cursor-pointer">确认</button>
                  <button onClick={() => setActOn(null)} className="px-2 h-7 rounded-md text-faint text-meta cursor-pointer">取消</button>
                </div>
              )}
            </div>
          )
        })}</div>
      )}
    </div>
  )
}

// ═══ ItemStateHistory ═══
function ItemStateHistory({ item }) {
  const history = item.state_history || []
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-meta text-faint uppercase tracking-wider">状态流转</span><span className="text-meta text-faint/50">当前: {item.symbolic_state}</span></div>
      {history.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无状态变更记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-2">{history.map((h, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full border-2 border-surface" style={{ background: h.state === 'active' ? '#10b981' : h.state === 'lost' ? '#f59e0b' : '#ef4444' }} /><div className="flex items-center gap-2"><Tag tone={h.state === 'active' ? 'ok' : h.state === 'lost' ? 'fore' : 'faint'}>{h.state}</Tag>{h.chapter && <span className="text-meta text-faint">第{h.chapter}章</span>}</div>{h.note && <div className="text-f12 text-faint mt-0.5">{h.note}</div>}</div>))}</div>
      )}
    </div>
  )
}

// 受控词表下拉的 label 关联行:isNew 走 ui/Field 统一表单外观,详情保留原 uppercase label(htmlFor 修屏读/键盘不可达)
function SelectRow({ id, label, isNew, value, onChange, children }) {
  const select = (
    <select id={isNew ? undefined : id} value={value} onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none focus:border-brand h-9 cursor-pointer">
      {children}
    </select>
  )
  if (isNew) return <div className="py-2"><UIField label={label}>{select}</UIField></div>
  return (
    <div className="py-2">
      <label htmlFor={id} className="block text-meta text-faint uppercase tracking-wider mb-1">{label}</label>
      {select}
    </div>
  )
}

// ═══ CX-Task 7:势力(faction)元数据驱动渲染 ═══
// 拉 GET /codex-schema/faction 按注册表渲染 28 个字段;拉取失败(网络错误/该 kind 未注册)
// 时 DetailView 回退到下方旧 fieldMap.factions 路径——spec 风险表「前端元数据渲染重写
// CodexView」的缓解措施就是"保留旧 fieldMap 作为 fallback"。仅切 faction 一类,
// character/item/term/world_rule 的渲染路径本次一行不动(阶段2 再迁)。

// 掩码占位符不当真值回填:沿用既有 private_operation/backstory 的处理方式(文件顶
// SECRET_MASK 注释)——掩码字符串仍走 Field 原样显示,真正防回写的是 save() 里的
// stripSecretMask(按值过滤、不认字段名,新 secret 字段自动获得防护,无需在此加分支)。
// 这里只加一枚 Tag 提示"这是打码不是真内容",不改变回填/保存逻辑。
const isMasked = (v) => v === SECRET_MASK

function SecretMaskHint() {
  return <Tag tone="secret">已限知 · 当前为打码占位,非真实内容</Tag>
}

const DEPRECATED_HINT = '已废弃,请分流到 遗产运作/对外操纵/加速手段'

function hasValue(v) {
  if (v == null) return false
  if (Array.isArray(v)) return v.length > 0
  if (typeof v === 'object') return Object.keys(v).length > 0
  return String(v).trim() !== ''
}

// secret_capable 字段的伴生旗标键——唯一派生点,与后端 codex_schema.secret_flag_key 同源
// (前端不 import 后端模块,只能手抄同一条派生规则 `${key}_secret`;两处不一致会导致开关
// 显示与实际掩码字段错位)。
const secretKeyOf = (key) => `${key}_secret`

// ═══ MiniFieldInput:object / array<object> 内部子字段的轻量输入控件 ═══
// 与顶层 Field 组件(点击进入编辑态)不同——嵌套子表单语境下没有"点击编辑"的空间,统一
// 渲染成始终可见的小号输入控件(参照 AbilitiesRow 表单区的既有写法)。只需覆盖
// codex_schema.item_schema 实际用到的子字段类型:text/int/enum/bool/textarea(本注册表
// item_schema 均一层、无 array/object 再嵌套,故不做递归)。
function MiniFieldInput({ field, value, onChange }) {
  const base = 'w-full h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand'
  if (field.type === 'enum') {
    return (
      <select aria-label={field.label} title={field.desc || field.label} value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)} className={`${base} cursor-pointer`}>
        <option value="">{field.label}: —</option>
        {(field.enum || []).map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    )
  }
  if (field.type === 'int') {
    return (
      <input aria-label={field.label} title={field.desc || field.label} type="number" value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        placeholder={field.label} className={base} />
    )
  }
  if (field.type === 'bool') {
    return (
      <label className="flex items-center gap-1.5 text-f12 text-faint cursor-pointer select-none h-8" title={field.desc || field.label}>
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)}
          className="w-3.5 h-3.5 accent-brand cursor-pointer" />{field.label}
      </label>
    )
  }
  if (field.type === 'textarea') {
    return (
      <textarea aria-label={field.label} title={field.desc || field.label} value={value ?? ''}
        onChange={(e) => onChange(e.target.value)} placeholder={field.label} rows={2}
        className="w-full rounded-md border border-line bg-canvas px-2 py-1.5 text-f12 text-ink outline-none focus:border-brand resize-y" />
    )
  }
  return (
    <input aria-label={field.label} title={field.desc || field.label} value={value ?? ''}
      onChange={(e) => onChange(e.target.value)} placeholder={field.label} className={base} />
  )
}

// ═══ ObjectField:object 类型(如 structure)——嵌套字段组,单个对象、无增删行 ═══
function ObjectField({ label, fieldKey, value, itemSchema, onSave }) {
  const obj = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  const setSub = (subKey, subVal) => onSave({ ...obj, [subKey]: subVal })
  return (
    <div className="py-2 mt-3 pt-3 border-t border-line/60" data-testid={`objfield-${fieldKey}`}>
      <div className="text-meta text-faint uppercase tracking-wider mb-1.5">{label}</div>
      <div className="pl-3 border-l-2 border-line/40 grid grid-cols-2 gap-2">
        {(itemSchema || []).map((sf) => (
          <div key={sf.key} className={sf.type === 'textarea' ? 'col-span-2' : ''}>
            <div className="text-meta text-faint/70 mb-0.5">{sf.label}</div>
            <MiniFieldInput field={sf} value={obj[sf.key]} onChange={(v) => setSub(sf.key, v)} />
          </div>
        ))}
      </div>
    </div>
  )
}

// ═══ ArrayObjectField:array<object> 类型——可增删行的子表 ═══
// 交互参照 AbilitiesRow(行内表单增删改)+ ItemStateHistory(时间线式展示)二者结合:
// 折叠态显示摘要行,点击/新建展开成按 item_schema 逐子字段渲染的表单。
function ArrayObjectField({ label, fieldKey, value, itemSchema, onSave }) {
  const rows = Array.isArray(value) ? value : []
  const schema = itemSchema || []
  const emptyRow = () => Object.fromEntries(schema.map((f) => [f.key, f.type === 'bool' ? false : null]))
  const [editingIdx, setEditingIdx] = useState(null)   // number(既有行下标) | 'new' | null
  const [form, setForm] = useState(emptyRow)

  const startAdd = () => { setForm(emptyRow()); setEditingIdx('new') }
  const startEdit = (i) => { setForm({ ...emptyRow(), ...rows[i] }); setEditingIdx(i) }
  const cancel = () => setEditingIdx(null)
  const commit = () => {
    const next = editingIdx === 'new' ? [...rows, form] : rows.map((r, i) => (i === editingIdx ? form : r))
    onSave(next)
    setEditingIdx(null)
  }
  const removeRow = (i) => onSave(rows.filter((_, idx) => idx !== i))
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const summarize = (r) => schema.map((f) => r?.[f.key]).filter((v) => v != null && v !== '')
    .slice(0, 3).join(' · ') || '(空行)'

  const formEl = (
    <div className="p-2.5 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-1.5" data-testid={`${fieldKey}-row-form`}>
      <div className="grid grid-cols-2 gap-1.5">
        {schema.map((f) => (
          <div key={f.key} className={f.type === 'textarea' ? 'col-span-2' : ''}>
            <MiniFieldInput field={f} value={form[f.key]} onChange={(v) => setField(f.key, v)} />
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={commit} className="px-3 h-7 rounded bg-brand text-brandfg text-f12 cursor-pointer">保存</button>
        <button onClick={cancel} className="px-2 h-7 rounded text-faint text-f12 cursor-pointer">取消</button>
      </div>
    </div>
  )

  return (
    <div className="py-2 mt-3 pt-3 border-t border-line/60" data-testid={`arrfield-${fieldKey}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-meta text-faint uppercase tracking-wider">{label}</span>
        <span className="text-meta text-faint/50">{rows.length}项</span>
        {editingIdx === null && (
          <button onClick={startAdd} className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5">
            <Plus size={12} />添加
          </button>
        )}
      </div>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div key={i} className="group">
            {editingIdx === i ? formEl : (
              <div className="flex items-center gap-2 py-1 px-1.5 rounded hover:bg-soft/40 cursor-text transition-colors duration-150"
                onClick={() => startEdit(i)}>
                <span className="text-f13 text-ink flex-1 min-w-0 truncate">{summarize(r)}</span>
                <button onClick={(e) => { e.stopPropagation(); removeRow(i) }} aria-label={`删除第${i + 1}行`}
                  className="opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer text-meta transition-opacity">
                  <X size={13} />
                </button>
              </div>
            )}
          </div>
        ))}
        {editingIdx === 'new' && formEl}
        {rows.length === 0 && editingIdx === null && <span className="text-f13 text-faint/40">—</span>}
      </div>
    </div>
  )
}

// ═══ FactionField:按元数据 dispatch 单个顶层字段到合适 widget ═══
// object/array<object> 走上面两个新 widget;标量类型复用既有 Field 组件(text/textarea/
// number/select/tags),与其余四类实体的既有交互保持一致(点击进入编辑态,immediate=isNew
// 时新建表单直填)。secret_capable 字段额外渲染限知开关(与 backstory_secret/
// private_operation_secret 的既有做法对齐)。当前注册表里 secret_capable 字段全是
// textarea(origin/secret_agenda/artifact_operation/external_manipulation/
// acceleration_methods/私下运作),object/array<object> 字段均非 secret_capable——
// 故两个新 widget 内部不必处理掩码;若未来注册表变化引入嵌套 secret 字段,需在此扩展。
function FactionField({ f, row, isNew, save, uid, readOnly = false }) {
  const value = row[f.key]
  if (readOnly && (f.type === 'object' || f.type === 'array<object>')) {
    return <ReadOnlyField label={f.label} value={typeof value === 'string' ? value : JSON.stringify(value || {}, null, 0)} />
  }
  if (f.type === 'object') {
    return <ObjectField label={f.label} fieldKey={f.key} value={value} itemSchema={f.item_schema} onSave={(v) => save(f.key, v)} />
  }
  if (f.type === 'array<object>') {
    return <ArrayObjectField label={f.label} fieldKey={f.key} value={value} itemSchema={f.item_schema} onSave={(v) => save(f.key, v)} />
  }
  const fType = f.type === 'array<string>' ? 'tags'
    : f.type === 'enum' ? 'select'
    : f.type === 'int' ? 'number'
    : f.type   // 'text' | 'textarea' | 'bool'
  const body = fType === 'tags' ? (
    <Field label={f.label} type="tags" options={value} onSave={(v) => save(f.key, v)} readOnly={readOnly} />
  ) : fType === 'bool' ? (
    readOnly ? <ReadOnlyField label={f.label} value={value ? '是' : '否'} /> : (
    <div className="py-2">
      <div className="flex items-center gap-2">
        <span className="text-meta text-faint uppercase tracking-wider">{f.label}</span>
        <input type="checkbox" checked={!!value} onChange={(e) => save(f.key, e.target.checked)}
          aria-label={f.label} className="w-4 h-4 accent-brand cursor-pointer" />
      </div>
      {f.desc && <div className="text-meta text-faint/60 mt-0.5">{f.desc}</div>}
    </div>
    )
  ) : (
    <Field label={f.label} value={value} type={fType} options={f.enum} description={f.desc}
      onSave={(v) => save(f.key, v)} immediate={isNew} required={isNew && f.key === 'name'} readOnly={readOnly} />
  )
  return (
    <div className={f.deprecated ? 'opacity-60' : undefined}>
      {f.deprecated && <div className="mt-3 pt-3 border-t border-line/60 text-meta text-fore">{DEPRECATED_HINT}</div>}
      {body}
      {isMasked(value) && <SecretMaskHint />}
      {f.secret_capable && !readOnly && (
        <div className="py-1.5 flex items-center gap-2">
          <input type="checkbox" id={`${uid}-sf-${f.key}`} checked={!!row[secretKeyOf(f.key)]}
            onChange={(e) => save(secretKeyOf(f.key), e.target.checked)}
            className="w-4 h-4 accent-brand cursor-pointer" />
          <label htmlFor={`${uid}-sf-${f.key}`} className="text-f12 text-faint cursor-pointer select-none inline-flex items-center gap-1">
            <Lock size={11} />限知(对读者屏蔽此字段,值将打码显示)
          </label>
        </div>
      )}
    </div>
  )
}

// ═══ FactionSchemaView:GET /codex-schema/faction 拉取成功后的渲染路径 ═══
function FactionSchemaView({ schema, row, isNew, onBack, save, onDelete, uid }) {
  const visible = schema.filter((f) => !f.deprecated || hasValue(row[f.key]))
  const ro = !isNew
  return (
    <div className="max-w-2xl mx-auto" data-testid="faction-schema-view">
      <div className="flex items-center gap-3 mb-4">
        {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
        <span className="text-meta text-faint/50">{isNew ? '新建势力' : '势力'}</span>
      </div>
      {ro && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-canvas/50 px-3 py-2" data-testid="codex-readonly-banner">
          <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编对话审批</span>
          <button type="button" data-testid="codex-ask-chief"
            onClick={() => seedChiefCodexWrite('factions', row)}
            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
            让主编写入
          </button>
        </div>
      )}
      <div className="border-t border-line pt-3">
        {visible.map((f) => <FactionField key={f.key} f={f} row={row} isNew={isNew} save={save} uid={uid} readOnly={ro} />)}
      </div>
      <div className="mt-4 pt-3 border-t border-line">
        <button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150">
          <Trash2 size={13}/>删除
        </button>
      </div>
    </div>
  )
}

// 新建时的最小必填集(与 CodexNew.isValid 同源语义):默认 name,伏笔为 text,命题为四键
const REQUIRED_NEW = { facts: ['entity', 'attribute', 'value', 'valid_from'], promises: ['text'] }

// ═══ DetailView ═══
export function DetailView({ type, row, isNew, onBack, onUpdate, onDelete, onCharStateAdded }) {
  // uid:同类 checkbox/select 的 DOM id 前缀。旧硬编码 id(backstory_secret_cb/sf_*)在
  // 新建+详情两个 DetailView 并存时会重复,htmlFor 会错绑到第一个。
  const uid = useId()
  // 整行回传前剔除掩码占位符字段:角色(backstory)/势力(private_operation)勾私密后 GET 打码,
  // 编辑任一字段不得把掩码占位符(SECRET_MASK)写回销毁真值(F-1/F-2)。stripSecretMask 只按值匹配,故只影响被打码字段。
  const save = (key, val) => onUpdate(stripSecretMask({ ...row, [key]: val }))
  const requiredNew = (k) => isNew && (REQUIRED_NEW[type] || ['name']).includes(k)

  // CX-Task 7:faction 元数据驱动——只切这一类(其余四类仍走下方 legacy fieldMap,阶段2 再迁)。
  // factionSchema 初值 null:既表示"尚未拉到"也表示"拉取失败",两种情况下面 render 都会落回
  // legacy fieldMap.factions 分支——不白屏,也不需要额外的 loading 态。
  const [factionSchema, setFactionSchema] = useState(null)
  useEffect(() => {
    if (type !== 'factions') return
    let alive = true
    api.get('/codex-schema/faction')
      .then((s) => { if (alive) setFactionSchema(Array.isArray(s) && s.length ? s : null) })
      .catch(() => { if (alive) setFactionSchema(null) })
    return () => { alive = false }
  }, [type])

  if (type === 'chars') {
    const ro = !isNew
    return (
      <div className="max-w-2xl mx-auto" data-testid="codex-detail-chars">
        <div className="flex items-center gap-3 mb-4">
          {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
          <span className="text-meta text-faint/50">{isNew ? '新建角色' : '角色档案'}</span>
        </div>
        {ro && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-canvas/50 px-3 py-2" data-testid="codex-readonly-banner">
            <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编 s3_patch_character + 审批</span>
            <button type="button" data-testid="codex-ask-chief"
              onClick={() => seedChiefCodexWrite('chars', row)}
              className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
              让主编写入
            </button>
          </div>
        )}
        <div className="border-t border-line pt-3">
          <Field label="名字" value={row.name} placeholder="输入角色名" onSave={(v) => save('name', v)} immediate={isNew} required={requiredNew('name')} readOnly={ro} />
          <Field label="重要度" value={row.importance} type="select" options={['protagonist','major','minor','background']} onSave={(v) => save('importance', v)} immediate={isNew} readOnly={ro} />
          <Field label="外貌" value={row.appearance} type="textarea" placeholder="描述外貌特征" onSave={(v) => save('appearance', v)} immediate={isNew} readOnly={ro} />
          <Field label="性格标签" type="tags" options={row.personality_tags} onSave={(v) => save('personality_tags', v)} readOnly={ro} />
          <Field label="性格深描" value={row.personality_detail} type="textarea" placeholder="深入描述性格" onSave={(v) => save('personality_detail', v)} immediate={isNew} readOnly={ro} />
          <Field label="前史" value={row.backstory} type="textarea" placeholder="角色背景故事" onSave={(v) => save('backstory', v)} immediate={isNew} readOnly={ro} />
          {isNew ? (
            <div className="py-1.5 flex items-center gap-2">
              <input type="checkbox" id={`${uid}-backstory-secret`} checked={!!row.backstory_secret}
                onChange={(e) => save('backstory_secret', e.target.checked)}
                className="w-4 h-4 accent-brand cursor-pointer" />
              <label htmlFor={`${uid}-backstory-secret`} className="text-f12 text-faint cursor-pointer select-none inline-flex items-center gap-1"><Lock size={11} />私密(默认屏蔽前史)</label>
            </div>
          ) : (
            <ReadOnlyField label="前史私密" value={row.backstory_secret ? '是' : '否'} />
          )}
          <Field label="能力" type="abilities" value={row.abilities} onSave={(v) => save('abilities', v)} readOnly={ro} />
          <Field label="弱点" type="tags" options={row.weaknesses} onSave={(v) => save('weaknesses', v)} readOnly={ro} />
          <Field label="表面目标" value={row.surface_goal} placeholder="角色想要什么" onSave={(v) => save('surface_goal', v)} immediate={isNew} section readOnly={ro} />
          <Field label="深层需求" value={row.deep_need} placeholder="角色真正需要什么" onSave={(v) => save('deep_need', v)} immediate={isNew} readOnly={ro} />
          <Field label="内在冲突" value={row.internal_conflict} placeholder="目标与需求的矛盾" onSave={(v) => save('internal_conflict', v)} immediate={isNew} readOnly={ro} />
          <Field label="恐惧" value={row.fear} placeholder="角色最怕什么" onSave={(v) => save('fear', v)} immediate={isNew} readOnly={ro} />
          <Field label="首次出场" value={row.first_appearance} type="number" onSave={(v) => save('first_appearance', v)} immediate={isNew} readOnly={ro} />
        </div>
        {!isNew && <DynamicTimeline characterId={row.id} onStateAdded={onCharStateAdded} />}
        {!isNew && <DynamicRelations characterId={row.id} />}
        <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除角色</button></div>
      </div>
    )
  }

  // CX-Task 7:元数据拉取成功 → 走注册表驱动渲染;失败/未就绪则穿透到下面的 legacy fieldMap。
  if (type === 'factions' && factionSchema) {
    return (
      <FactionSchemaView schema={factionSchema} row={row} isNew={isNew} uid={uid}
        onBack={onBack} save={save} onDelete={onDelete} />
    )
  }

  const fieldMap = {
    // 批D 件1:命题生产表单(限知引擎核心)。entity 填实体 oid(role:名);secret 勾选后命题对读者隐藏,
    // leak_markers 是"出现即算泄密"的标记词表 —— find_leaks 据此对 UI 作者的命题做限知泄露检测。
    facts: [['entity','主体(实体 oid,如 role:焦三)','text'],['attribute','属性','text'],['value','值','textarea'],['valid_from','生效章','number'],['secret','命题私密(对读者隐藏,find_leaks 检测泄露)','secret_flag'],['leak_markers','泄露标记词(逗号分隔,出现即视为泄密)','array_csv']],
    rules: [['name','规则名','text'],['category','类别','rule_cat'],['source','源头','text'],['cost','代价','textarea'],['scope','作用域','scope'],['established_chapter','确立章节','number'],['limitations','限制条件(逗号分隔)','array_csv'],['exceptions','例外情形(逗号分隔)','array_csv'],['capabilities','赋予能力(逗号分隔)','array_csv'],['note','备注','textarea']],
    factions: [['name','势力名','text'],['ideology','意识形态','textarea'],['leader','领袖','text'],['public_face','公开面目','textarea'],['private_operation','私下运作','textarea'],['known_members','已知成员(逗号分隔)','array_csv'],['private_operation_secret','私密(私下运作)','secret_flag']],
    items: [['name','物品名','text'],['category','类别','text'],['description','描述','textarea'],['symbolic_state','状态','select'],['current_owner','持有者','text'],['first_chapter','首次出场章','number'],['special_properties','特殊属性(逗号分隔)','array_csv']],
    terms: [['name','术语名','text'],['category','类别','text'],['definition','定义','textarea'],['first_mention_chapter','首次提及章','number']],
    promises: [['text','伏笔内容','textarea'],['setup_chapter','埋于','number'],['tier','兑现层级','tier_sel'],['resolution','真实答案（作者存档，读者不可见）','textarea'],['kind','类型','kind_sel']],
    motifs: [['name','母题名','text'],['theme','绑定主题','text'],['unfolding','隐喻展开','textarea'],['echoes','物质回声','textarea']],
  }
  const fields = fieldMap[type] || []
  const tabLabel = TABS.find((t) => t.key === type)?.label || type
  const stateOptions = ['active','lost','destroyed','unknown']
  // 世界规则作用域:严格对齐后端 DB ASSERT(migrations/027_setting_completeness.surql
  // `scope IN ['global','regional','faction_specific']`)。曾误含 'local' → 用户选中保存必被
  // SurrealDB 断言拒绝(报文不可读)。P1-8:去 'local',补正确三值。
  const scopeOptions = ['global','regional','faction_specific']
  const tierOptions = [
    { value: 'chapter', label: '章级（近场 +1~3 章内兑现）' },
    { value: 'arc',     label: '卷级（中程 +5~15 章内兑现）' },
    { value: 'book',    label: '书级（贯穿全书，永不超期）' },
  ]
  // 伏笔类型(P1-3):行数据字段名为 `kind`(GET /promises 与后端 DB 一致),仅 promise/red_herring
  // 两值(ledger 三栏 open/closed/red_herring 依此归位)。旧版误用 `promise_kind` 读空、且改文案时
  // 因请求体缺 promise_kind 被后端默认 'promise' 静默重置 red_herring——现统一读写 `kind`,
  // 由 api.editPromise/addPromiseNew 在线上转译 kind→promise_kind(请求体字段名),两向对齐。
  const kindOptions = [
    { value: 'promise',     label: '正伏笔（promise · 需兑现）' },
    { value: 'red_herring', label: '障眼法（red_herring · 误导，永不兑现）' },
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
  const ro = !isNew
  return (
    <div className="max-w-2xl mx-auto" data-testid={`codex-detail-${type}`}>
      <div className="flex items-center gap-3 mb-4">
        {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
        <span className="text-meta text-faint/50">{isNew ? `新建${tabLabel}` : tabLabel}</span>
      </div>
      {ro && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-canvas/50 px-3 py-2" data-testid="codex-readonly-banner">
          <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编对话审批</span>
          <button type="button" data-testid="codex-ask-chief"
            onClick={() => seedChiefCodexWrite(type, row)}
            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
            让主编写入
          </button>
        </div>
      )}
      <div className="border-t border-line pt-3">
        {fields.map(([k, label, ftype]) =>
          ftype === 'secret_flag' ? (
            ro ? (
              <ReadOnlyField key={k} label={label} value={row[k] ? '是' : '否'} />
            ) : (
            <div key={k} className="py-1.5 flex items-center gap-2">
              <input type="checkbox" id={`${uid}-sf-${k}`} checked={!!row[k]}
                onChange={(e) => save(k, e.target.checked)}
                className="w-4 h-4 accent-brand cursor-pointer" />
              <label htmlFor={`${uid}-sf-${k}`} className="text-f12 text-faint cursor-pointer select-none">{label}</label>
            </div>
            )
          ) :
          ftype === 'bool' ? (<div key={k} className="py-2"><div className="text-meta text-faint uppercase tracking-wider mb-1">{label}</div><div className="text-f13 text-ink">{row[k] ? '是' : '否'}</div></div>) :
          ftype === 'rule_cat' ? (
            ro ? <ReadOnlyField key={k} label={label} value={row[k] || 'magic'} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'magic'} onChange={(v) => save(k, v)}>
              {ruleCatOptions.map((o) => <option key={o.value} value={o.value}>{o.label}（{o.value}）</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'scope' ? (
            ro ? <ReadOnlyField key={k} label={label} value={row[k] || '—'} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || ''} onChange={(v) => save(k, v || null)}>
              <option value="">—</option>
              {scopeOptions.map((o) => <option key={o} value={o}>{o}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'tier_sel' ? (
            // 伏笔兑现层级(B-2):章级近场兑现 / 卷级中程 / 书级贯穿全书(书级永不超期)。
            ro ? <ReadOnlyField key={k} label={label} value={row[k] || 'chapter'} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'chapter'} onChange={(v) => save(k, v)}>
              {tierOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'kind_sel' ? (
            // 伏笔类型(P1-3):读写 row.kind;缺省视作 promise。改此值等价 mark-herring(store 同为 SET kind)。
            ro ? <ReadOnlyField key={k} label={label} value={row[k] || 'promise'} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'promise'} onChange={(v) => save(k, v)}>
              {kindOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'array_csv' ? (
            <Field key={k} label={label} value={arrToCSV(row[k])} type="text"
              placeholder="逗号分隔，留空即可" immediate={isNew} readOnly={ro}
              onSave={(v) => save(k, v ? csvToArr(v) : [])} />
          ) :
          ftype === 'select' ? <Field key={k} label={label} value={row[k]} type="select" options={stateOptions} onSave={(v) => save(k, v)} immediate={isNew} readOnly={ro} /> :
          <Field key={k} label={label} value={row[k]} type={ftype === 'textarea' ? 'textarea' : ftype === 'number' ? 'number' : 'text'} onSave={(v) => save(k, v)} immediate={isNew} required={requiredNew(k)} readOnly={ro} />
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
