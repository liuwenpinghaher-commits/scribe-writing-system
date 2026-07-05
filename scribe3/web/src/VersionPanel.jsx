import { useEffect, useState } from 'react'
import { api } from './api'
import { Empty } from './ui'

// 存档点历史(改造④):作者命名里程碑;回看只读 + 恢复。
export function VersionPanel({ seq, refreshKey, onRestore }) {
  const [list, setList] = useState([])
  const [view, setView] = useState(null)   // 正在回看的版本全文
  useEffect(() => { api.chapterVersions(seq).then(setList).catch(() => setList([])) }, [seq, refreshKey])
  return (
    <div>
      {list.length === 0 ? <Empty>还没有存档点。写到满意时点顶部「存档点」。</Empty> : (
        <ul className="space-y-1.5">
          {list.map((v) => (
            <li key={v.id} className="rounded-lg border border-line bg-canvas px-2.5 py-2">
              <div className="flex items-center gap-2">
                <span className="text-f12 text-ink font-medium">{v.label || (v.kind === 'final' ? '定稿' : '存档')}</span>
                {v.kind === 'final' && <span className="text-f10 text-brand">定稿</span>}
                <button onClick={() => api.chapterVersion(v.id).then(setView)} className="ml-auto text-f11 text-faint hover:text-ink cursor-pointer">回看</button>
              </div>
              {(() => {
                // v.qc.repetition / .purple 可能是检测器数组([{phrase,count}]/[{phrase,kind}])或数字——统一成计数,
                // 否则把对象当 React 子节点渲染会崩(整个面板白屏)。
                const cnt = (x) => Array.isArray(x) ? x.length : (x || 0)
                const rep = cnt(v.qc?.repetition), pur = cnt(v.qc?.purple)
                // 断头修复#16:stats/summary 后端一直落库(_prose_stats),此前 UI 不消费
                const s = v.stats || {}
                const bits = [
                  s.words ? `${s.words}字` : null,
                  s.avg_sentence ? `句长${s.avg_sentence}` : null,
                  s.dialog_count != null && s.words ? `对白${s.dialog_count}` : null,
                  (rep || pur) ? `QC 复读${rep}·升华${pur}` : null,
                ].filter(Boolean)
                return (
                  <>
                    {bits.length > 0 && <div className="text-f10 text-faint mt-0.5">{bits.join(' · ')}</div>}
                    {v.summary && <div className="text-f10 text-faint/80 mt-0.5 truncate">{v.summary}</div>}
                  </>
                )
              })()}
            </li>
          ))}
        </ul>
      )}
      {view && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center z-50" onClick={() => setView(null)}>
          <div className="bg-surface rounded-xl max-w-[680px] w-[90vw] max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-4 h-11 border-b border-line">
              <span className="text-f13 text-ink">{view.label || '存档'}</span>
              <button onClick={() => { onRestore?.(view.prose); setView(null) }} className="ml-auto text-f12 text-brand hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">恢复到此版本</button>
              <button onClick={() => setView(null)} className="text-f12 text-faint hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">关闭</button>
            </div>
            <div className="manuscript px-5 py-4 overflow-y-auto whitespace-pre-wrap text-f15 leading-[1.85] text-ink">{view.prose}</div>
          </div>
        </div>
      )}
    </div>
  )
}
