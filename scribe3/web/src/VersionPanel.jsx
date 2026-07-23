import { useEffect, useState } from 'react'
import { api } from './api'
import { Empty } from './ui'
import { AsyncState } from './ui/AsyncState.jsx'

// 存档点历史(改造④):作者命名里程碑;回看只读 + 恢复 + R1-6 多选并排对比(needs_human 三稿裁决)。
export function VersionPanel({ seq, refreshKey, onRestore }) {
  // Task 8:undefined=加载中,null=拉取失败,array=数据——此前 catch 落空数组,
  // 失败被谎报成「还没有存档点」(与收件箱 badge 同型的可见状态谎报);现走 AsyncState 如实呈现。
  const [list, setList] = useState(undefined)
  const [retryTick, setRetryTick] = useState(0)   // 错误重试:bump 重跑同一拉取,不改 API 调用
  const [view, setView] = useState(null)   // 正在回看的版本全文
  const [compare, setCompare] = useState([])   // R1-6:并排对比集合 [{id,label,prose}]
  const [showCompare, setShowCompare] = useState(false)
  useEffect(() => {
    setList(undefined)
    api.chapterVersions(seq).then((l) => setList(Array.isArray(l) ? l : [])).catch(() => setList(null))
  }, [seq, refreshKey, retryTick])
  useEffect(() => { setCompare([]); setShowCompare(false) }, [seq])   // 切章清空对比集
  // children 在 JSX 构造期即求值(AsyncState 只是选择性渲染),加载/失败期以空数组兜底防 .map 崩
  const rows = Array.isArray(list) ? list : []
  const inCompare = (id) => compare.some((c) => c.id === id)
  const toggleCompare = (v) => {
    if (inCompare(v.id)) { setCompare((cs) => cs.filter((c) => c.id !== v.id)); return }
    // 拉全稿入对比集(复用留版,不重烧);needs_human 三稿全在版本库,选中即可并排裁决
    api.chapterVersion(v.id).then((full) => setCompare((cs) => cs.length >= 4 ? cs
      : [...cs, { id: v.id, label: v.label || (v.kind === 'final' ? '定稿' : '存档'), prose: full?.prose || '' }])).catch(() => {})
  }
  return (
    <AsyncState
      state={list === undefined ? 'loading' : list === null ? 'error' : 'ready'}
      title={list === null ? '存档列表加载失败' : '加载存档'}
      message={list === null ? '这不代表没有存档点(可能后端/网络异常)。' : undefined}
      onRetry={() => setRetryTick((t) => t + 1)}>
    <div>
      {rows.length === 0 ? <Empty>还没有存档点。写到满意时点顶部「存档点」。</Empty> : (
        <ul className="space-y-1.5">
          {rows.map((v) => (
            <li key={v.id} className={`rounded-lg border bg-canvas px-2.5 py-2 ${inCompare(v.id) ? 'border-brand' : 'border-line'}`}>
              <div className="flex items-center gap-2">
                <span className="text-f12 text-ink font-medium">{v.label || (v.kind === 'final' ? '定稿' : '存档')}</span>
                {v.kind === 'final' && <span className="text-meta text-brand">定稿</span>}
                <button onClick={() => toggleCompare(v)} className="ml-auto text-meta text-faint hover:text-ink cursor-pointer">{inCompare(v.id) ? '✓ 对比中' : '+ 对比'}</button>
                <button onClick={() => api.chapterVersion(v.id).then(setView)} className="text-meta text-faint hover:text-ink cursor-pointer">回看</button>
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
                    {bits.length > 0 && <div className="text-meta text-faint mt-0.5">{bits.join(' · ')}</div>}
                    {v.summary && <div className="text-meta text-faint/80 mt-0.5 truncate">{v.summary}</div>}
                  </>
                )
              })()}
            </li>
          ))}
        </ul>
      )}
      {/* R1-6:选了 ≥2 稿 → 并排对比入口(needs_human 三稿裁决的承载) */}
      {compare.length >= 2 && (
        <div className="sticky bottom-0 mt-2 pt-2 bg-surface border-t border-line">
          <button onClick={() => setShowCompare(true)} className="w-full h-8 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">
            并排对比 {compare.length} 稿 →
          </button>
        </div>
      )}
      {view && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center z-50" onClick={() => setView(null)}>
          <div className="bg-surface rounded-md max-w-[680px] w-[90vw] max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-4 h-11 border-b border-line">
              <span className="text-f13 text-ink">{view.label || '存档'}</span>
              <button onClick={() => { onRestore?.(view.prose); setView(null) }} className="ml-auto text-f12 text-brand hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">恢复到此版本</button>
              <button onClick={() => setView(null)} className="text-f12 text-faint hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">关闭</button>
            </div>
            <div className="manuscript type-stage px-5 py-4 overflow-y-auto whitespace-pre-wrap text-ink">{view.prose}</div>
          </div>
        </div>
      )}
      {/* R1-6:三稿横向并排(每稿一列可滚动),裁决时同屏读全文,「选此稿」直接恢复 */}
      {showCompare && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center z-50" onClick={() => setShowCompare(false)}>
          <div className="bg-surface rounded-md max-w-[95vw] w-[95vw] max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-4 h-11 border-b border-line shrink-0">
              <span className="text-f13 text-ink">并排对比 · {compare.length} 稿</span>
              <button onClick={() => setShowCompare(false)} className="ml-auto text-f12 text-faint hover:bg-soft px-2 h-7 rounded-lg cursor-pointer">关闭</button>
            </div>
            <div className="flex gap-3 overflow-x-auto p-4 min-h-0">
              {compare.map((c) => (
                <div key={c.id} className="w-[360px] shrink-0 flex flex-col border border-line rounded-lg overflow-hidden">
                  <div className="px-3 h-8 flex items-center gap-2 border-b border-line bg-canvas shrink-0">
                    <span className="text-f12 text-ink font-medium truncate">{c.label}</span>
                    <button onClick={() => { onRestore?.(c.prose); setShowCompare(false) }} className="ml-auto text-meta text-brand hover:underline cursor-pointer shrink-0">选此稿</button>
                  </div>
                  <div className="manuscript px-3 py-3 overflow-y-auto whitespace-pre-wrap text-f13 leading-[1.8] text-ink">{c.prose}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
    </AsyncState>
  )
}
