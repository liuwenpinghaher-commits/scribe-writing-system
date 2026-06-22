import { useEffect, useState } from 'react'
import { Users, Boxes, Bookmark, Flame, Search, Lock } from 'lucide-react'
import { api } from '../api'
import { Tag } from '../ui'

// 设定库:角色/设定(命题)/伏笔/母题 分类表(读)。编辑器(EntityEditor)随后补。
const TABS = [
  { key: 'chars', label: '角色', icon: Users },
  { key: 'facts', label: '设定 · 命题', icon: Boxes },
  { key: 'promises', label: '伏笔', icon: Bookmark },
  { key: 'motifs', label: '母题', icon: Flame },
]

export function CodexView() {
  const [tab, setTab] = useState('chars')
  const [chars, setChars] = useState([])
  const [facts, setFacts] = useState([])
  const [promises, setPromises] = useState([])
  const [motifs, setMotifs] = useState([])
  const [q, setQ] = useState('')

  useEffect(() => {
    api.entities().then((es) => setChars(es.filter((e) => e.kind === 'character')))
    api.facts(99999).then(setFacts)
    api.promises().then(setPromises)
    api.motifs().then(setMotifs)
  }, [])

  const f = (s) => !q.trim() || (s || '').includes(q.trim())
  const Th = ({ children, w }) => <th className="text-left font-medium text-faint px-3 py-2 text-[11px] uppercase tracking-wider" style={{ width: w }}>{children}</th>
  const Td = ({ children, className = '' }) => <td className={`px-3 py-2.5 align-top ${className}`}>{children}</td>
  const tableWrap = 'w-full text-[13px] border-collapse'
  const rowCls = 'border-b border-line/60 hover:bg-soft/50 transition-colors'

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-1 px-3">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 px-3 h-8 rounded-lg text-[13px] transition-colors cursor-pointer ${tab === t.key ? 'bg-soft text-ink font-medium' : 'text-faint hover:bg-soft hover:text-ink'}`}>
            <t.icon size={14} />{t.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1.5 h-8 rounded-lg border border-line bg-canvas px-2.5 w-56">
          <Search size={14} className="text-faint" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索…" className="flex-1 bg-transparent text-[13px] outline-none placeholder:text-faint/60" />
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">
          {tab === 'chars' && (
            <table className={tableWrap}><thead><tr><Th w="40%">角色</Th><Th>前史(冰山)</Th></tr></thead>
              <tbody>{chars.filter((c) => f(c.name)).map((c) => (
                <tr key={c.id} className={rowCls}><Td className="font-medium text-ink prose-serif text-[14px]">{c.name}</Td><Td className="text-faint">{c.backstory || <span className="text-faint/50">—</span>}</Td></tr>
              ))}</tbody></table>
          )}
          {tab === 'facts' && (
            <table className={tableWrap}><thead><tr><Th w="22%">主体</Th><Th w="20%">属性</Th><Th>值</Th><Th w="8%">私密</Th></tr></thead>
              <tbody>{facts.filter((x) => f(x.value) || f(x.attribute)).map((x) => (
                <tr key={x.id} className={rowCls}><Td className="text-faint">{x.entity}</Td><Td className="text-ink">{x.attribute}</Td><Td className="text-ink">{x.value}</Td><Td>{x.secret && <Lock size={13} className="text-secret" />}</Td></tr>
              ))}</tbody></table>
          )}
          {tab === 'promises' && (
            <table className={tableWrap}><thead><tr><Th>伏笔</Th><Th w="12%">埋于</Th><Th w="14%">状态</Th></tr></thead>
              <tbody>{promises.filter((p) => f(p.text)).map((p) => (
                <tr key={p.id} className={rowCls}><Td className="text-ink">{p.text}</Td><Td className="text-faint tnum">第{p.setup_chapter}章</Td><Td>{p.status === 'open' ? <Tag tone="fore">未回收</Tag> : <Tag tone="ok">已回收</Tag>}</Td></tr>
              ))}</tbody></table>
          )}
          {tab === 'motifs' && (
            <table className={tableWrap}><thead><tr><Th w="22%">母题</Th><Th w="30%">绑定主题</Th><Th>隐喻展开</Th></tr></thead>
              <tbody>{motifs.filter((m) => f(m.name)).map((m) => (
                <tr key={m.id} className={rowCls}><Td className="font-medium text-ink prose-serif text-[14px]">{m.name}</Td><Td className="text-fore">{m.theme}</Td><Td className="text-faint">{m.unfolding}</Td></tr>
              ))}</tbody></table>
          )}
        </div>
      </div>
    </div>
  )
}
