import { useEffect, useState } from 'react'
import { BookOpen, Drama, Eye, FileSearch, Lock } from 'lucide-react'
import { api } from './api'
import { Empty } from './ui'
import { useSelection } from './selectionContext'

// 块三:帧行(知识帧/戏剧反讽的一条事实)→ 通用 focus。value 为 null 即私密(面板本身就打码)。
function factFocus(f, irony) {
  const secret = f.value == null
  const label = `${f.entity ? f.entity + '·' : ''}${f.attribute}${secret ? '' : ':' + f.value}`
  return { type: 'frame_fact', id: String(f.id), label, payload: { secret, irony: !!irony }, origin: 'panel' }
}

const TABS = [
  { key: 'write', label: '可写入正文' },
  { key: 'forbid', label: '禁止泄露' },
  { key: 'irony', label: '戏剧反讽' },
  { key: 'source', label: '来源账本' },
]

function factTitle(f) {
  return `${f.entity ? f.entity + ' · ' : ''}${f.attribute}`
}

function factValue(f) {
  return f.value == null ? '私密/未知' : String(f.value)
}

function Stat({ label, value, tone }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2">
      <div className="text-f10 uppercase tracking-wider text-faint">{label}</div>
      <div className={`mt-0.5 text-f18 font-semibold tnum ${tone || 'text-ink'}`}>{value}</div>
    </div>
  )
}

function FactCard({ fact, tone, icon: Icon, onPick, hint }) {
  return (
    <button type="button" onClick={onPick} title="聚焦此事实"
      className={`w-full text-left rounded-lg border border-line bg-surface px-3 py-2 hover:border-brand/40 hover:bg-soft/40 transition-colors cursor-pointer ${tone || ''}`}>
      <div className="flex items-start gap-2">
        {Icon && <Icon size={14} className="mt-0.5 shrink-0 text-faint" />}
        <div className="min-w-0 flex-1">
          <div className="text-f13 font-medium text-ink leading-snug">{factTitle(fact)}</div>
          <div className="text-f12 text-fore leading-snug break-words">{factValue(fact)}</div>
          {hint && <div className="mt-1 text-f11 text-faint leading-snug">{hint}</div>}
        </div>
      </div>
    </button>
  )
}

// 限知帧:写作决策面板。默认只给作者看“能写什么”,禁写/反讽/来源按需切换。
export function FramePanel({ focalizer, chapter }) {
  const { setFocus } = useSelection()
  const [frame, setFrame] = useState([])
  const [irony, setIrony] = useState([])
  const [active, setActive] = useState('write')
  useEffect(() => {
    if (focalizer) {
      api.frame(focalizer, chapter).then(setFrame).catch(() => setFrame([]))
      api.irony(focalizer, chapter).then(setIrony).catch(() => setIrony([]))
    } else { setFrame([]); setIrony([]) }
  }, [focalizer, chapter])

  const writable = frame.filter((f) => f.value != null)
  const forbidden = frame.filter((f) => f.value == null)
  const sourceRows = [...frame.map((f) => ({ ...f, sourceKind: '知识帧' })), ...irony.map((f) => ({ ...f, sourceKind: '戏剧反讽' }))]
  const renderList = (items, empty, icon, ironyFlag, hint) => (
    items.length === 0 ? <Empty>{empty}</Empty> : (
      <div className="space-y-2">
        {items.map((f) => (
          <FactCard key={f.id} fact={f} icon={icon} onPick={() => setFocus(factFocus(f, ironyFlag))}
            hint={typeof hint === 'function' ? hint(f) : hint} />
        ))}
      </div>
    )
  )

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="shrink-0">
        <div className="flex items-center gap-2 mb-3">
          <Eye size={16} className="text-brand" />
          <div>
            <div className="text-f14 font-semibold text-ink">限知帧</div>
            <div className="text-f11 text-faint">{focalizer ? `当前 POV:${focalizer} · 第 ${chapter} 章` : '作者全知视角'}</div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 mb-3">
          <Stat label="可写事实" value={writable.length} tone="text-ok" />
          <Stat label="禁写风险" value={forbidden.length} tone={forbidden.length ? 'text-danger' : 'text-faint'} />
          <Stat label="反讽张力" value={irony.length} tone={irony.length ? 'text-brand' : 'text-faint'} />
        </div>
        <div className="inline-flex rounded-lg border border-line bg-canvas p-0.5 mb-3">
          {TABS.map((t) => (
            <button key={t.key} type="button" onClick={() => setActive(t.key)}
              className={`h-7 px-2.5 rounded-md text-f12 transition-colors cursor-pointer ${active === t.key ? 'bg-brand text-brandfg' : 'text-faint hover:text-ink'}`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {!focalizer ? <Empty>作者全知视角——暂无限知约束</Empty>
          : active === 'write' ? renderList(writable, '该角色此章暂无可写事实', BookOpen, false, '可从当前 POV 安全写入正文。')
          : active === 'forbid' ? renderList(forbidden, '暂无禁写风险', Lock, false, '当前 POV 不知道；直接写出会造成限知泄露。')
          : active === 'irony' ? renderList(irony, '暂无戏剧反讽', Drama, true, '读者知道、当前 POV 不知道；适合制造悬念和误读。')
          : sourceRows.length === 0 ? <Empty>暂无来源账本</Empty>
          : (
            <div className="space-y-1.5">
              {sourceRows.map((f) => (
                <button key={`${f.sourceKind}:${f.id}`} type="button" onClick={() => setFocus(factFocus(f, f.sourceKind === '戏剧反讽'))}
                  className="w-full text-left rounded-lg border border-line bg-surface px-3 py-2 hover:bg-soft/40 cursor-pointer">
                  <div className="flex items-center gap-2 text-f12">
                    <FileSearch size={13} className="text-faint shrink-0" />
                    <span className="text-faint shrink-0">{f.sourceKind}</span>
                    <span className="text-ink truncate">{factTitle(f)}:{factValue(f)}</span>
                    {f.chapter != null && <span className="ml-auto text-f11 text-faint shrink-0">第 {f.chapter} 章</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  )
}
