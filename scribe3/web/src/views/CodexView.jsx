import { useEffect, useState, useRef, useId } from 'react'
import { Users, Boxes, Bookmark, Flame, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, ArrowLeft, Trash2, Plus, Lock, X } from 'lucide-react'
import { api } from '../api'
import { Tag, Input, Textarea, Btn } from '../ui'
import { Field as UIField } from '../ui/Field.jsx'
import { EditableText, ReadOnlyText } from '../ui/EditableText.jsx'
import { showToast } from '../ui/Toast'
import {
  uiStatusLabel,
  optionValue,
  optionLabel,
  labeledOptions,
  ITEM_STATE_CN,
  SCOPE_CN,
  IMPORTANCE_CN,
  PROMISE_TIER_CN,
  PROMISE_KIND_CN,
  RULE_CAT_CN,
} from '../lib/statusLabels'


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
  { key: 'facts', label: '设定·世界真相', icon: Boxes },
  { key: 'rules', label: '世界规则', icon: Shield },
  { key: 'factions', label: '势力', icon: Swords },
  { key: 'items', label: '物品', icon: MapPin },
  { key: 'terms', label: '术语', icon: Tags },
  { key: 'promises', label: '伏笔', icon: Bookmark },
  { key: 'motifs', label: '母题', icon: Flame },
  { key: 'timeline', label: '弧光', icon: GitBranch },
  { key: 'relations', label: '关系', icon: Heart },
]

// 设定库补全/更正种子:实现位于 lib/chiefSeed(含 s3-right-tab 聚焦)。
import {
  seedChiefCodexWrite,
  focusChiefWithSeed,
  seedChiefNarrativeWrite,
} from '../lib/chiefSeed.js'
export { seedChiefCodexWrite, focusChiefWithSeed, seedChiefNarrativeWrite }

function ReadOnlyField({ label, value, section, testId, entityLabel, fieldKey }) {
  return (
    <ReadOnlyText
      label={label}
      value={value}
      section={section}
      testId={testId}
      emptyHint="（空 · 由主编审批写入）"
      entityLabel={entityLabel}
      fieldKey={fieldKey}
      scopeLabel={entityLabel && label ? `${entityLabel} · ${label}` : label}
      emptyAskLabel="聊聊怎么写"
    />
  )
}

// ═══ Field 组件(上下布局,label在上,全宽) ═══
// immediate(新建表单):直填用 bordered Input + ui/Field a11y。
// readOnly:已存在设定只读检视,禁止失焦保存(产品铁律:对话审批写)。
// 默认可写:EditableText click-to-edit(Notion)。
function Field({ label, value, onSave, type = 'text', options, placeholder, section, immediate = false, required = false, description, readOnly = false, entityLabel, fieldKey }) {
  const [val, setVal] = useState(value ?? '')
  const id = useId()

  useEffect(() => { if (!immediate) setVal(value ?? '') }, [value, immediate])

  if (readOnly) {
    if (type === 'tags') {
      return <ReadOnlyField label={label} value={options} section={section} entityLabel={entityLabel} fieldKey={fieldKey} />
    }
    if (type === 'abilities') {
      let ab = value
      try { if (typeof ab === 'string' && ab.trim()) ab = JSON.parse(ab) } catch { /* */ }
      const text = Array.isArray(ab)
        ? ab.map((a) => (typeof a === 'string' ? a : (a?.name || JSON.stringify(a)))).join('、')
        : (value || '')
      return <ReadOnlyField label={label} value={text} section={section} entityLabel={entityLabel} fieldKey={fieldKey} />
    }
    const display = type === 'select' ? uiStatusLabel(value) : value
    return <ReadOnlyField label={label} value={display} section={section} entityLabel={entityLabel} fieldKey={fieldKey} />
  }

  if (immediate && type !== 'tags' && type !== 'abilities') {
    const set = (v) => { setVal(v); onSave(type === 'number' ? (v === '' ? null : Number(v)) : v) }
    return (
      <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
        <UIField label={label} required={required} description={description}>
          {type === 'textarea' ? (
            <Textarea variant="bordered" rows={3} value={val} onChange={(e) => set(e.target.value)} placeholder={placeholder || `输入${label}...`} />
          ) : type === 'select' ? (
            <select value={val ?? ''} onChange={(e) => set(e.target.value)}
              className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-f13 text-ink outline-none transition-colors focus:border-brand cursor-pointer">
              <option value="">—</option>
              {(options || []).map((o) => (
                <option key={String(optionValue(o))} value={optionValue(o)}>{optionLabel(o)}</option>
              ))}
            </select>
          ) : (
            <Input variant="bordered" type={type === 'number' ? 'number' : 'text'} value={val}
              onChange={(e) => set(e.target.value)} placeholder={placeholder || `输入${label}...`} />
          )}
        </UIField>
      </div>
    )
  }

  if (type === 'tags') return <TagsRow label={label} tags={options} onSave={onSave} section={section} />
  if (type === 'abilities') return <AbilitiesRow value={value} onSave={onSave} section={section} />

  // select 暂保留本地编辑态(EditableText 未覆盖 option 列表)
  if (type === 'select') {
    return (
      <SelectClickField
        id={id}
        label={label}
        value={value}
        options={options}
        description={description}
        section={section}
        placeholder={placeholder}
        onSave={onSave}
      />
    )
  }

  return (
    <div className={section ? 'mt-3 pt-3 border-t border-line/60' : ''}>
      <EditableText
        label={label}
        value={value}
        type={type === 'number' ? 'number' : 'text'}
        multiline={type === 'textarea'}
        placeholder={placeholder}
        description={description}
        onCommit={onSave}
      />
    </div>
  )
}

/** select 的 click-to-edit(与 EditableText 同交互) */
function SelectClickField({ id, label, value, options, description, section, placeholder, onSave }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')
  const ref = useRef(null)
  useEffect(() => { if (!editing) setVal(value ?? '') }, [value, editing])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])
  const commit = () => { setEditing(false); if (val !== (value ?? '')) onSave(val) }
  const cancel = () => { setVal(value ?? ''); setEditing(false) }
  if (!value && !editing) {
    return (
      <div className={`py-1.5 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
        <button type="button" onClick={() => setEditing(true)} className="text-f12 text-faint hover:text-brand cursor-pointer transition-colors duration-150">+ 添加{label}</button>
      </div>
    )
  }
  if (editing) {
    return (
      <div className={`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`} onClick={(e) => e.stopPropagation()}>
        <label htmlFor={id} className="block text-meta text-faint uppercase tracking-wider mb-1">{label}</label>
        {description && <div className="text-meta text-faint/60 mb-1.5">{description}</div>}
        <select ref={ref} id={id} value={val ?? ''} onChange={(e) => setVal(e.target.value)} onBlur={commit}
          onKeyDown={(e) => { if (e.key === 'Escape') cancel() }}
          className="w-full h-9 rounded-lg border border-brand/40 bg-canvas px-3 text-f13 text-ink outline-none focus:border-brand cursor-pointer">
          <option value="">—</option>
          {(options || []).map((o) => (
            <option key={String(optionValue(o))} value={optionValue(o)}>{optionLabel(o)}</option>
          ))}
        </select>
        <div className="text-meta text-faint/50 mt-0.5">失焦自动保存 · ESC 取消</div>
      </div>
    )
  }
  return (
    <div className={`group py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-meta text-faint uppercase tracking-wider">{label}</span>
        <button type="button" onClick={() => setEditing(true)} aria-label={`编辑${label}`}
          className="text-meta text-brand opacity-0 group-hover:opacity-100 focus-visible:opacity-100 cursor-pointer transition-opacity">编辑</button>
      </div>
      <div
        role="button"
        tabIndex={0}
        className="text-f13 text-ink leading-relaxed cursor-text hover:bg-soft/30 rounded-md px-2 py-1.5 -mx-1 transition-colors duration-150"
        onClick={() => setEditing(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setEditing(true)
          }
        }}
      >{value ? uiStatusLabel(value) : (placeholder || '—')}</div>
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
          <button onClick={() => setEditing(true)} className="text-f12 text-faint hover:text-brand cursor-pointer">{list.length === 0 ? '+ 添加' : '+'}</button>
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
        {abilities.length === 0 && !adding && <span className="text-f13 text-faint">—</span>}
      </div>
    </div>
  )
}

// ═══ DynamicTimeline(只读 + 主编写入) ═══
// 产品政策:已存在角色禁止表单直填;质变记录走主编审批写。快照查询为只读。
function DynamicTimeline({ characterId, characterName }) {
  const [states, setStates] = useState(null)
  const [snapCh, setSnapCh] = useState('')
  const [snapshot, setSnapshot] = useState(null)
  useEffect(() => {
    api.get(`/char-states?character_id=${encodeURIComponent(characterId)}`)
      .then(setStates).catch(() => setStates([]))
  }, [characterId])
  const querySnapshot = async () => {
    if (!snapCh) return
    const data = await api.get(`/char-state-at?character_id=${encodeURIComponent(characterId)}&chapter=${snapCh}`)
    setSnapshot(data)
  }
  if (!states) return <div className="mt-4 text-f12 text-faint/50">加载中...</div>
  const name = characterName || String(characterId || '').split(':').pop()
  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="dynamic-timeline">
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="text-meta text-faint uppercase tracking-wider">弧光演进史</span>
        <span className="text-meta text-faint/50">{states.length}个质变点</span>
        <button
          type="button"
          data-testid="timeline-ask-chief"
          onClick={() => seedChiefCodexWrite('chars', { id: characterId, name },
            '请记录角色弧光质变(能力/关系/性格/综合),含章号、摘要与必要快照;用对应写工具提交审批。')}
          className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer"
        >
          让主编记录质变
        </button>
      </div>
      <div className="mb-3 flex items-center gap-2 py-1.5">
        <span className="text-meta text-faint">查询第</span>
        <Input variant="ghost" size="sm" type="number" value={snapCh} onChange={(e) => setSnapCh(e.target.value)}
          placeholder="章" aria-label="快照章号" className="w-16" />
        <Btn size="xs" variant="soft" onClick={querySnapshot}>查快照</Btn>
        {snapshot && (
          <div className="flex-1 text-meta text-faint space-y-0.5 min-w-0">
            <div>能力: {Object.keys(snapshot.abilities || {}).length ? JSON.stringify(snapshot.abilities) : '—'}</div>
            <div>关系: {Object.keys(snapshot.relations || {}).length ? JSON.stringify(snapshot.relations) : '—'}</div>
            <div>性格: {snapshot.personality || '—'}</div>
          </div>
        )}
      </div>
      {states.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无弧光记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-3">
          {states.map((s, i) => (
            <div key={i} className="relative">
              <div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-brand border-2 border-surface" />
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-meta text-faint font-medium">第{s.chapter}章</span>
                <Tag tone={s.change_type === 'ability' ? 'fore' : s.change_type === 'relation' ? 'ok' : 'faint'}>{s.change_type}</Tag>
                {s.arc_phase && <span className="text-meta text-fore">{s.arc_phase}</span>}
              </div>
              <div className="text-f13 text-ink">{s.summary}</div>
              {s.trigger_event && <div className="text-meta text-faint/60 mt-0.5">触发: {s.trigger_event}</div>}
            </div>
          ))}
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

// 角色关系:只读列表 + 主编写入(与档案字段同一政策)
function DynamicRelations({ characterId, characterName }) {
  const meLocal = String(characterId || '').split(':').pop()
  const [relations, setRelations] = useState(null)

  useEffect(() => {
    api.characterRelations(9999)
      .then((all) => setRelations((all || []).filter((r) => r.src === meLocal || r.dst === meLocal)))
      .catch(() => setRelations([]))
  }, [characterId, meLocal])

  if (!relations) return null
  const name = characterName || meLocal
  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="dynamic-relations">
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="text-meta text-faint uppercase tracking-wider">角色关系</span>
        <span className="text-meta text-faint/50">{relations.length}条</span>
        <button
          type="button"
          data-testid="relations-ask-chief"
          onClick={() => seedChiefCodexWrite('chars', { id: characterId, name },
            '请建立/演变/结束角色关系(受控词表),含对象、关系类型与章号;用对应写工具提交审批。')}
          className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5"
        >
          <Plus size={12} />让主编维护关系
        </button>
      </div>

      {relations.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无关系记录。</div> : (
        <div className="space-y-1">{relations.map((r) => {
          const otherLocal = r.src === meLocal ? r.dst : r.src
          const dir = r.src === meLocal ? '→' : '←'
          const k = `${r.src}->${r.dst}`
          return (
            <div key={k} className="py-1 px-1.5 rounded hover:bg-soft/40 transition-colors duration-150">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-meta text-faint/60 w-3 text-center" title={r.src === meLocal ? '本角色 → 对方' : '对方 → 本角色'}>{dir}</span>
                <span className="text-f14 font-medium text-ink prose-serif min-w-[60px]">{otherLocal}</span>
                <Tag tone={REL_TONE(r.relation)}>{r.relation}</Tag>
                <span className="text-meta text-faint">第{r.since_chapter}章建立</span>
                {r.until_chapter && <span className="text-meta text-danger">第{r.until_chapter}章结束</span>}
                {r.note && <span className="text-meta text-faint/60 truncate">· {r.note}</span>}
              </div>
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
      <div className="flex items-center gap-2 mb-2"><span className="text-meta text-faint uppercase tracking-wider">状态流转</span><span className="text-meta text-faint/50">当前: {uiStatusLabel(item.symbolic_state, ITEM_STATE_CN)}</span></div>
      {history.length === 0 ? <div className="text-f12 text-faint/50 py-2">尚无状态变更记录。</div> : (
        <div className="relative pl-6 border-l-2 border-brand/30 space-y-2">{history.map((h, i) => (<div key={i} className="relative"><div className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full border-2 border-surface" style={{ background: h.state === 'active' ? 'var(--color-ok)' : h.state === 'lost' ? 'var(--color-fore)' : 'var(--color-danger)' }} /><div className="flex items-center gap-2"><Tag tone={h.state === 'active' ? 'ok' : h.state === 'lost' ? 'fore' : 'faint'}>{uiStatusLabel(h.state, ITEM_STATE_CN)}</Tag>{h.chapter && <span className="text-meta text-faint">第{h.chapter}章</span>}</div>{h.note && <div className="text-f12 text-faint mt-0.5">{h.note}</div>}</div>))}</div>
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
        {rows.length === 0 && editingIdx === null && <span className="text-f13 text-faint">—</span>}
      </div>
    </div>
  )
}

/** 只读嵌套 object / array<object>：按 schema 标签展开,禁止 raw JSON 糊墙 */
function formatNestedReadonly(value, itemSchema) {
  if (value == null || value === '') return null
  if (typeof value === 'string') return value
  // item_schema 可能是 { key: fieldDef } 或 fieldDef[]
  let labelOf = (k) => k
  let preferredKeys = []
  if (Array.isArray(itemSchema)) {
    preferredKeys = itemSchema.map((f) => f.key).filter(Boolean)
    const map = Object.fromEntries(itemSchema.filter((f) => f?.key).map((f) => [f.key, f]))
    labelOf = (k) => map[k]?.label || k
  } else if (itemSchema && typeof itemSchema === 'object') {
    preferredKeys = Object.keys(itemSchema)
    labelOf = (k) => itemSchema[k]?.label || k
  }
  const rowLines = (obj) => {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return String(obj ?? '')
    const keys = preferredKeys.length ? preferredKeys : Object.keys(obj)
    const parts = keys.map((k) => {
      const v = obj[k]
      if (v == null || v === '') return null
      return `${labelOf(k)}: ${typeof v === 'object' ? JSON.stringify(v) : v}`
    }).filter(Boolean)
    // 补 schema 未列但 obj 有的键
    for (const k of Object.keys(obj)) {
      if (keys.includes(k)) continue
      const v = obj[k]
      if (v == null || v === '') continue
      parts.push(`${labelOf(k)}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
    }
    return parts.length ? parts.join(' · ') : '（空）'
  }
  if (Array.isArray(value)) {
    if (!value.length) return null
    return value.map((row, i) => `${i + 1}. ${rowLines(row)}`).join('\n')
  }
  if (typeof value === 'object') return rowLines(value)
  return String(value)
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
    return <ReadOnlyField label={f.label} value={formatNestedReadonly(value, f.item_schema)} />
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

// ═══ SchemaView:GET /codex-schema/{kind} 成功后的通用渲染(势力/角色) ═══
// 字段控件复用 FactionField(按元数据 type dispatch);角色另挂弧光/关系只读区。
function SchemaDrivenView({
  schema, row, isNew, onBack, save, onDelete, uid,
  kindLabel, seedType, testId, deleteLabel, extras = null,
}) {
  const visible = schema.filter((f) => !f.deprecated || hasValue(row[f.key]))
  const ro = !isNew
  return (
    <div className="max-w-2xl mx-auto" data-testid={testId}>
      <div className="flex items-center gap-3 mb-4">
        {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
        <span className="text-meta text-faint/50">{isNew ? `新建${kindLabel}` : kindLabel}</span>
      </div>
      {ro && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 py-1" data-testid="codex-readonly-banner">
          <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编对话审批</span>
          <button type="button" data-testid="codex-ask-chief"
            onClick={() => seedChiefCodexWrite(seedType, row)}
            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
            让主编写入
          </button>
        </div>
      )}
      <div className="border-t border-line pt-3">
        {visible.map((f) => <FactionField key={f.key} f={f} row={row} isNew={isNew} save={save} uid={uid} readOnly={ro} />)}
      </div>
      {extras}
      <div className="mt-4 pt-3 border-t border-line">
        <button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150">
          <Trash2 size={13}/>{deleteLabel || '删除'}
        </button>
      </div>
    </div>
  )
}

function FactionSchemaView({ schema, row, isNew, onBack, save, onDelete, uid }) {
  return (
    <SchemaDrivenView
      schema={schema} row={row} isNew={isNew} onBack={onBack} save={save} onDelete={onDelete} uid={uid}
      kindLabel="势力" seedType="factions" testId="faction-schema-view" deleteLabel="删除"
    />
  )
}

function CharacterSchemaView({ schema, row, isNew, onBack, save, onDelete, uid }) {
  return (
    <SchemaDrivenView
      schema={schema} row={row} isNew={isNew} onBack={onBack} save={save} onDelete={onDelete} uid={uid}
      kindLabel={isNew ? '角色' : '角色档案'} seedType="chars" testId="character-schema-view"
      deleteLabel="删除角色"
      extras={!isNew ? (
        <>
          <DynamicTimeline characterId={row.id} characterName={row.name} />
          <DynamicRelations characterId={row.id} characterName={row.name} />
        </>
      ) : null}
    />
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

  // 元数据驱动 kinds: DetailView type → GET /codex-schema/{kind}
  // schema 初值 null=未拉到/失败 → 落回 legacy fieldMap / 硬编码,不白屏。
  const SCHEMA_KIND_BY_TYPE = {
    factions: 'faction',
    chars: 'character',
    items: 'item',
    terms: 'term',
    rules: 'world_rule',
  }
  const schemaKind = SCHEMA_KIND_BY_TYPE[type] || null
  const [kindSchema, setKindSchema] = useState(null)
  useEffect(() => {
    if (!schemaKind) { setKindSchema(null); return }
    let alive = true
    setKindSchema(null)
    // 优先 codexSchema;否则 api.get;测试 mock 缺一则走 legacy 字段表
    const load = typeof api.codexSchema === 'function'
      ? api.codexSchema(schemaKind)
      : (typeof api.get === 'function' ? api.get(`/codex-schema/${schemaKind}`) : null)
    if (!load) return () => { alive = false }
    Promise.resolve(load)
      .then((s) => { if (alive) setKindSchema(Array.isArray(s) && s.length ? s : null) })
      .catch(() => { if (alive) setKindSchema(null) })
    return () => { alive = false }
  }, [type, schemaKind])

  // 角色 schema 成功 → 注册表渲染;失败/未就绪 → 下方 legacy 硬编码字段表。
  if (type === 'chars' && kindSchema) {
    return (
      <CharacterSchemaView schema={kindSchema} row={row} isNew={isNew} uid={uid}
        onBack={onBack} save={save} onDelete={onDelete} />
    )
  }

  if (type === 'chars') {
    const ro = !isNew
    return (
      <div className="max-w-2xl mx-auto" data-testid="codex-detail-chars">
        <div className="flex items-center gap-3 mb-4">
          {onBack && <button onClick={onBack} className="inline-flex items-center gap-1 text-f13 text-faint hover:text-ink cursor-pointer transition-colors duration-150"><ArrowLeft size={16}/>返回</button>}
          <span className="text-meta text-faint/50">{isNew ? '新建角色' : '角色档案'}</span>
        </div>
        {ro && (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 py-1" data-testid="codex-readonly-banner">
            <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编 s3_patch_character + 审批</span>
            <button type="button" data-testid="codex-ask-chief"
              onClick={() => seedChiefCodexWrite('chars', row)}
              className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
              让主编写入
            </button>
          </div>
        )}
        <div className="border-t border-line pt-3">
          {/* entityLabel：空字段「聊聊怎么写」把条目+字段名送进主编 */}
          {(() => {
            const ent = row.name || row.id || '角色'
            const f = (label, extra) => ({ ...extra, entityLabel: ent, readOnly: ro })
            return (
              <>
                <Field label="名字" value={row.name} placeholder="输入角色名" onSave={(v) => save('name', v)} immediate={isNew} required={requiredNew('name')} {...f('名字', { fieldKey: 'name' })} />
                <Field label="重要度" value={row.importance} type="select" options={labeledOptions(['protagonist', 'major', 'minor', 'background'], IMPORTANCE_CN)} onSave={(v) => save('importance', v)} immediate={isNew} {...f('重要度', { fieldKey: 'importance' })} />
                <Field label="性别" value={row.gender} type="select" options={[{value:'男',label:'男'},{value:'女',label:'女'}]} onSave={(v) => save('gender', v)} immediate={isNew} {...f('性别', { fieldKey: 'gender' })} />
                <Field label="外貌" value={row.appearance} type="textarea" placeholder="描述外貌特征" onSave={(v) => save('appearance', v)} immediate={isNew} {...f('外貌', { fieldKey: 'appearance' })} />
                <Field label="性格标签" type="tags" options={row.personality_tags} onSave={(v) => save('personality_tags', v)} {...f('性格标签', { fieldKey: 'personality_tags' })} />
                <Field label="性格深描" value={row.personality_detail} type="textarea" placeholder="深入描述性格" onSave={(v) => save('personality_detail', v)} immediate={isNew} {...f('性格深描', { fieldKey: 'personality_detail' })} />
                <Field label="前史" value={row.backstory} type="textarea" placeholder="角色背景故事" onSave={(v) => save('backstory', v)} immediate={isNew} {...f('前史', { fieldKey: 'backstory' })} />
                {isNew ? (
                  <div className="py-1.5 flex items-center gap-2">
                    <input type="checkbox" id={`${uid}-backstory-secret`} checked={!!row.backstory_secret}
                      onChange={(e) => save('backstory_secret', e.target.checked)}
                      className="w-4 h-4 accent-brand cursor-pointer" />
                    <label htmlFor={`${uid}-backstory-secret`} className="text-f12 text-faint cursor-pointer select-none inline-flex items-center gap-1"><Lock size={11} />私密(默认屏蔽前史)</label>
                  </div>
                ) : (
                  <ReadOnlyField label="前史私密" value={row.backstory_secret ? '是' : '否'} entityLabel={ent} fieldKey="backstory_secret" />
                )}
                <Field label="能力" type="abilities" value={row.abilities} onSave={(v) => save('abilities', v)} {...f('能力', { fieldKey: 'abilities' })} />
                <Field label="弱点" type="tags" options={row.weaknesses} onSave={(v) => save('weaknesses', v)} {...f('弱点', { fieldKey: 'weaknesses' })} />
                <Field label="表面目标" value={row.surface_goal} placeholder="角色想要什么" onSave={(v) => save('surface_goal', v)} immediate={isNew} section {...f('表面目标', { fieldKey: 'surface_goal' })} />
                <Field label="深层需求" value={row.deep_need} placeholder="角色真正需要什么" onSave={(v) => save('deep_need', v)} immediate={isNew} {...f('深层需求', { fieldKey: 'deep_need' })} />
                <Field label="内在冲突" value={row.internal_conflict} placeholder="目标与需求的矛盾" onSave={(v) => save('internal_conflict', v)} immediate={isNew} {...f('内在冲突', { fieldKey: 'internal_conflict' })} />
                <Field label="恐惧" value={row.fear} placeholder="角色最怕什么" onSave={(v) => save('fear', v)} immediate={isNew} {...f('恐惧', { fieldKey: 'fear' })} />
                <Field label="首次出场" value={row.first_appearance} type="number" onSave={(v) => save('first_appearance', v)} immediate={isNew} {...f('首次出场', { fieldKey: 'first_appearance' })} />
              </>
            )
          })()}
        </div>
        {!isNew && <DynamicTimeline characterId={row.id} characterName={row.name} />}
        {!isNew && <DynamicRelations characterId={row.id} characterName={row.name} />}
        <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除角色</button></div>
      </div>
    )
  }

  // 势力 / 物件 / 术语 / 世界规则 schema 成功 → 注册表;失败 → legacy fieldMap。
  if (type === 'factions' && kindSchema) {
    return (
      <FactionSchemaView schema={kindSchema} row={row} isNew={isNew} uid={uid}
        onBack={onBack} save={save} onDelete={onDelete} />
    )
  }
  if (type === 'items' && kindSchema) {
    return (
      <SchemaDrivenView
        schema={kindSchema} row={row} isNew={isNew} onBack={onBack} save={save} onDelete={onDelete} uid={uid}
        kindLabel="物品" seedType="items" testId="item-schema-view" deleteLabel="删除"
        extras={!isNew ? <ItemStateHistory item={row} /> : null}
      />
    )
  }
  if (type === 'terms' && kindSchema) {
    return (
      <SchemaDrivenView
        schema={kindSchema} row={row} isNew={isNew} onBack={onBack} save={save} onDelete={onDelete} uid={uid}
        kindLabel="术语" seedType="terms" testId="term-schema-view" deleteLabel="删除"
      />
    )
  }
  if (type === 'rules' && kindSchema) {
    return (
      <SchemaDrivenView
        schema={kindSchema} row={row} isNew={isNew} onBack={onBack} save={save} onDelete={onDelete} uid={uid}
        kindLabel="世界规则" seedType="rules" testId="world-rule-schema-view" deleteLabel="删除"
      />
    )
  }

  const fieldMap = {
    // 批D 件1 + PR-6：世界真相生产表单。勿与「场景真相/deduce」混淆。
    // leak_markers = 破绽词（出现即算泄密）；改已有状态请 supersede 勿原地抹历史。
    facts: [
      ['entity', '关于谁（角色/物件等，如 role:焦三）', 'text'],
      ['attribute', '哪方面状态（如 state/位置）', 'text'],
      ['value', '具体内容', 'textarea'],
      ['valid_from', '从第几章起成立', 'number'],
      ['secret', '私密（限知；非持有者视角不可直说）', 'secret_flag'],
      ['leak_markers', '破绽词（出现即算泄密，可选，逗号分隔）', 'array_csv'],
    ],
    rules: [['name','规则名','text'],['category','类别','rule_cat'],['source','源头','text'],['cost','代价','textarea'],['scope','作用域','scope'],['established_chapter','确立章节','number'],['limitations','限制条件(逗号分隔)','array_csv'],['exceptions','例外情形(逗号分隔)','array_csv'],['capabilities','赋予能力(逗号分隔)','array_csv'],['note','备注','textarea']],
    factions: [['name','势力名','text'],['ideology','意识形态','textarea'],['leader','领袖','text'],['public_face','公开面目','textarea'],['private_operation','私下运作','textarea'],['known_members','已知成员(逗号分隔)','array_csv'],['private_operation_secret','私密(私下运作)','secret_flag']],
    items: [['name','物品名','text'],['category','类别','text'],['description','描述','textarea'],['symbolic_state','状态','select'],['current_owner','持有者','text'],['first_chapter','首次出场章','number'],['special_properties','特殊属性(逗号分隔)','array_csv']],
    terms: [['name','术语名','text'],['category','类别','text'],['definition','定义','textarea'],['first_mention_chapter','首次提及章','number']],
    promises: [['text','伏笔内容','textarea'],['setup_chapter','埋于','number'],['tier','兑现层级','tier_sel'],['resolution','真实答案（作者存档，读者不可见）','textarea'],['kind','类型','kind_sel']],
    motifs: [['name','母题名','text'],['theme','绑定主题','text'],['unfolding','隐喻展开','textarea'],['echoes','物质回声','textarea']],
  }
  const fields = fieldMap[type] || []
  const tabLabel = TABS.find((t) => t.key === type)?.label || type
  const stateOptions = labeledOptions(['active', 'lost', 'destroyed', 'unknown'], ITEM_STATE_CN)
  // 世界规则作用域:严格对齐后端 DB ASSERT(migrations/027_setting_completeness.surql
  // `scope IN ['global','regional','faction_specific']`)。曾误含 'local' → 用户选中保存必被
  // SurrealDB 断言拒绝(报文不可读)。P1-8:去 'local',补正确三值。
  const scopeOptions = labeledOptions(['global', 'regional', 'faction_specific'], SCOPE_CN)
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
    { value: 'promise',     label: '正伏笔（需兑现）' },
    { value: 'red_herring', label: '障眼法（误导，永不兑现）' },
  ]
  const ruleCatOptions = labeledOptions(
    ['magic', 'technology', 'social', 'physical', 'economic', 'political'],
    RULE_CAT_CN,
  )
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
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 py-1" data-testid="codex-readonly-banner">
          <span className="text-meta text-faint">只读检视 · 禁止表单直填 · 写入走主编对话审批</span>
          <button type="button" data-testid="codex-ask-chief"
            onClick={() => seedChiefCodexWrite(type, row)}
            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
            让主编写入
          </button>
        </div>
      )}
      <div className="border-t border-line pt-3">
        {fields.map(([k, label, ftype]) => {
          const ent = row.name || row.text || row.id || tabLabel || type
          const roField = { entityLabel: ent, fieldKey: k }
          return (
          ftype === 'secret_flag' ? (
            ro ? (
              <ReadOnlyField key={k} label={label} value={row[k] ? '是' : '否'} {...roField} />
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
            ro ? <ReadOnlyField key={k} label={label} value={uiStatusLabel(row[k] || 'magic', RULE_CAT_CN)} {...roField} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'magic'} onChange={(v) => save(k, v)}>
              {ruleCatOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'scope' ? (
            ro ? <ReadOnlyField key={k} label={label} value={row[k] ? uiStatusLabel(row[k], SCOPE_CN) : '—'} {...roField} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || ''} onChange={(v) => save(k, v || null)}>
              <option value="">—</option>
              {scopeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'tier_sel' ? (
            // 伏笔兑现层级(B-2):章级近场兑现 / 卷级中程 / 书级贯穿全书(书级永不超期)。
            ro ? <ReadOnlyField key={k} label={label} value={uiStatusLabel(row[k] || 'chapter', PROMISE_TIER_CN)} {...roField} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'chapter'} onChange={(v) => save(k, v)}>
              {tierOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'kind_sel' ? (
            // 伏笔类型(P1-3):读写 row.kind;缺省视作 promise。改此值等价 mark-herring(store 同为 SET kind)。
            ro ? <ReadOnlyField key={k} label={label} value={uiStatusLabel(row[k] || 'promise', PROMISE_KIND_CN)} {...roField} /> : (
            <SelectRow key={k} id={`${uid}-${k}`} label={label} isNew={isNew} value={row[k] || 'promise'} onChange={(v) => save(k, v)}>
              {kindOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </SelectRow>
            )
          ) :
          ftype === 'array_csv' ? (
            <Field key={k} label={label} value={arrToCSV(row[k])} type="text"
              placeholder="逗号分隔，留空即可" immediate={isNew} readOnly={ro}
              entityLabel={ent} fieldKey={k}
              onSave={(v) => save(k, v ? csvToArr(v) : [])} />
          ) :
          ftype === 'select' ? <Field key={k} label={label} value={row[k]} type="select" options={stateOptions} onSave={(v) => save(k, v)} immediate={isNew} readOnly={ro} entityLabel={ent} fieldKey={k} /> :
          <Field key={k} label={label} value={row[k]} type={ftype === 'textarea' ? 'textarea' : ftype === 'number' ? 'number' : 'text'} onSave={(v) => save(k, v)} immediate={isNew} required={requiredNew(k)} readOnly={ro} entityLabel={ent} fieldKey={k} />
          )
        })}
      </div>
      {type === 'items' && !isNew && <ItemStateHistory item={row} />}
      <div className="mt-4 pt-3 border-t border-line"><button onClick={onDelete} className="text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13}/>删除</button></div>
    </div>
  )
}

// 注:原主组件 CodexView（设定库整页:Shell + 左栏分类 + 中区列表/详情 + 右栏 EditorChat/检查）
// 已无人 import（设定库现由项目树 + DetailPane 承载,弧光由 views/TimelineView 承载),整段连同
// 其专属子件已删除。本文件只保留 DetailView 这一被复用的详情卡。
