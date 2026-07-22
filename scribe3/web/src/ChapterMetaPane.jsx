import { useEffect, useState } from 'react'
import { api } from './api'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { ReadOnlyText } from './ui/EditableText.jsx'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'

const LABEL_OPTIONS = [
  ['idea', '想法'],
  ['beat', '节拍'],
  ['draft', '草稿'],
  ['revise', '修订'],
  ['done', '完成'],
]

// 章节标题/标签/归属卷:只读 + 主编种子(禁止 patchChapter 叙事直写)。
export function ChapterMetaPane({ seq, work, onClose }) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [volumes, setVolumes] = useState([])
  const [title, setTitle] = useState('')
  const [label, setLabel] = useState('')
  const [volume, setVolume] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all([api.chapter(seq, work), api.listVolumes()])
      .then(([chapter, rows]) => {
        if (!alive) return
        setTitle(chapter?.title || '')
        setLabel(chapter?.label || '')
        setVolume(chapter?.volume || '')
        setVolumes(Array.isArray(rows) ? rows : [])
      })
      .catch((e) => {
        if (alive) toast(e?.body?.detail || e?.message || '章节信息加载失败', { tone: 'danger' })
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [seq, work])

  const volTitle = volumes.find((v) => String(v.id) === String(volume))?.title || volume || '未分卷'
  const labelText = LABEL_OPTIONS.find(([v]) => v === label)?.[1] || label || '未标记'

  const askChief = () => seedChiefNarrativeWrite(
    'chapter-meta',
    `第 ${seq} 章信息`,
    `请更新第 ${seq} 章 title/label/volume。当前: title=${title || '（空）'}; label=${label || '（空）'}; volume=${volume || '（空）'}。`,
  )

  if (loading) return <div className="p-5 text-f13 text-faint">加载章节信息…</div>

  return (
    <div className="w-full max-w-[42rem] mx-auto px-5 py-5" data-testid="chapter-meta-pane">
      <div className="flex items-start justify-between gap-3 mb-5">
        <div>
          <h3 className="text-f20 font-semibold text-ink">章节信息</h3>
          <p className="mt-1 text-f13 text-faint">只读检视;命名/标签/分卷由主编审批写入。</p>
        </div>
        <Btn variant="ghost" size="sm" onClick={onClose}>返回写作</Btn>
      </div>
      <div className="space-y-4">
        <ReadOnlyText label="章节标题" value={title} emptyHint="（空 · 由主编审批写入）" />
        <ReadOnlyText label="章节标签" value={labelText} />
        <ReadOnlyText label="所属卷" value={volTitle} />
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Btn variant="ghost" onClick={onClose}>关闭</Btn>
        <Btn variant="primary" data-testid="chapter-meta-ask-chief" onClick={askChief}>让主编写入章节信息</Btn>
      </div>
    </div>
  )
}
