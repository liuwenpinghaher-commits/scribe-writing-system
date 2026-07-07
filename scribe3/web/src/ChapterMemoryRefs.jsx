import { useEffect, useState } from 'react'
import { BookMarked, ChevronDown } from 'lucide-react'
import { api } from './api'

// 反向溯源(正文侧):本章写作参考了哪些素材记忆(material_reference by chapter)。
// 默认收起、无参考则不占位(不打扰);点开看每条的参考维度 + 主编为何参考 + 来源相位。
export function ChapterMemoryRefs({ chapter }) {
  const [refs, setRefs] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (chapter == null) { setRefs([]); return }
    let alive = true
    api.materialRefsByChapter(chapter)
      .then((r) => { if (alive) setRefs(Array.isArray(r) ? r : []) })
      .catch(() => { if (alive) setRefs([]) })
    return () => { alive = false }
  }, [chapter])

  if (!refs.length) return null   // 无参考 → 不显示(不占位、不打扰)

  return (
    <div className="shrink-0 border-b border-line bg-surface/50 px-4 py-1.5">
      <button onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-f11 text-faint hover:text-ink transition-colors cursor-pointer">
        <BookMarked size={12} />
        本章参考了 {refs.length} 条素材记忆
        <ChevronDown size={12} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-1.5 flex flex-col gap-1 pb-1">
          {refs.map((r, i) => (
            <div key={i} className="text-f11 leading-snug pl-4">
              <span className="text-ink">{r.dimension ? `参考${r.dimension}` : '参考'}</span>
              {r.reason && <span className="text-faint">:{r.reason}</span>}
              {r.via && <span className="text-faint/50 ml-1">({r.via})</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
