import { useEffect, useState } from 'react'
import { api } from './api'
import { useToast } from './ui/Toast.jsx'
import { Btn, Input } from './ui.jsx'

const LABEL_OPTIONS = [
  ['idea', '想法'],
  ['beat', '节拍'],
  ['draft', '草稿'],
  ['revise', '修订'],
  ['done', '完成'],
]

// 章节标题、标签与归属卷是 chapter 的作者字段。四阶段只覆盖大纲/节拍/演绎/草稿/正文，
// 因此把这三项放在一个轻量的章信息面板中，避免作者只能依赖默认“第 N 章”。
export function ChapterMetaPane({ seq, work, onSaved, onClose }) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
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

  const save = async () => {
    const nextTitle = title.trim()
    if (!nextTitle) {
      toast('章节标题不能为空', { tone: 'danger' })
      return
    }
    setSaving(true)
    try {
      await api.patchChapter(seq, { title: nextTitle, label: label.trim() || null, volume: volume || null }, work)
      toast('章节信息已保存', { tone: 'ok' })
      onSaved?.({ title: nextTitle, label: label.trim(), volume: volume || null })
    } catch (e) {
      toast(e?.body?.detail || e?.message || '章节信息保存失败', { tone: 'danger' })
    } finally { setSaving(false) }
  }

  if (loading) return <div className="p-5 text-f13 text-faint">加载章节信息…</div>

  return (
    <div className="w-full max-w-[42rem] mx-auto px-5 py-5" data-testid="chapter-meta-pane">
      <div className="flex items-start justify-between gap-3 mb-5">
        <div>
          <h3 className="text-f20 font-semibold text-ink">章节信息</h3>
          <p className="mt-1 text-f13 text-faint">命名、标记并把章节归入正确的卷；大纲和正文仍在对应写作阶段编辑。</p>
        </div>
        <Btn variant="ghost" size="sm" onClick={onClose}>返回写作</Btn>
      </div>
      <div className="space-y-4">
        <label className="block text-f13 text-ink">章节标题
          <Input variant="bordered" aria-label="章节标题" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例：闸底刻名" className="mt-1" />
        </label>
        <label className="block text-f13 text-ink">章节标签
          <select aria-label="章节标签" value={label} onChange={(e) => setLabel(e.target.value)}
            className="mt-1 h-9 w-full rounded-lg border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand">
            <option value="">未标记</option>
            {LABEL_OPTIONS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
          </select>
        </label>
        <label className="block text-f13 text-ink">所属卷
          <select aria-label="所属卷" value={volume} onChange={(e) => setVolume(e.target.value)}
            className="mt-1 h-9 w-full rounded-lg border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand">
            <option value="">未分卷</option>
            {volumes.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
          </select>
        </label>
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Btn variant="ghost" onClick={onClose}>取消</Btn>
        <Btn variant="primary" onClick={save} disabled={saving}>{saving ? '保存中…' : '保存章节信息'}</Btn>
      </div>
    </div>
  )
}
