import { useEffect, useState } from 'react'
import { Users, Boxes, Bookmark, Flame, Search, Lock, Plus, Pencil, Trash2, X, Shield, Swords } from 'lucide-react'
import { api } from '../api'
import { Btn, Tag } from '../ui'

const TABS = [
  { key: 'chars', label: '角色', icon: Users },
  { key: 'facts', label: '设定 · 命题', icon: Boxes },
  { key: 'rules', label: '世界规则', icon: Shield },
  { key: 'factions', label: '势力', icon: Swords },
  { key: 'promises', label: '伏笔', icon: Bookmark },
  { key: 'motifs', label: '母题', icon: Flame },
]
const FIELDS = {
  chars: [{ k: 'name', label: '名字' }, { k: 'backstory', label: '前史(冰山·私密)', area: true }],
  facts: [{ k: 'entity', label: '主体(如 role:焦三 / 世界设定)' }, { k: 'attribute', label: '属性' }, { k: 'value', label: '值', area: true }, { k: 'valid_from', label: '生效章', num: true }, { k: 'secret', label: '私密(泄露=穿帮)', bool: true }],
  rules: [{ k: 'name', label: '规则名' }, { k: 'category', label: '类别(magic/technology/social/physical/economic/political)' }, { k: 'source', label: '源头' }, { k: 'cost', label: '代价', area: true }, { k: 'scope', label: '范围(global/regional/faction_specific)' }, { k: 'note', label: '备注', area: true }],
  factions: [{ k: 'name', label: '势力名' }, { k: 'ideology', label: '意识形态', area: true }, { k: 'leader', label: '领袖' }, { k: 'public_face', label: '公开面目', area: true }, { k: 'private_operation', label: '私下运作', area: true }, { k: 'status', label: '状态(active/dissolved/dormant/reformed)' }],
  promises: [{ k: 'text', label: '伏笔内容', area: true }, { k: 'setup_chapter', label: '埋于第几章', num: true }, { k: 'promise_kind', label: '类型(promise/red_herring)' }],
  motifs: [{ k: 'name', label: '母题名' }, { k: 'theme', label: '绑定主题' }, { k: 'unfolding', label: '隐喻展开', area: true }, { k: 'echoes', label: '物质回声', area: true }],
}
const localOf = (row) => (row.id || '').includes(':') ? row.id.split(':').slice(1).join(':') : row.id

function Editor({ type, row, onClose, onSaved }) {
  const fields = FIELDS[type]
  const [form, setForm] = useState(() => {
    const f = {}
    fields.forEach((fl) => { f[fl.k] = row ? (row[fl.k] ?? (fl.bool ? false : fl.num ? 1 : '')) : (fl.bool ? false : fl.num ? 1 : (fl.k === 'kind' ? 'promise' : '')) })
    return f
  })
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const save = async () => {
    if (type === 'chars') row ? await api.editChar(localOf(row), form) : await api.addChar(form)
    else if (type === 'facts') row ? await api.editFact(localOf(row), form) : await api.addFact(form)
    else if (type === 'promises') row ? await api.editPromise(row.id, form) : await api.addPromiseNew(form)
    else if (type === 'motifs') row ? await api.editMotif(row.id, form) : await api.addMotifNew(form)
    onSaved()
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center h-12 px-4 border-b border-line">
          <span className="text-[14px] font-semibold text-ink">{row ? '编辑' : '新建'} · {TABS.find((t) => t.key === type).label}</span>
          <button onClick={onClose} className="ml-auto w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><X size={16} /></button>
        </div>
        <div className="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
          {fields.map((fl) => (
            <div key={fl.k}>
              <label className="block text-[12px] text-faint mb-1">{fl.label}</label>
              {fl.bool ? (
                <button onClick={() => set(fl.k, !form[fl.k])} className={`inline-flex items-center gap-2 text-[13px] cursor-pointer ${form[fl.k] ? 'text-secret' : 'text-faint'}`}>
                  <span className={`w-4 h-4 rounded border ${form[fl.k] ? 'bg-secret border-secret' : 'border-line'}`} />{form[fl.k] ? '是' : '否'}
                </button>
              ) : fl.area ? (
                <textarea value={form[fl.k]} onChange={(e) => set(fl.k, e.target.value)} rows={3}
                  className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-[13px] text-ink outline-none focus:border-brand resize-y" />
              ) : (
                <input type={fl.num ? 'number' : 'text'} value={form[fl.k]} onChange={(e) => set(fl.k, fl.num ? Number(e.target.value) : e.target.value)}
                  className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-[13px] text-ink outline-none focus:border-brand" />
              )}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-end gap-2 h-14 px-4 border-t border-line">
          <Btn variant="ghost" onClick={onClose}>取消</Btn>
          <Btn variant="primary" onClick={save}>保存</Btn>
        </div>
      </div>
    </div>
  )
}

export function CodexView() {
  const [tab, setTab] = useState('chars')
  const [data, setData] = useState({ chars: [], facts: [], rules: [], factions: [], promises: [], motifs: [] })
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState(null)   // {type,row}

  const reload = () => {
    api.entities().then((es) => setData((d) => ({ ...d, chars: es.filter((e) => e.kind === 'character') })))
    api.facts(99999).then((f) => setData((d) => ({ ...d, facts: f })))
    api.get('/world-rules').then((r) => r.json()).then((r) => setData((d) => ({ ...d, rules: r || [] }))).catch(() => {})
    api.get('/factions').then((r) => r.json()).then((r) => setData((d) => ({ ...d, factions: r || [] }))).catch(() => {})
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
    else if (type === 'promises') await api.delPromise(row.id)
    else if (type === 'motifs') await api.delMotif(row.id)
    reload()
  }
  const onSaved = () => { setEditing(null); reload() }

  const f = (s) => !q.trim() || (s || '').includes(q.trim())
  const Th = ({ children, w }) => <th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase tracking-wider" style={{ width: w }}>{children}</th>
  const rowCls = 'group border-b border-line/60 hover:bg-soft/40 transition-colors'
  const Act = ({ type, row }) => (
    <td className="px-2 w-16">
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={() => setEditing({ type, row })} className="w-6 h-6 rounded text-faint hover:text-brand hover:bg-brand/10 inline-flex items-center justify-center cursor-pointer"><Pencil size={12} /></button>
        <button onClick={() => remove(type, row)} className="w-6 h-6 rounded text-faint hover:text-danger hover:bg-danger/10 inline-flex items-center justify-center cursor-pointer"><Trash2 size={12} /></button>
      </div>
    </td>
  )

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-1 px-3">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 px-3 h-8 rounded-lg text-[13px] transition-colors cursor-pointer ${tab === t.key ? 'bg-soft text-ink font-medium' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <t.icon size={14} />{t.label}<span className="text-faint tnum">{data[t.key]?.length || 0}</span>
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1.5 h-8 rounded-lg border border-line bg-canvas px-2.5 w-48">
            <Search size={14} className="text-faint" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索…" className="flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint/60" />
          </div>
          <Btn variant="primary" size="sm" onClick={() => setEditing({ type: tab, row: null })}><Plus size={14} />新建</Btn>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">
          {tab === 'chars' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th w="34%">角色</Th><Th>前史(冰山)</Th><Th w="64" /></tr></thead>
              <tbody>{data.chars.filter((c) => f(c.name)).map((c) => (
                <tr key={c.id} className={rowCls}><td className="px-3 py-2.5 font-medium text-ink prose-serif text-[14px]">{c.name}</td><td className="px-3 py-2.5 text-faint align-top">{c.backstory || <span className="text-faint/50">—</span>}</td><Act type="chars" row={c} /></tr>
              ))}</tbody></table>
          )}
          {tab === 'facts' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th w="20%">主体</Th><Th w="18%">属性</Th><Th>值</Th><Th w="8%">私密</Th><Th w="64" /></tr></thead>
              <tbody>{data.facts.filter((x) => f(x.value) || f(x.attribute)).map((x) => (
                <tr key={x.id} className={rowCls}><td className="px-3 py-2.5 text-faint">{x.entity}</td><td className="px-3 py-2.5 text-ink">{x.attribute}</td><td className="px-3 py-2.5 text-ink">{x.value}</td><td className="px-3 py-2.5">{x.secret && <Lock size={13} className="text-secret" />}</td><Act type="facts" row={x} /></tr>
              ))}</tbody></table>
          )}
          {tab === 'rules' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th w="22%">规则</Th><Th w="14%">类别</Th><Th>代价</Th><Th w="64" /></tr></thead>
              <tbody>{(data.rules || []).filter((r) => f(r.name) || f(r.category)).map((r) => (
                <tr key={r.name} className={rowCls}><td className="px-3 py-2.5 font-medium text-ink">{r.name}</td><td className="px-3 py-2.5"><Tag tone="fore">{r.category}</Tag></td><td className="px-3 py-2.5 text-faint">{r.cost || '—'}</td><Act type="rules" row={r} /></tr>
              ))}</tbody></table>
          )}
          {tab === 'factions' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th w="20%">势力</Th><Th w="24%">意识形态</Th><Th>领袖</Th><Th w="64" /></tr></thead>
              <tbody>{(data.factions || []).filter((fc) => f(fc.name)).map((fc) => (
                <tr key={fc.name} className={rowCls}><td className="px-3 py-2.5 font-medium text-ink">{fc.name}</td><td className="px-3 py-2.5 text-faint">{fc.ideology || '—'}</td><td className="px-3 py-2.5 text-ink">{fc.leader || '—'}</td><Act type="factions" row={fc} /></tr>
              ))}</tbody></table>
          )}
          {tab === 'promises' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th>伏笔</Th><Th w="12%">埋于</Th><Th w="14%">状态</Th><Th w="64" /></tr></thead>
              <tbody>{data.promises.filter((p) => f(p.text)).map((p) => (
                <tr key={p.id} className={rowCls}><td className="px-3 py-2.5 text-ink">{p.text}</td><td className="px-3 py-2.5 text-faint tnum">第{p.setup_chapter}章</td><td className="px-3 py-2.5">{p.status === 'open' ? <Tag tone="fore">未回收</Tag> : <Tag tone="ok">已回收</Tag>}</td><Act type="promises" row={p} /></tr>
              ))}</tbody></table>
          )}
          {tab === 'motifs' && (
            <table className="w-full text-[13px] border-collapse"><thead><tr><Th w="20%">母题</Th><Th w="28%">绑定主题</Th><Th>隐喻展开</Th><Th w="64" /></tr></thead>
              <tbody>{data.motifs.filter((m) => f(m.name)).map((m) => (
                <tr key={m.id} className={rowCls}><td className="px-3 py-2.5 font-medium text-ink prose-serif text-[14px]">{m.name}</td><td className="px-3 py-2.5 text-fore">{m.theme}</td><td className="px-3 py-2.5 text-faint">{m.unfolding}</td><Act type="motifs" row={m} /></tr>
              ))}</tbody></table>
          )}
        </div>
      </div>

      {editing && <Editor type={editing.type} row={editing.row} onClose={() => setEditing(null)} onSaved={onSaved} />}
    </div>
  )
}
