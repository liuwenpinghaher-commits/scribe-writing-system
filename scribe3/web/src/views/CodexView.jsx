import { useEffect, useState, useRef } from 'react'
import { Users, Boxes, Bookmark, Flame, Search, Lock, Plus, Trash2, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, ArrowLeft, Loader2, MessageSquare, Send, BookText, Network, Activity, Feather, Eye } from 'lucide-react'
import { api } from '../api'
import { Btn, Tag } from '../ui'
import { Shell } from '../shell'

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

// ═══ Field 组件(上下布局,label在上,全宽) ═══
function Field({ label, value, onSave, type = 'text', options, placeholder, section }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')
  const ref = useRef(null)
  const isEmpty = !value

  useEffect(() => { if (!editing) setVal(value ?? '') }, [value, editing])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])

  const commit = () => { setEditing(false); const fv = type === 'number' ? (val === '' ? null : Number(val)) : val; if (fv !== (value ?? '')) onSave(fv) }
  const cancel = () => { setVal(value ?? ''); setEditing(false) }
  const inputBase = 'w-full rounded-md border border-brand/40 bg-canvas px-3 py-2 text-[13px] text-ink leading-relaxed outline-none focus:border-brand'

  if (isEmpty && !editing) {
    return (<div className={`py-1.5 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <button onClick={() => setEditing(true)} className="text-[12px] text-faint/40 hover:text-brand cursor-pointer transition-colors duration-150">+ 添加{label}</button>
    </div>)
  }
  if (type === 'tags') return <TagsRow label={label} tags={options} onSave={onSave} section={section} />
  if (type === 'abilities') return <AbilitiesRow value={value} onSave={onSave} section={section} />

  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1">{label}</div>
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
          <div className="text-[10px] text-faint/50 mt-0.5">失焦自动保存 · ESC 取消</div>
        </div>
      ) : (
        <div className="text-[13px] text-ink leading-relaxed cursor-text hover:bg-soft/30 rounded-md px-2 py-1.5 -mx-1 transition-colors duration-150 whitespace-pre-wrap"
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
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1">{label}</div>
      <div className="flex flex-wrap items-center gap-1" onClick={(e) => editing && e.stopPropagation()}>
        {list.map((t, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-[12px] text-fore bg-fore/10 px-2 py-0.5 rounded">
            {t}{editing && <button onClick={() => remove(i)} className="text-faint hover:text-danger cursor-pointer ml-0.5">×</button>}
          </span>
        ))}
        {editing ? (
          <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() }; if (e.key === 'Escape') setEditing(false) }}
            onBlur={exitIfEmpty} placeholder="回车添加..." className="w-28 h-6 text-[12px] bg-transparent border-b border-brand/40 text-ink outline-none placeholder:text-faint/40" />
        ) : list.length === 0 ? (
          <button onClick={() => setEditing(true)} className="text-[12px] text-faint/40 hover:text-brand cursor-pointer">+ 添加</button>
        ) : null}
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
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="能力名称" autoFocus onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="flex-1 h-7 rounded border border-line bg-canvas px-2 text-[12px] text-ink outline-none" />
        <input value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })} placeholder="等级" onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-24 h-7 rounded border border-line bg-canvas px-2 text-[12px] text-ink outline-none" />
      </div>
      <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="描述" rows={2} onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-full rounded border border-line bg-canvas px-2 py-1 text-[12px] text-ink outline-none resize-y" />
      <div className="flex items-center gap-2">
        <input type="number" value={form.acquired_chapter} onChange={(e) => setForm({ ...form, acquired_chapter: e.target.value })} placeholder="第几章习得" onKeyDown={(e) => { if (e.key === 'Escape') { setAdding(false); setEditingIdx(null) } }} className="w-28 h-7 rounded border border-line bg-canvas px-2 text-[12px] text-ink outline-none" />
        <button onClick={saveForm} className="px-3 h-7 rounded bg-brand text-white text-[12px] cursor-pointer">保存</button>
        <button onClick={() => { setAdding(false); setEditingIdx(null) }} className="px-2 h-7 rounded text-faint text-[12px] cursor-pointer">取消</button>
      </div>
    </div>
  )
  return (
    <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="text-[11px] text-faint uppercase tracking-wider mb-1">能力</div>
      <div className="space-y-1.5">
        {abilities.map((ab, i) => (
          <div key={i} className="group">
            {editingIdx === i ? formEl : (
              <div className="flex items-center gap-2 py-1 px-1 rounded hover:bg-soft/40 cursor-text transition-colors duration-150" onClick={() => { setEditingIdx(i); setForm(ab) }}>
                <span className="text-[13px] font-medium text-ink">{ab.name}</span>
                <Tag tone={ab.level === '宗师级' || ab.level === '高' ? 'fore' : 'faint'}>{ab.level || '—'}</Tag>
                {ab.acquired_chapter && <span className="text-[10px] text-faint">第{ab.acquired_chapter}章</span>}
                {ab.description && <span className="text-[11px] text-faint/60 truncate flex-1">{ab.description}</span>}
                <button onClick={(e) => { e.stopPropagation(); remove(i) }} className="opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer text-[11px] transition-opacity">删除</button>
              </div>
            )}
          </div>
        ))}
        {adding ? formEl : <button onClick={(e) => { e.stopPropagation(); setAdding(true); setForm({ name: '', level: '', description: '', acquired_chapter: '' }) }} className="text-[11px] text-brand hover:text-brand/80 cursor-pointer">+ 添加能力</button>}
        {abilities.length === 0 && !adding && <span className="text-[13px] text-faint/40">—</span>}
      </div>
    </div>
  )
}

// ═══ TimelineCard (独立组件) ═══
function TimelineCard({ char }) {
  const [states, setStates] = useState(null)
  useEffect(() => { api.get(`/char-states?character_id=${encodeURIComponent(char.id)}`).then((r) => r.json()).then(setStates).catch(() => setStates([])) }, [char.id])
  if (!states || states.length === 0) return null
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <div className="flex items-center gap-2 mb-2"><span className="text-[14px] font-semibold text-ink prose-serif">{char.name}</span><span className="text-[11px] text-faint">{states.length}个弧光点</span></div>
      <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
        {states.map((s, i) => (
          <div key={i} className="relative">
            <div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" />
            <div className="flex items-center gap-2 mb-0.5"><span className="text-[11px] text-faint font-medium">第{s.chapter}章</span><Tag tone={s.change_type === 'ability' ? 'fore' : s.change_type === 'relation' ? 'ok' : 'faint'}>{s.change_type}</Tag>{s.arc_phase && <span className="text-[11px] text-fore">{s.arc_phase}</span>}</div>
            <div className="text-[13px] text-ink">{s.summary}</div>
            {s.trigger_event && <div className="text-[11px] text-faint/60 mt-0.5">触发: {s.trigger_event}</div>}
          </div>
        ))}
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
  const [form, setForm] = useState({ chapter: '', change_type: 'ability', summary: '', arc_phase: '' })
  useEffect(() => { api.get(`/char-states?character_id=${encodeURIComponent(characterId)}`).then((r) => r.json()).then(setStates).catch(() => setStates([])) }, [characterId])
  const reload = () => { api.get(`/char-states?character_id=${encodeURIComponent(characterId)}`).then((r) => r.json()).then(setStates) }
  const addState = async () => { if (!form.chapter || !form.summary) return; await api.post('/char-states', { ...form, character_id: characterId, chapter: Number(form.chapter) }); setAdding(false); setForm({ chapter: '', change_type: 'ability', summary: '', arc_phase: '' }); reload() }
  const querySnapshot = async () => { if (!snapCh) return; const r = await api.get(`/char-state-at?character_id=${encodeURIComponent(characterId)}&chapter=${snapCh}`); setSnapshot(await r.json()) }
  if (!states) return <div className="mt-4 text-[12px] text-faint/50">加载中...</div>
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">弧光演进史</span><span className="text-[11px] text-faint/50">{states.length}个质变点</span><button onClick={() => setAdding(!adding)} className="ml-auto text-[11px] text-brand hover:text-brand/80 cursor-pointer">+ 记录质变</button></div>
      <div className="mb-3 flex items-center gap-2 p-2 rounded-lg bg-soft/30">
        <span className="text-[11px] text-faint">查询第</span><input type="number" value={snapCh} onChange={(e) => setSnapCh(e.target.value)} placeholder="章" className="w-16 h-7 rounded border border-line bg-canvas px-1.5 text-[12px] text-ink outline-none" />
        <button onClick={querySnapshot} className="px-2 h-7 rounded text-[11px] bg-brand/10 text-brand cursor-pointer">查快照</button>
        {snapshot && (<div className="flex-1 text-[11px] text-faint space-y-0.5"><div>能力: {Object.keys(snapshot.abilities || {}).length ? JSON.stringify(snapshot.abilities) : '—'}</div><div>关系: {Object.keys(snapshot.relations || {}).length ? JSON.stringify(snapshot.relations) : '—'}</div><div>性格: {snapshot.personality || '—'}</div></div>)}
      </div>
      {adding && (<div className="mb-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2" onClick={(e) => e.stopPropagation()}>
        <div className="flex gap-2"><input type="number" placeholder="第几章" value={form.chapter} onChange={(e) => setForm({ ...form, chapter: e.target.value })} className="w-20 h-8 rounded-md border border-line bg-canvas px-2 text-[12px] text-ink outline-none" /><select value={form.change_type} onChange={(e) => setForm({ ...form, change_type: e.target.value })} className="h-8 rounded-md border border-line bg-canvas px-2 text-[12px] text-ink outline-none cursor-pointer"><option value="ability">能力变化</option><option value="relation">关系质变</option><option value="personality">性格转折</option><option value="composite">综合</option></select><input placeholder="弧光阶段" value={form.arc_phase} onChange={(e) => setForm({ ...form, arc_phase: e.target.value })} className="flex-1 h-8 rounded-md border border-line bg-canvas px-2 text-[12px] text-ink outline-none" /></div>
        <textarea placeholder="发生了什么变化..." value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} rows={2} className="w-full rounded-md border border-line bg-canvas px-2 py-1.5 text-[12px] text-ink outline-none resize-y" />
        <div className="flex gap-2"><button onClick={addState} className="px-3 h-7 rounded-lg bg-brand text-white text-[12px] cursor-pointer">保存</button><button onClick={() => setAdding(false)} className="px-3 h-7 rounded-lg text-faint text-[12px] cursor-pointer">取消</button></div>
      </div>)}
      {states.length === 0 ? <div className="text-[12px] text-faint/50 py-2">尚无弧光记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
          {states.map((s, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" /><div className="flex items-center gap-2 mb-0.5"><span className="text-[11px] text-faint font-medium">第{s.chapter}章</span><Tag tone={s.change_type === 'ability' ? 'fore' : s.change_type === 'relation' ? 'ok' : 'faint'}>{s.change_type}</Tag>{s.arc_phase && <span className="text-[11px] text-fore">{s.arc_phase}</span>}</div><div className="text-[13px] text-ink">{s.summary}</div>{s.trigger_event && <div className="text-[11px] text-faint/60 mt-0.5">触发: {s.trigger_event}</div>}</div>))}
        </div>
      )}
    </div>
  )
}

// ═══ DynamicRelations ═══
function DynamicRelations({ characterId }) {
  const [relations, setRelations] = useState(null)
  useEffect(() => { api.get('/character-relations?chapter=9999').then((r) => r.json()).then((all) => { setRelations((all || []).filter((r) => r.src === characterId || r.dst === characterId)) }).catch(() => setRelations([])) }, [characterId])
  if (!relations) return null
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">角色关系</span><span className="text-[11px] text-faint/50">{relations.length}条</span></div>
      {relations.length === 0 ? <div className="text-[12px] text-faint/50 py-2">尚无关系记录。</div> : (
        <div className="space-y-1">{relations.map((r, i) => { const oid = r.src === characterId ? r.dst : r.src; return (<div key={i} className="flex items-center gap-3 py-1 px-2 rounded hover:bg-soft/40 transition-colors duration-150"><span className="text-[14px] font-medium text-ink prose-serif min-w-[60px]">{(oid || '').split(':').pop()}</span><Tag tone={['盟友','同门','熟人','夫妻'].includes(r.relation) ? 'ok' : ['利益对立','仇敌'].includes(r.relation) ? 'fore' : 'faint'}>{r.relation}</Tag><span className="text-[11px] text-faint">第{r.since_chapter}章建立</span>{r.until_chapter && <span className="text-[11px] text-danger">第{r.until_chapter}章结束</span>}</div>) })}</div>
      )}
    </div>
  )
}

// ═══ ItemStateHistory ═══
function ItemStateHistory({ item }) {
  const history = item.state_history || []
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">状态流转</span><span className="text-[11px] text-faint/50">当前: {item.symbolic_state}</span></div>
      {history.length === 0 ? <div className="text-[12px] text-faint/50 py-2">尚无状态变更记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-2">{history.map((h, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full border-2 border-surface" style={{ background: h.state === 'active' ? '#10b981' : h.state === 'lost' ? '#f59e0b' : '#ef4444' }} /><div className="flex items-center gap-2"><Tag tone={h.state === 'active' ? 'ok' : h.state === 'lost' ? 'fore' : 'faint'}>{h.state}</Tag>{h.chapter && <span className="text-[11px] text-faint">第{h.chapter}章</span>}</div>{h.note && <div className="text-[12px] text-faint mt-0.5">{h.note}</div>}</div>))}</div>
      )}
    </div>
  )
}

// ═══ EditorChat — 主编对话面板(右栏) ═══
function EditorChat({ context }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async () => {
    if (!input.trim() || sending) return
    const msg = input.trim()
    setMessages((m) => [...m, { role: 'user', text: msg }])
    setInput('')
    setSending(true)
    try {
      const res = await fetch((import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:3321') + '/chat/stream?msg=' + encodeURIComponent(msg) + '&work=main')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantText = ''
      setMessages((m) => [...m, { role: 'assistant', text: '' }])
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.slice(6))
              if (d.delta) { assistantText += d.delta; setMessages((m) => { const nm = [...m]; nm[nm.length - 1] = { role: 'assistant', text: assistantText }; return nm }) }
              if (d.done) break
              if (d.error) { setMessages((m) => { const nm = [...m]; nm[nm.length - 1] = { role: 'assistant', text: '错误: ' + d.error }; return nm }) }
            } catch {}
          }
        }
      }
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: '连接失败: ' + e.message }])
    } finally { setSending(false) }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-2 space-y-2">
        {messages.length === 0 && <div className="text-[12px] text-faint/50 text-center py-4">与主编讨论设定。<br/>可问:"帮我完善胡不为的角色设定"<br/>"这个世界还缺什么规则?"</div>}
        {messages.map((m, i) => (
          <div key={i} className={`text-[13px] leading-relaxed ${m.role === 'user' ? 'text-ink bg-soft/50 rounded-lg px-2.5 py-1.5 ml-4' : 'text-ink'}`}>
            {m.role === 'assistant' && <span className="text-[10px] text-faint uppercase mr-1">主编</span>}
            {m.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="shrink-0 border-t border-line p-2 flex items-center gap-1.5">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="问主编..." disabled={sending}
          className="flex-1 h-8 rounded-lg border border-line bg-canvas px-2.5 text-[13px] text-ink outline-none focus:border-brand placeholder:text-faint/50 disabled:opacity-50" />
        <button onClick={send} disabled={sending || !input.trim()}
          className="w-8 h-8 rounded-lg bg-brand text-white inline-flex items-center justify-center cursor-pointer disabled:opacity-40 shrink-0">
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}

// ═══ DetailView ═══
function DetailView({ type, row, isNew, onBack, onUpdate, onDelete }) {
  const save = (key, val) => onUpdate({ ...row, [key]: val })
  if (type === 'chars') {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <button onClick={onBack} className="inline-flex items-center gap-1 text-[13px] text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>
          <span className="text-[11px] text-faint/50">{isNew ? '新建角色' : '角色档案'}</span>
        </div>
        <div className="border-t border-line pt-3">
          <Field label="名字" value={row.name} placeholder="输入角色名" onSave={(v) => save('name', v)} />
          <Field label="重要度" value={row.importance} type="select" options={['protagonist','major','minor','background']} onSave={(v) => save('importance', v)} />
          <Field label="外貌" value={row.appearance} type="textarea" placeholder="描述外貌特征" onSave={(v) => save('appearance', v)} />
          <Field label="性格标签" type="tags" options={row.personality_tags} onSave={(v) => save('personality_tags', v)} />
          <Field label="性格深描" value={row.personality_detail} type="textarea" placeholder="深入描述性格" onSave={(v) => save('personality_detail', v)} />
          <Field label="前史" value={row.backstory} type="textarea" placeholder="角色背景故事" onSave={(v) => save('backstory', v)} />
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
        <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-[12px] text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除角色</button></div>
      </div>
    )
  }
  const fieldMap = {
    facts: [['entity','主体','text'],['attribute','属性','text'],['value','值','textarea'],['valid_from','生效章','number'],['secret','私密','bool']],
    rules: [['name','规则名','text'],['category','类别','text'],['source','源头','text'],['cost','代价','textarea'],['note','备注','textarea']],
    factions: [['name','势力名','text'],['ideology','意识形态','textarea'],['leader','领袖','text'],['public_face','公开面目','textarea'],['private_operation','私下运作','textarea']],
    items: [['name','物品名','text'],['category','类别','text'],['description','描述','textarea'],['symbolic_state','状态','select'],['current_owner','持有者','text']],
    terms: [['name','术语名','text'],['category','类别','text'],['definition','定义','textarea']],
    promises: [['text','伏笔内容','textarea'],['setup_chapter','埋于','number'],['promise_kind','类型','text']],
    motifs: [['name','母题名','text'],['theme','绑定主题','text'],['unfolding','隐喻展开','textarea'],['echoes','物质回声','textarea']],
  }
  const fields = fieldMap[type] || []
  const tabLabel = TABS.find((t) => t.key === type)?.label || type
  const stateOptions = ['active','lost','destroyed','unknown']
  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={onBack} className="inline-flex items-center gap-1 text-[13px] text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>
        <span className="text-[11px] text-faint/50">{isNew ? `新建${tabLabel}` : tabLabel}</span>
      </div>
      <div className="border-t border-line pt-3">
        {fields.map(([k, label, ftype]) =>
          ftype === 'bool' ? (<div key={k} className="py-2"><div className="text-[11px] text-faint uppercase tracking-wider mb-1">{label}</div><div className="text-[13px] text-ink">{row[k] ? '是' : '否'}</div></div>) :
          ftype === 'select' ? <Field key={k} label={label} value={row[k]} type="select" options={stateOptions} onSave={(v) => save(k, v)} /> :
          <Field key={k} label={label} value={row[k]} type={ftype === 'textarea' ? 'textarea' : ftype === 'number' ? 'number' : 'text'} onSave={(v) => save(k, v)} />
        )}
      </div>
      {type === 'items' && !isNew && <ItemStateHistory item={row} />}
      <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-[12px] text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除</button></div>
    </div>
  )
}

// ═══ 主组件 — 使用 Shell 框架(左栏导航 + 中区内容 + 右栏主编对话) ═══
export function CodexView({ work }) {
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState({ chars: [], facts: [], rules: [], factions: [], items: [], terms: [], places: [], promises: [], motifs: [], completeness: null, relations: [] })
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  const reload = () => {
    setLoading(true)
    Promise.all([
      api.entities().then((es) => ({ chars: es.filter((e) => e.kind === 'character'), places: es.filter((e) => e.kind === 'place') })),
      api.facts(99999).then((f) => ({ facts: f })),
      api.get('/world-rules').then((r) => r.json()).catch(() => []),
      api.get('/factions').then((r) => r.json()).catch(() => []),
      api.get('/items').then((r) => r.json()).catch(() => []),
      api.get('/terms').then((r) => r.json()).catch(() => []),
      api.get('/setting-completeness').then((r) => r.json()).catch(() => null),
      api.get('/character-relations?chapter=9999').then((r) => r.json()).catch(() => []),
      api.promises().catch(() => []), api.motifs().catch(() => []),
    ]).then(([ent, fac, rules, factions, items, terms, comp, rels, promises, motifs]) => {
      setData({ ...ent, ...fac, rules, factions, items, terms, completeness: comp, relations: rels, promises, motifs }); setLoading(false)
    })
  }
  useEffect(() => { reload() }, [])
  useEffect(() => { const onKey = (e) => { if (e.key === 'Escape') setSelected(null) }; window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey) }, [])

  const f = (s) => !q.trim() || (s || '').includes(q.trim())
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
  const addNew = (type) => setSelected({ type, row: { name: '', text: '', entity: '', attribute: '', value: '' }, isNew: true })

  // ─── 详情页模式(全屏,不使用 Shell) ───
  if (selected) {
    return (
      <div className="h-full flex flex-col bg-canvas">
        <div className="flex-1 min-h-0 overflow-y-auto"><div className="px-6 py-5">
          <DetailView type={selected.type} row={selected.row} isNew={selected.isNew}
            onBack={() => setSelected(null)} onUpdate={(updated) => updateRow(selected.type, updated)}
            onDelete={() => deleteRow(selected.type, selected.row)} />
        </div></div>
      </div>
    )
  }

  // ─── 中区内容 ───
  const centerContent = (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-5">
        {loading ? <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2"/>加载中...</div> : (
          <>
            {/* 搜索 + 新建 */}
            <div className="flex items-center gap-2 mb-4">
              <div className="flex items-center gap-1.5 h-8 rounded-lg border border-line bg-canvas px-2.5 flex-1">
                <Search size={14} className="text-faint" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索…" className="flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint/60" />
              </div>
              {!['overview','timeline','relations'].includes(tab) && <Btn variant="primary" size="sm" onClick={() => addNew(tab)}><Plus size={14} />新建</Btn>}
            </div>

            {/* 概览 */}
            {tab === 'overview' && data.completeness && (
              <div className="space-y-4">
                <div className="flex items-center gap-3"><span className="text-[28px] font-bold text-ink">{data.completeness.completeness_score}</span><span className="text-[14px] text-faint">设定完整度 / 100</span></div>
                <div className="grid grid-cols-3 gap-3">
                  {[['角色', data.completeness.total_chars, Users], ['世界规则', data.completeness.total_rules, Shield], ['势力', data.completeness.total_factions, Swords], ['地点', data.completeness.total_places, MapPin], ['事实/命题', data.completeness.total_facts, Boxes], ['物品', data.items?.length || 0, MapPin], ['术语', data.terms?.length || 0, Tags], ['伏笔', data.promises?.length || 0, Bookmark], ['母题', data.motifs?.length || 0, Flame]].map(([label, count, Icon]) => (
                    <div key={label} className="rounded-xl border border-line bg-surface p-3 transition-colors duration-150 hover:border-brand/20"><div className="flex items-center gap-2 text-[12px] text-faint mb-1"><Icon size={14}/>{label}</div><div className="text-[20px] font-semibold text-ink">{count}</div></div>
                  ))}
                </div>
                {data.completeness.missing_dimensions?.length > 0 && (<div className="rounded-xl border border-danger/30 bg-danger/5 p-3"><div className="text-[13px] text-danger font-medium mb-1">缺失维度</div><ul className="text-[12px] text-faint space-y-0.5">{data.completeness.missing_dimensions.map((m, i) => <li key={i}>· {m}</li>)}</ul></div>)}
                {data.completeness.char_issues?.length > 0 && (<div className="rounded-xl border border-line bg-surface p-3"><div className="text-[13px] text-ink font-medium mb-1">角色问题</div><div className="text-[12px] text-faint space-y-0.5">{data.completeness.char_issues.map((c, i) => <div key={i}>{c.name}: {c.issues.join(', ')}</div>)}</div></div>)}
              </div>
            )}

            {/* 角色卡片 */}
            {tab === 'chars' && (
              <div className="space-y-3">
                {data.chars.filter((c) => f(c.name)).length === 0 ? <div className="text-center py-12 text-[13px] text-faint/50">暂无角色</div> :
                data.chars.filter((c) => f(c.name)).map((c) => (
                  <div key={c.id} className="rounded-2xl border border-line bg-surface p-4 group cursor-pointer hover:border-brand/30 transition-colors duration-150" onClick={() => setSelected({ type: 'chars', row: c })}>
                    <div className="flex items-center gap-2 mb-1.5"><span className="text-[16px] font-semibold text-ink prose-serif">{c.name}</span>{c.importance && <Tag tone={c.importance === 'protagonist' ? 'fore' : c.importance === 'major' ? 'fore' : 'faint'}>{c.importance}</Tag>}{c.first_appearance && <span className="text-[10px] text-faint">第{c.first_appearance}章</span>}</div>
                    {c.surface_goal && <div className="text-[13px] text-fore mb-1.5">目标: {c.surface_goal}</div>}
                    {c.backstory && <div className="text-[12px] text-faint leading-relaxed mb-2 line-clamp-2">{c.backstory}</div>}
                    {c.personality_tags?.length > 0 && <div className="flex items-center gap-1 flex-wrap">{c.personality_tags.map((t) => <Tag key={t} tone="fore">{t}</Tag>)}</div>}
                    {c.weaknesses?.length > 0 && <div className="flex items-center gap-1 flex-wrap mt-1">{c.weaknesses.map((w, i) => <span key={i} className="text-[11px] text-secret/70 bg-secret/5 px-1.5 py-0.5 rounded">{w}</span>)}</div>}
                  </div>
                ))}
              </div>
            )}

            {/* 通用表格 */}
            {['facts','rules','factions','items','terms','promises','motifs'].includes(tab) && (
              <div className="overflow-x-auto"><table className="w-full text-[13px] border-collapse">
                <thead><tr>
                  {tab === 'facts' && <><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase tracking-wider" style={{width:'20%'}}>主体</th><th style={{width:'18%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">属性</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">值</th><th style={{width:'8%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">私密</th></>}
                  {tab === 'rules' && <><th style={{width:'22%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">规则</th><th style={{width:'14%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">类别</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">代价</th></>}
                  {tab === 'factions' && <><th style={{width:'20%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">势力</th><th style={{width:'24%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">意识形态</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">领袖</th></>}
                  {tab === 'items' && <><th style={{width:'18%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">物品</th><th style={{width:'14%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">类别</th><th style={{width:'16%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">状态</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">描述</th></>}
                  {tab === 'terms' && <><th style={{width:'18%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">术语</th><th style={{width:'14%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">类别</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">定义</th></>}
                  {tab === 'promises' && <><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">伏笔</th><th style={{width:'12%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">埋于</th><th style={{width:'14%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">状态</th></>}
                  {tab === 'motifs' && <><th style={{width:'20%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">母题</th><th style={{width:'28%'}} className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">绑定主题</th><th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase">隐喻展开</th></>}
                </tr></thead>
                <tbody>
                  {(data[tab] || []).filter((x) => f(x.value) || f(x.attribute) || f(x.text) || f(x.name) || f(x.category)).length === 0 ? <tr><td colSpan="5" className="text-center py-8 text-faint/50">暂无数据</td></tr> :
                  (data[tab] || []).filter((x) => f(x.value) || f(x.attribute) || f(x.text) || f(x.name) || f(x.category)).map((x) => (
                    <tr key={x.id || x.name} className="group border-b border-line/60 hover:bg-brand/[0.04] transition-colors duration-150 cursor-pointer" onClick={() => setSelected({ type: tab, row: x })}>
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
              </table></div>
            )}

            {/* 弧光 */}
            {tab === 'timeline' && <div className="space-y-4">{data.chars.filter((c) => f(c.name)).map((c) => <TimelineCard key={c.id} char={c} />)}{data.chars.length === 0 && <div className="text-center py-12 text-[13px] text-faint/50">暂无角色</div>}</div>}

            {/* 关系 */}
            {tab === 'relations' && (
              <div className="space-y-3">
                {data.relations.length === 0 ? <div className="text-center py-12 text-[13px] text-faint/50">无关系数据</div> :
                data.relations.map((r, i) => (
                  <div key={i} className="rounded-xl border border-line bg-surface p-3 flex items-center gap-4 transition-colors duration-150 hover:border-brand/20">
                    <span className="text-[14px] font-medium text-ink prose-serif min-w-[80px]">{r.src?.split(':').pop() || r.src}</span>
                    <span className="flex-1 text-center"><Tag tone={['盟友','同门','熟人','夫妻'].includes(r.relation) ? 'ok' : ['利益对立','仇敌'].includes(r.relation) ? 'fore' : 'faint'}>{r.relation}</Tag></span>
                    <span className="text-[14px] font-medium text-ink prose-serif min-w-[80px] text-right">{r.dst?.split(':').pop() || r.dst}</span>
                    <span className="text-[11px] text-faint">第{r.since_chapter}章</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )

  // ─── 左栏:设定导航 ───
  const leftCaps = TABS.map((t) => ({
    key: t.key, label: t.label, icon: t.icon,
    badge: ['overview','timeline','relations'].includes(t.key) ? undefined : (data[t.key]?.length || 0),
    render: () => (
      <div className="space-y-0.5">
        {TABS.map((tt) => (
          <button key={tt.key} onClick={() => { setTab(tt.key); setSelected(null) }}
            className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-[13px] transition-colors cursor-pointer ${tab === tt.key ? 'bg-soft text-ink font-medium' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <tt.icon size={14} />{tt.label}
            {!['overview','timeline','relations'].includes(tt.key) && <span className="ml-auto text-faint tnum text-[11px]">{data[tt.key]?.length || 0}</span>}
          </button>
        ))}
      </div>
    ),
  }))

  // ─── 右栏:主编对话 ───
  const rightCaps = [{
    key: 'chat', label: '主编', icon: MessageSquare,
    render: () => <EditorChat context={tab} />,
  }]

  // ─── 顶栏 ───
  const topbar = (
    <header className="h-11 shrink-0 border-b border-line bg-surface flex items-center px-4 gap-2">
      <span className="text-[14px] font-semibold text-ink">设定库</span>
      <span className="text-[11px] text-faint">· {TABS.find((t) => t.key === tab)?.label}</span>
      {data.completeness && <span className="ml-auto text-[11px] text-faint">完整度 <span className="text-ink font-medium tnum">{data.completeness.completeness_score}</span>/100</span>}
    </header>
  )

  return (
    <Shell topbar={topbar} center={centerContent}
      left={{ caps: leftCaps, active: 'overview', onActive: () => {} }}
      right={{ caps: rightCaps, active: 'chat', onActive: () => {} }} />
  )
}
