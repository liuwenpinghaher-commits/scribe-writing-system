import { useEffect, useState } from 'react'
import { Eye, Drama, Target } from 'lucide-react'
import { api } from './api'
import { Empty } from './ui'

// 知识帧 / 戏剧反讽 / 北极星意图(原 DeduceLayout 右面板,迁入写作台左面板)。
export function FramePanel({ focalizer, chapter }) {
  const [frame, setFrame] = useState([])
  const [irony, setIrony] = useState([])
  const [intent, setIntent] = useState({ reader_feeling: '', emotional_arc: '', red_lines: '' })
  const [intentSaved, setIntentSaved] = useState(false)
  useEffect(() => {
    if (focalizer) {
      api.frame(focalizer, chapter).then(setFrame).catch(() => setFrame([]))
      api.irony(focalizer, chapter).then(setIrony).catch(() => setIrony([]))
    } else { setFrame([]); setIrony([]) }
  }, [focalizer, chapter])
  useEffect(() => { api.intent().then(setIntent).catch(() => {}) }, [])
  return (
    <div className="space-y-4">
      <section>
        <div className="flex items-center gap-1.5 text-[12px] font-medium text-ink mb-1.5"><Eye size={14} strokeWidth={1.5} />知识帧</div>
        {!focalizer ? <Empty>作者全知视角——无限知约束</Empty>
          : frame.length === 0 ? <Empty>该角色此章暂无已知事实</Empty>
          : <ul className="space-y-1">{frame.map((f) => (
            <li key={f.id} className="text-[12px] text-ink">
              {f.entity && <span className="text-faint">{f.entity} · </span>}
              <span className="text-faint">{f.attribute}</span>:{f.value == null ? <span className="text-secret">🔒 私密</span> : f.value}
            </li>
          ))}</ul>}
      </section>
      <section>
        <div className="flex items-center gap-1.5 text-[12px] font-medium text-ink mb-1.5"><Drama size={14} strokeWidth={1.5} />戏剧反讽(读者知道,他不知道)</div>
        {!focalizer ? <Empty>切某角色视角后显示</Empty>
          : irony.length === 0 ? <Empty>无</Empty>
          : <ul className="space-y-1">{irony.map((f) => (
            <li key={f.id} className="text-[12px] text-irony">
              {f.entity && <span className="opacity-70">{f.entity} · </span>}
              <span className="opacity-70">{f.attribute}</span>:{f.value == null ? <span className="text-secret">🔒 私密</span> : f.value}
            </li>
          ))}</ul>}
      </section>
      <section>
        <div className="flex items-center gap-1.5 text-[12px] font-medium text-ink mb-1.5"><Target size={14} strokeWidth={1.5} />北极星意图</div>
        {[['reader_feeling', '读者感受'], ['emotional_arc', '主角情感弧'], ['red_lines', '绝不背叛(红线)']].map(([k, label]) => (
          <textarea key={k} value={intent[k] || ''} placeholder={label}
            onChange={(e) => { setIntent((s) => ({ ...s, [k]: e.target.value })); setIntentSaved(false) }}
            className="w-full mb-1.5 rounded-lg border border-line bg-canvas px-2 py-1 text-[12px] text-ink outline-none focus:border-brand" rows={2} />
        ))}
        <button onClick={async () => { await api.putIntent(intent); setIntentSaved(true) }} className="text-[11px] text-brand hover:bg-soft px-2 h-6 rounded-lg cursor-pointer">{intentSaved ? '已存 ✓' : '保存意图'}</button>
      </section>
    </div>
  )
}
