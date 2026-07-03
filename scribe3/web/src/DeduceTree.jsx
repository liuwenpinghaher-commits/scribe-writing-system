import { useEffect, useState } from 'react'
import { BookOpen, User, Check, Plus, X, Users } from 'lucide-react'
import { api } from './api'
import { cn } from './lib/utils'
import { useDeduceSel } from './deduceContext'
import { useSelection } from './selectionContext'
import { Empty, SectionTitle } from './ui'

// 演绎树:根「场景真相」+ 涉及角色(已演打勾/未演)。选中驱动中区 DeduceStage。
export function DeduceTree({ seq }) {
  const { selected, setSelected } = useDeduceSel()
  // 块三:演绎目标选中也上通用总线(type:'deduction';主编话术仍走 selContext 演绎分支,不回退块二行为)。
  const { setFocus } = useSelection()
  const pick = (id, name) => {
    setSelected(id)
    setFocus({ type: 'deduction', id, label: name, payload: { seq }, origin: 'deduce' })
  }
  const [ch, setCh] = useState(null)
  const [chars, setChars] = useState([])
  useEffect(() => { if (seq == null) return; api.chapter(seq).then(setCh).catch(() => {}); api.entities().then((es) => setChars(es.filter((e) => e.kind === 'character'))).catch(() => {}) }, [seq])
  // 涉及角色智能预填:章 involved 为空时,按角色名是否出现在大纲/节拍文本里预填一次。
  // 只在 involved 为空时 patch(patch 后非空→条件不再满足,不会无限循环)。
  useEffect(() => {
    if (!ch || (ch.involved_characters || []).length > 0 || chars.length === 0) return
    const text = (ch.synopsis || '') + ' ' + (ch.beats || []).map((b) => b.text || b).join(' ')
    const hit = chars.filter((c) => c.name && text.includes(c.name)).map((c) => c.id)
    if (hit.length) api.patchChapter(seq, { involved_characters: hit }).then(() => api.chapter(seq).then(setCh))
  }, [ch, chars, seq]) // eslint-disable-line
  if (seq == null) return <div className="p-3"><Empty>选一章开始演绎</Empty></div>
  const involved = ch?.involved_characters || []
  const deds = ch?.deductions || []
  const doneSet = new Set(deds.filter((d) => (d.prose || '').trim()).map((d) => d.character_id))
  const involvedChars = chars.filter((c) => involved.includes(c.id))
  const addable = chars.filter((c) => !involved.includes(c.id))
  const setInvolved = async (ids) => { await api.patchChapter(seq, { involved_characters: ids }); api.chapter(seq).then(setCh) }
  return (
    <div className="p-2">
      <button onClick={() => pick('truth', '场景真相')}
        className={cn('w-full flex items-center gap-2 px-2 h-8 rounded-lg text-f13 cursor-pointer', selected === 'truth' ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-soft')}>
        <BookOpen size={14} />场景真相{(ch?.scene_truth || '').trim() && <Check size={12} className="ml-auto text-ok" />}
      </button>
      <div className="mt-3 px-2"><SectionTitle icon={Users}>涉及角色</SectionTitle></div>
      {involvedChars.length === 0 && <div className="px-2"><Empty>暂无涉及角色——下方展开添加 ↓</Empty></div>}
      {involvedChars.map((c) => (
        <div key={c.id} className="group flex items-center">
          <button onClick={() => pick(c.id, c.name)}
            className={cn('flex-1 flex items-center gap-2 px-2 h-8 rounded-lg text-f13 cursor-pointer', selected === c.id ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-soft')}>
            <User size={13} />{c.name}{doneSet.has(c.id) ? <Check size={12} className="ml-auto text-ok" /> : <span className="ml-auto text-f10 text-faint/50">未演</span>}
          </button>
          <button onClick={() => setInvolved(involved.filter((x) => x !== c.id))} title="移除" className="opacity-0 group-hover:opacity-100 w-5 h-5 grid place-items-center text-faint hover:text-danger cursor-pointer"><X size={11} /></button>
        </div>
      ))}
      {addable.length > 0 && (
        <details className="mt-1">
          <summary className="px-2 h-7 flex items-center gap-1 text-f12 text-brand cursor-pointer list-none"><Plus size={12} />添加涉及角色</summary>
          {addable.map((c) => <button key={c.id} onClick={() => setInvolved([...involved, c.id])} className="w-full text-left px-4 h-7 text-f13 text-faint hover:bg-soft hover:text-ink cursor-pointer">{c.name}</button>)}
        </details>
      )}
    </div>
  )
}
