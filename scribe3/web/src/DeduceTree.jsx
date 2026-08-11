import { useEffect, useState } from 'react'
import { BookOpen, User, Check, Plus, X, Users } from 'lucide-react'
import { api } from './api'
import { cn } from './lib/utils'
import { useDeduceSel } from './deduceContext'
import { useSelection } from './selectionContext'
import { Empty, SectionTitle } from './ui'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'
import { isStaleDeduction, normalizeRoleId, truthRevision } from './lib/deduceGate.js'
import { liveTouchesChapter, liveTouchesTable } from './lib/liveRefresh.js'

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
  const [inferredInvolved, setInferredInvolved] = useState([])
  const [syncingInferred, setSyncingInferred] = useState(false)
  const [syncError, setSyncError] = useState('')
  useEffect(() => {
    if (seq == null) return undefined
    let ignore = false
    const pullCh = () => api.chapter(seq).then((c) => { if (!ignore) setCh(c) }).catch(() => {})
    const pullChars = () => api.entities().then((es) => {
      if (!ignore) setChars((Array.isArray(es) ? es : []).filter((e) => e.kind === 'character'))
    }).catch(() => {})
    pullCh()
    pullChars()
    // S-8: 本章 chapter 或角色表变更才刷新演绎树
    const onLive = (e) => {
      const d = e?.detail || {}
      if (liveTouchesTable(d, ['character', 'entity'])) pullChars()
      if (liveTouchesChapter(d, seq)) pullCh()
    }
    window.addEventListener('s3-live', onLive)
    return () => { ignore = true; window.removeEventListener('s3-live', onLive) }
  }, [seq])
  // 涉及角色智能建议:查看演绎树必须只读,只给出本地建议;写入必须由用户点击确认。
  useEffect(() => {
    if (!ch || (ch.involved_characters || []).length > 0 || chars.length === 0) {
      setInferredInvolved([])
      setSyncError('')
      return
    }
    const text = [
      ch.title || '',
      ch.synopsis || '',
      (ch.beats || []).map((b) => b.text || b).join(' '),
      ch.scene_truth || '',
    ].join(' ')
    const hit = chars.filter((c) => c.name && text.includes(c.name)).map((c) => c.id)
    setInferredInvolved(hit)
    setSyncError('')
  }, [ch, chars, seq]) // eslint-disable-line
  if (seq == null) return <div className="p-3"><Empty>选一章开始演绎</Empty></div>
  const involved = (ch?.involved_characters || []).map(normalizeRoleId).filter(Boolean)
  const deds = ch?.deductions || []
  const rev = truthRevision(ch)
  const doneSet = new Set(
    deds.filter((d) => (d.prose || '').trim()).map((d) => normalizeRoleId(d.character_id)),
  )
  const staleSet = new Set(
    deds
      .filter((d) => (d.prose || '').trim() && isStaleDeduction(d, rev))
      .map((d) => normalizeRoleId(d.character_id)),
  )
  const involvedChars = chars.filter((c) => involved.includes(normalizeRoleId(c.id)))
  const addable = chars.filter((c) => !involved.includes(normalizeRoleId(c.id)))
  const nameOf = (id) => chars.find((c) => normalizeRoleId(c.id) === normalizeRoleId(id))?.name || id
  const nameOfId = (id) => chars.find((c) => normalizeRoleId(c.id) === normalizeRoleId(id))?.name || id
  const setInvolved = async (ids) => {
    const names = ids.map((id) => nameOfId(id)).join('、')
    seedChiefNarrativeWrite('deduce', `第 ${seq} 章涉及角色`, `请将 involved_characters 更新为: ${names || '（空）'} (${ids.join(',')})`)
  }
  const syncInferred = async () => {
    if (!inferredInvolved.length || syncingInferred) return
    seedChiefNarrativeWrite(
      'deduce',
      `第 ${seq} 章涉及角色`,
      `请同步建议角色到本章: ${inferredInvolved.map(nameOfId).join('、')} (${inferredInvolved.join(',')})`,
    )
  }
  return (
    <div className="p-2">
      <button onClick={() => pick('truth', '场景真相')}
        className={cn('w-full flex items-center gap-2 px-2 h-8 rounded-lg text-f13 cursor-pointer', selected === 'truth' ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-soft')}>
        <BookOpen size={14} />场景真相{(ch?.scene_truth || '').trim() && <Check size={12} className="ml-auto text-ok" />}
      </button>
      <div className="mt-3 px-2"><SectionTitle icon={Users}>涉及角色</SectionTitle></div>
      {involvedChars.length === 0 && <div className="px-2"><Empty>暂无涉及角色——下方展开添加 ↓</Empty></div>}
      {inferredInvolved.length > 0 && (
        <div role="status" className="mx-2 mb-2 rounded-lg border border-brand/20 bg-brand/5 px-2.5 py-2 text-f12 text-ink">
          <div className="font-medium text-brand">检测到可能涉及角色: {inferredInvolved.map(nameOf).join('、')}</div>
          <div className="mt-0.5 text-faint">确认后由主编审批写入;打开面板本身不会改数据。</div>
          <button
            onClick={syncInferred}
            disabled={syncingInferred}
            className="mt-1.5 h-7 rounded-lg border border-brand/40 bg-canvas px-2 text-f12 text-brand hover:bg-brand/10 disabled:opacity-50 cursor-pointer"
          >
            让主编同步
          </button>
          {syncError && <div role="alert" className="mt-1 text-danger">{syncError}</div>}
        </div>
      )}
      {involvedChars.map((c) => {
        const cid = normalizeRoleId(c.id)
        const status = staleSet.has(cid)
          ? <span data-testid="deduce-stale-badge" className="ml-auto text-warn text-f12">过期</span>
          : doneSet.has(cid)
            ? <Check size={12} className="ml-auto text-ok" />
            : <span className="ml-auto text-meta text-faint/50">未演</span>
        return (
        <div key={c.id} className="group flex items-center">
          <button onClick={() => pick(c.id, c.name)}
            className={cn('flex-1 flex items-center gap-2 px-2 h-8 rounded-lg text-f13 cursor-pointer', selected === c.id || selected === cid ? 'bg-brand/10 text-brand font-medium' : 'text-ink hover:bg-soft')}>
            <User size={13} />{c.name}{status}
          </button>
          <button onClick={() => setInvolved(involved.filter((x) => normalizeRoleId(x) !== cid))} title="移除" className="opacity-0 group-hover:opacity-100 w-5 h-5 grid place-items-center text-faint hover:text-danger cursor-pointer"><X size={11} /></button>
        </div>
        )
      })}
      {addable.length > 0 && (
        <details className="mt-1">
          <summary className="px-2 h-7 flex items-center gap-1 text-f12 text-brand cursor-pointer list-none"><Plus size={12} />添加涉及角色</summary>
          {addable.map((c) => <button key={c.id} onClick={() => setInvolved([...involved, c.id])} className="w-full text-left px-4 h-7 text-f13 text-faint hover:bg-soft hover:text-ink cursor-pointer">{c.name}</button>)}
        </details>
      )}
    </div>
  )
}
