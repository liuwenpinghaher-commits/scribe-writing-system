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
                <span className="text-[12px] text-ink font-medium">{v.label || (v.kind === 'final' ? '定稿' : '存档')}</span>
                {v.kind === 'final' && <span className="text-[10px] text-brand">定稿</span>}
                <button onClick={() => api.chapterVersion(v.id).then(setView)} className="ml-auto text-[11px] text-faint hover:text-ink cursor-pointer">回看</button>
              </div>
              {v.qc && (v.qc.repetition || v.qc.purple) ? <div className="text-[10px] text-faint mt-0.5">QC 复读{v.qc.repetition||0}·升华{v.qc.purple||0}</div> : null}
            </li>
          ))}
        </ul>
      )}
      {view && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center z-50" onClick={() => setView(null)}>
          <div className="bg-surface rounded-xl max-w-[680px] w-[90vw] max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-4 h-11 border-b border-line">
              <span className="text-[13px] text-ink">{view.label || '存档'}</span>
              <button onClick={() => { onRestore?.(view.prose); setView(null) }} className="ml-auto text-[12px] text-brand hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">恢复到此版本</button>
              <button onClick={() => setView(null)} className="text-[12px] text-faint hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">关闭</button>
            </div>
            <div className="manuscript px-5 py-4 overflow-y-auto whitespace-pre-wrap text-[15px] leading-[1.85] text-ink">{view.prose}</div>
          </div>
        </div>
      )}
    </div>
  )
}
