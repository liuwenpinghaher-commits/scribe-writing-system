import { useEffect, useState } from 'react'
import { Users, Boxes, Bookmark, Flame, Search, Lock, Plus, Pencil, Trash2, X, Shield, Swords, MapPin, Tags, PieChart, GitBranch, Heart, Check, Undo2 } from 'lucide-react'
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
const FIELDS = {
  chars: [
    { k: 'name', label: '名字' }, { k: 'importance', label: '重要度' },
    { k: 'backstory', label: '前史', area: true },
    { k: 'appearance', label: '外貌', area: true },
    { k: 'personality_detail', label: '性格深描', area: true },
    { k: 'abilities', label: '能力', area: true },
    { k: 'surface_goal', label: '目标' }, { k: 'deep_need', label: '深层需求' },
    { k: 'internal_conflict', label: '内在冲突' }, { k: 'fear', label: '恐惧' },
  ],
  facts: [{ k: 'entity', label: '主体' }, { k: 'attribute', label: '属性' }, { k: 'value', label: '值', area: true }, { k: 'valid_from', label: '生效章', num: true }, { k: 'secret', label: '私密', bool: true }],
  rules: [{ k: 'name', label: '规则名' }, { k: 'category', label: '类别' }, { k: 'source', label: '源头' }, { k: 'cost', label: '代价', area: true }, { k: 'note', label: '备注', area: true }],
  factions: [{ k: 'name', label: '势力名' }, { k: 'ideology', label: '意识形态', area: true }, { k: 'leader', label: '领袖' }, { k: 'public_face', label: '公开面目', area: true }, { k: 'private_operation', label: '私下运作', area: true }],
  items: [{ k: 'name', label: '物品名' }, { k: 'category', label: '类别' }, { k: 'description', label: '描述', area: true }, { k: 'symbolic_state', label: '状态' }, { k: 'current_owner', label: '持有者' }],
  terms: [{ k: 'name', label: '术语名' }, { k: 'category', label: '类别' }, { k: 'definition', label: '定义', area: true }],
  promises: [{ k: 'text', label: '伏笔内容', area: true }, { k: 'setup_chapter', label: '埋于第几章', num: true }, { k: 'promise_kind', label: '类型' }],
  motifs: [{ k: 'name', label: '母题名' }, { k: 'theme', label: '绑定主题' }, { k: 'unfolding', label: '隐喻展开', area: true }, { k: 'echoes', label: '物质回声', area: true }],
}
const localOf = (row) => (row.id || '').includes(':') ? row.id.split(':').slice(1).join(':') : row.id

// 原地编辑表单(嵌入在列表项中,非弹窗)
function InlineForm({ type, row, onSave, onCancel }) {
  const fields = FIELDS[type] || []
  const [form, setForm] = useState(() => {
    const f = {}
    fields.forEach((fl) => { f[fl.k] = row ? (row[fl.k] ?? (fl.bool ? false : fl.num ? 1 : '')) : (fl.bool ? false : fl.num ? 1 : '') })
    return f
  })
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const save = async () => {
    if (type === 'chars') row ? await api.editChar(localOf(row), form) : await api.addChar(form)
    else if (type === 'facts') row ? await api.editFact(localOf(row), form) : await api.addFact(form)
    else if (type === 'rules') await api.post('/world-rules', form)
    else if (type === 'factions') await api.post('/factions', form)
    else if (type === 'items') await api.post('/items', form)
    else if (type === 'terms') await api.post('/terms', form)
    else if (type === 'promises') row ? await api.editPromise(row.id, form) : await api.addPromiseNew(form)
    else if (type === 'motifs') row ? await api.editMotif(row.id, form) : await api.addMotifNew(form)
    onSave()
  }
  const inputCls = 'w-full h-8 rounded-md border border-line bg-canvas px-2 text-[12px] text-ink outline-none focus:border-brand'
  const areaCls = 'w-full rounded-md border border-line bg-canvas px-2 py-1.5 text-[12px] text-ink outline-none focus:border-brand resize-y'
  return (
    <div className="p-3 border-2 border-brand/30 rounded-xl bg-brand/[0.02] space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-faint">{row ? '编辑' : '新建'}·{type}</span>
        <div className="flex items-center gap-1">
          <button onClick={save} className="inline-flex items-center gap-1 px-3 h-7 rounded-lg text-[12px] bg-brand text-white font-medium hover:bg-brand/90 cursor-pointer"><Check size={13}/>保存</button>
          <button onClick={onCancel} className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><Undo2 size={13}/></button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {fields.filter((f) => !f.area).map((fl) => (
          <div key={fl.k} className="flex items-center gap-2">
            <span className="text-[11px] text-faint shrink-0 min-w-[48px]">{fl.label}</span>
            {fl.bool ? (
              <button onClick={() => set(fl.k, !form[fl.k])} className={`inline-flex items-center gap-1 text-[12px] cursor-pointer ${form[fl.k] ? 'text-secret' : 'text-faint'}`}>
                <span className={`w-3.5 h-3.5 rounded border ${form[fl.k] ? 'bg-secret border-secret' : 'border-line'}`} />{form[fl.k] ? '是' : '否'}
              </button>
            ) : fl.num ? (
              <input type="number" value={form[fl.k]} onChange={(e) => set(fl.k, Number(e.target.value))} className={inputCls} />
            ) : (
              <input type="text" value={form[fl.k]} onChange={(e) => set(fl.k, e.target.value)} className={inputCls} />
            )}
          </div>
        ))}
      </div>
      {fields.filter((f) => f.area).map((fl) => (
        <div key={fl.k}>
          <span className="text-[11px] text-faint">{fl.label}</span>
          <textarea value={form[fl.k] || ''} onChange={(e) => set(fl.k, e.target.value)} rows={3} className={areaCls} />
        </div>
      ))}
    </div>
  )
}

const Th = ({ children, w }) => <th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase tracking-wider" style={{ width: w }}>{children}</th>
const rowCls = 'group border-b border-line/60 hover:bg-soft/40 transition-colors'

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

function TimelineView({ chars }) {
  return <div className="space-y-4">{chars.map((c) => <TimelineCard key={c.id} char={c} />)}</div>
}

export function CodexView() {
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState({ chars: [], facts: [], rules: [], factions: [], items: [], terms: [], places: [], promises: [], motifs: [], completeness: null, relations: [] })
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState(null)

  const reload = () => {
    api.entities().then((es) => {
      setData((d) => ({ ...d, chars: es.filter((e) => e.kind === 'character'), places: es.filter((e) => e.kind === 'place') }))
    })
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

  const remove = async (type, row) => {
    if (!window.confirm('确认删除?不可撤销。')) return
    if (type === 'chars') await api.delChar(localOf(row))
    else if (type === 'facts') await api.delFact(localOf(row))
    else if (type === 'rules') await api.del(`/world-rules?name=${encodeURIComponent(row.name)}`)
    else if (type === 'factions') await api.del(`/factions?name=${encodeURIComponent(row.name)}`)
    else if (type === 'items') await api.del(`/items?name=${encodeURIComponent(row.name)}`)
    else if (type === 'terms') await api.del(`/terms?name=${encodeURIComponent(row.name)}`)
    else if (type === 'promises') await api.delPromise(row.id)
    else if (type === 'motifs') await api.delMotif(row.id)
    reload()
  }
  const onSaved = () => { setEditing(null); reload() }
  const f = (s) => !q.trim() || (s || '').includes(q.trim())

  // isEditing(type, row) 检查某行/卡片是否在编辑模式
  const isEditing = (type, row) => editing && editing.type === type && editing.row === row
  // isNew(type) 检查是否在新建模式(row=null)
  const isNew = (type) => editing && editing.type === type && editing.row === null

  const Act = ({ type, row }) => (
    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
      <button onClick={() => setEditing({ type, row })} className="w-6 h-6 rounded text-faint hover:text-brand hover:bg-brand/10 inline-flex items-center justify-center cursor-pointer"><Pencil size={12} /></button>
      <button onClick={() => remove(type, row)} className="w-6 h-6 rounded text-faint hover:text-danger hover:bg-danger/10 inline-flex items-center justify-center cursor-pointer"><Trash2 size={12} /></button>
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-1 px-3">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => { setTab(t.key); setEditing(null) }}
            className={`inline-flex items-center gap-1.5 px-3 h-8 rounded-lg text-[13px] transition-colors cursor-pointer ${tab === t.key ? 'bg-soft text-ink font-medium' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <t.icon size={14} />{t.label}{t.key === 'overview' ? '' : <span className="text-faint tnum">{data[t.key]?.length || 0}</span>}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 h-8 rounded-lg border border-line bg-canvas px-2.5 w-48">
            <Search size={14} className="text-faint" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索…" className="flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint/60" />
          </div>
          {['overview','timeline','relations'].indexOf(tab) < 0 && (
            <Btn variant="primary" size="sm" onClick={() => setEditing({ type: tab, row: null })}><Plus size={14} />新建</Btn>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">

          {/* ===== 概览 ===== */}
          {tab === 'overview' && data.completeness && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-[28px] font-bold text-ink">{data.completeness.completeness_score}</span>
                <span className="text-[14px] text-faint">设定完整度 / 100</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ['角色', data.completeness.total_chars, Users], ['世界规则', data.completeness.total_rules, Shield],
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

          {/* ===== 角色(卡片+行内编辑) ===== */}
          {tab === 'chars' && (
            <div className="space-y-3">
              {isNew('chars') && <InlineForm type="chars" row={null} onSave={onSaved} onCancel={() => setEditing(null)} />}
              {data.chars.filter((c) => f(c.name)).map((c) =>
                isEditing('chars', c) ? (
                  <InlineForm key={c.id} type="chars" row={c} onSave={onSaved} onCancel={() => setEditing(null)} />
                ) : (
                  <div key={c.id} className="rounded-2xl border border-line bg-surface p-4 group">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[16px] font-semibold text-ink prose-serif">{c.name}</span>
                          {c.importance && <Tag tone={c.importance === 'protagonist' ? 'fore' : c.importance === 'major' ? 'fore' : 'faint'}>{c.importance}</Tag>}
                          {c.first_appearance && <span className="text-[11px] text-faint">第{c.first_appearance}章出场</span>}
                        </div>
                        {c.surface_goal && <div className="text-[13px] text-fore mt-1">{c.surface_goal}</div>}
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => setEditing({ type: 'chars', row: c })} className="w-6 h-6 rounded text-faint hover:text-brand hover:bg-brand/10 inline-flex items-center justify-center cursor-pointer"><Pencil size={12} /></button>
                        <button onClick={() => remove('chars', c)} className="w-6 h-6 rounded text-faint hover:text-danger hover:bg-danger/10 inline-flex items-center justify-center cursor-pointer"><Trash2 size={12} /></button>
                      </div>
                    </div>
                    {c.appearance && <div className="mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">外貌</span><div className="text-[13px] text-ink leading-relaxed">{c.appearance}</div></div>}
                    {c.personality_tags?.length > 0 && <div className="flex items-center gap-1.5 mb-2 flex-wrap">{c.personality_tags.map((t) => <Tag key={t} tone="fore">{t}</Tag>)}</div>}
                    {c.personality_detail && <div className="mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">性格深描</span><div className="text-[13px] text-ink leading-relaxed">{c.personality_detail}</div></div>}
                    {c.backstory && <div className="mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">前史</span><div className="text-[13px] text-faint leading-relaxed">{c.backstory}</div></div>}
                    {c.abilities && <div className="mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">能力</span><div className="text-[13px] text-faint leading-relaxed">{c.abilities}</div></div>}
                    {c.weaknesses?.length > 0 && <div className="mb-2"><span className="text-[11px] text-faint uppercase tracking-wider">弱点</span><div className="flex items-center gap-1 flex-wrap">{c.weaknesses.map((w, i) => <span key={i} className="text-[12px] text-secret bg-secret/10 px-2 py-0.5 rounded">{w}</span>)}</div></div>}
                    {(c.deep_need || c.internal_conflict || c.fear) && (
                      <div className="mt-2 pt-2 border-t border-line/60">
                        <span className="text-[11px] text-faint uppercase tracking-wider">动机与冲突</span>
                        {c.deep_need && <div className="text-[12px] text-faint">深层需求: {c.deep_need}</div>}
                        {c.internal_conflict && <div className="text-[12px] text-faint">内在冲突: {c.internal_conflict}</div>}
                        {c.fear && <div className="text-[12px] text-faint">恐惧: {c.fear}</div>}
                      </div>
                    )}
                  </div>
                )
              )}
            </div>
          )}

          {/* ===== 表格类(行内编辑) ===== */}
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
                <Th w="72" />
              </tr></thead>
              <tbody>
                {isNew(tab) && (
                  <tr><td colSpan="9" className="p-0"><InlineForm type={tab} row={null} onSave={onSaved} onCancel={() => setEditing(null)} /></td></tr>
                )}
                {(data[tab] || []).filter((x) => f(x.value) || f(x.attribute) || f(x.text) || f(x.name) || f(x.category)).map((x) => (
                  isEditing(tab, x) ? <tr key={x.id || x.name}><td colSpan="9" className="p-0"><InlineForm type={tab} row={x} onSave={onSaved} onCancel={() => setEditing(null)} /></td></tr> :
                    <tr key={x.id || x.name} className={rowCls}>
                      {tab === 'facts' && <><td className="px-3 py-2.5 text-faint">{x.entity}</td><td className="px-3 py-2.5 text-ink">{x.attribute}</td><td className="px-3 py-2.5 text-ink">{x.value}</td><td className="px-3 py-2.5">{x.secret && <Lock size={13} className="text-secret" />}</td></>}
                      {tab === 'rules' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5"><Tag tone="fore">{x.category}</Tag></td><td className="px-3 py-2.5 text-faint">{x.cost || '—'}</td></>}
                      {tab === 'factions' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.ideology || '—'}</td><td className="px-3 py-2.5 text-ink">{x.leader || '—'}</td></>}
                      {tab === 'items' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.category || '—'}</td><td className="px-3 py-2.5"><Tag tone={x.symbolic_state==='active'?'ok':x.symbolic_state==='lost'?'fore':'faint'}>{x.symbolic_state}</Tag></td><td className="px-3 py-2.5 text-faint">{(x.description || '—').slice(0,40)}</td></>}
                      {tab === 'terms' && <><td className="px-3 py-2.5 font-medium text-ink">{x.name}</td><td className="px-3 py-2.5 text-faint">{x.category || '—'}</td><td className="px-3 py-2.5 text-faint">{x.definition || '—'}</td></>}
                      {tab === 'promises' && <><td className="px-3 py-2.5 text-ink">{x.text}</td><td className="px-3 py-2.5 text-faint tnum">第{x.setup_chapter}章</td><td className="px-3 py-2.5">{x.status === 'open' ? <Tag tone="fore">未回收</Tag> : <Tag tone="ok">已回收</Tag>}</td></>}
                      {tab === 'motifs' && <><td className="px-3 py-2.5 font-medium text-ink prose-serif text-[14px]">{x.name}</td><td className="px-3 py-2.5 text-fore">{x.theme}</td><td className="px-3 py-2.5 text-faint">{x.unfolding}</td></>}
                      <td className="px-2 w-[72px]"><Act type={tab} row={x} /></td>
                    </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* ===== 弧光 ===== */}
          {tab === 'timeline' && <TimelineView chars={data.chars.filter((c) => f(c.name))} />}

          {/* ===== 关系 ===== */}
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
