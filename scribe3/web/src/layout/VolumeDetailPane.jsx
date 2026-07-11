import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { chapterLabel } from '../chapterLabel'
import { wcLabel } from '../outlineColors'
import { showToast } from '../ui/Toast'

function volumeIdOf(node) {
  if (node?.ref != null) return node.ref
  const id = String(node?.id || '')
  if (!id.startsWith('vol:')) return null
  const raw = id.slice(4)
  return raw && raw !== 'null' ? raw : null
}

function chapterNode(chapter) {
  return {
    id: `ch:${chapter.seq}`,
    type: 'chapter',
    ref: chapter.seq,
    label: `${chapter.seq} ${chapter.title || ''}`.trim(),
    phase: 'outline',
  }
}

export function VolumeDetailPane({ node, onSelectNode, onChanged }) {
  const vid = volumeIdOf(node)
  const [outline, setOutline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ title: '', intro: '', color: '' })

  const reload = () => {
    setLoading(true)
    setErr('')
    return api.outline()
      .then((data) => {
        const nextOutline = data || { volumes: [], chapters: [] }
        const nextVolume = (nextOutline.volumes || [])
          .find((v) => String(v.id) === String(vid)) || null
        setOutline(nextOutline)
        setForm(vid == null
          ? { title: '', intro: '', color: '' }
          : {
              title: nextVolume?.title || node?.label || '未命名卷',
              intro: nextVolume?.intro || '',
              color: nextVolume?.color || '',
            })
        setErr('')
      })
      .catch((e) => {
        setOutline(null)
        setErr(e?.body?.detail || e?.message || '卷信息加载失败')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [vid]) // eslint-disable-line react-hooks/exhaustive-deps

  const volume = useMemo(() => {
    const volumes = outline?.volumes || []
    return volumes.find((v) => String(v.id) === String(vid)) || null
  }, [outline, vid])

  const chapters = useMemo(() => {
    const rows = outline?.chapters || []
    return rows.filter((c) => String(c.volume ?? '') === String(vid ?? ''))
  }, [outline, vid])

  const totalWords = chapters.reduce((sum, c) => sum + (c.word_count || 0), 0)
  const statusCounts = chapters.reduce((map, c) => {
    const key = c.label || '未设'
    map[key] = (map[key] || 0) + 1
    return map
  }, {})

  const save = async () => {
    if (!vid || saving) return
    const title = form.title.trim() || volume?.title || node?.label || '未命名卷'
    setSaving(true)
    try {
      await api.patchVolume(vid, { title, intro: form.intro, color: form.color || null })
      showToast('卷信息已保存', { tone: 'ok' })
      onChanged?.()
      await reload()
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '卷信息保存失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const createChapter = async () => {
    if (saving) return
    setSaving(true)
    try {
      const res = await api.createChapter({ volume: vid ?? null })
      showToast('章节已创建', { tone: 'ok' })
      onChanged?.()
      if (res?.seq != null) onSelectNode?.(chapterNode(res))
      else await reload()
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '新建章节失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const createFromUnassigned = async () => {
    if (vid != null || saving) return
    const title = form.title.trim()
    if (!title) {
      showToast('请先填写新卷名', { tone: 'warn' })
      return
    }
    const maxOrder = (outline?.volumes || []).reduce((max, v) => Math.max(max, v.sort_order ?? 0), 0)
    setSaving(true)
    try {
      const res = await api.addVolume(title, maxOrder + 1, form.color || null, form.intro)
      const newId = res?.id
      if (newId && chapters.length > 0) {
        await api.reorderChapters(newId, chapters.map((c) => c.seq))
      }
      showToast('分卷已创建', { tone: 'ok' })
      onChanged?.()
      if (newId) onSelectNode?.({ id: `vol:${newId}`, type: 'volume', ref: newId, label: title })
      else await reload()
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '创建分卷失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-8 text-f13 text-faint/60">加载卷信息…</div>
  if (err) {
    return (
      <div className="h-full grid place-items-center px-6 text-center">
        <div role="alert" className="max-w-md rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-f13 text-danger">
          <div>{err}</div>
          <button type="button" onClick={reload} className="mt-3 h-8 rounded-md border border-danger/30 px-3 text-f12">重试</button>
        </div>
      </div>
    )
  }
  if (vid == null) {
    return (
      <section data-testid="volume-detail-pane" className="h-full min-h-0 overflow-y-auto bg-canvas">
        <header className="border-b border-line bg-surface/90 px-6 py-4">
          <div className="text-meta font-semibold text-faint">手稿 / 未分卷</div>
          <div className="mt-1 flex min-w-0 items-center gap-3">
            <h2 className="min-w-0 flex-1 truncate text-f24 font-semibold leading-tight text-ink">{node?.label || '未分卷'}</h2>
            <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{chapters.length} 章</span>
            <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{wcLabel(totalWords)} 字</span>
          </div>
        </header>
        <div className="grid gap-5 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <section className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-2 text-f13 font-semibold text-ink">创建正式分卷</div>
            <div className="mb-4 text-f12 leading-relaxed text-faint">
              未分卷只是暂存分组。创建正式分卷后,这些章节会归入新卷,卷纲保存到新卷档案。
            </div>
            <div className="grid gap-3">
              <label className="grid gap-1 text-f12 text-faint">
                新卷名
                <input
                  aria-label="新卷名"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="第一卷"
                  className="h-9 rounded-md border border-line bg-canvas px-3 text-f13 text-ink outline-none focus:border-brand"
                />
              </label>
              <label className="grid gap-1 text-f12 text-faint">
                标识色
                <input
                  value={form.color}
                  onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
                  placeholder="#2f7563"
                  className="h-9 rounded-md border border-line bg-canvas px-3 text-f13 text-ink outline-none focus:border-brand"
                />
              </label>
              <label className="grid gap-1 text-f12 text-faint">
                新卷卷纲
                <textarea
                  aria-label="新卷卷纲"
                  value={form.intro}
                  onChange={(e) => setForm((f) => ({ ...f, intro: e.target.value }))}
                  rows={8}
                  placeholder="写这个新分卷的主冲突、角色弧线、伏笔收束。"
                  className="min-h-40 resize-y rounded-md border border-line bg-canvas px-3 py-2 text-f13 leading-relaxed text-ink outline-none focus:border-brand"
                />
              </label>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={createFromUnassigned}
                  disabled={saving}
                  className="h-9 rounded-md bg-brand px-4 text-f13 font-medium text-brandfg disabled:opacity-50"
                >
                  {saving ? '创建中…' : '创建分卷'}
                </button>
              </div>
            </div>
          </section>
          <aside className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-3 text-f13 font-semibold text-ink">将收纳章节</div>
            <div className="grid gap-1.5">
              {chapters.length === 0 ? (
                <div className="text-f12 text-faint">暂无未分卷章节。</div>
              ) : chapters.map((chapter) => (
                <button
                  key={chapter.seq}
                  type="button"
                  onClick={() => onSelectNode?.(chapterNode(chapter))}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-1.5 text-left text-f12 hover:bg-hover"
                >
                  <span className="min-w-0 truncate text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                  <span className="text-faint">{wcLabel(chapter.word_count)} 字</span>
                </button>
              ))}
            </div>
          </aside>
        </div>
      </section>
    )
  }

  if (!volume) {
    return (
      <div className="h-full grid place-items-center px-6 text-center text-f13 text-faint/60">
        该分卷还没有可编辑的卷记录。
      </div>
    )
  }

  return (
    <section data-testid="volume-detail-pane" className="h-full min-h-0 overflow-y-auto bg-canvas">
      <header className="border-b border-line bg-surface/90 px-6 py-4">
        <div className="text-meta font-semibold text-faint">手稿 / 分卷</div>
        <div className="mt-1 flex min-w-0 items-center gap-3">
          <h2 className="min-w-0 flex-1 truncate text-f24 font-semibold leading-tight text-ink">{volume.title || node.label || '未命名卷'}</h2>
          <span className="rounded-full bg-brand/10 px-2.5 py-1 text-meta text-brand">{chapters.length} 章</span>
          <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{wcLabel(totalWords)} 字</span>
        </div>
      </header>

      <div className="grid gap-5 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0 space-y-5">
          <section className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-3 text-f13 font-semibold text-ink">卷信息</div>
            <div className="grid gap-3">
              <label className="grid gap-1 text-f12 text-faint">
                卷名
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="h-9 rounded-md border border-line bg-canvas px-3 text-f13 text-ink outline-none focus:border-brand"
                />
              </label>
              <label className="grid gap-1 text-f12 text-faint">
                标识色
                <input
                  value={form.color}
                  onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
                  placeholder="#2f7563"
                  className="h-9 rounded-md border border-line bg-canvas px-3 text-f13 text-ink outline-none focus:border-brand"
                />
              </label>
              <label className="grid gap-1 text-f12 text-faint">
                卷纲
                <textarea
                  aria-label="卷纲"
                  value={form.intro}
                  onChange={(e) => setForm((f) => ({ ...f, intro: e.target.value }))}
                  rows={9}
                  placeholder="写本卷的主冲突、角色弧线、伏笔收束、情绪走向。"
                  className="min-h-44 resize-y rounded-md border border-line bg-canvas px-3 py-2 text-f13 leading-relaxed text-ink outline-none focus:border-brand"
                />
              </label>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="h-9 rounded-md bg-brand px-4 text-f13 font-medium text-brandfg disabled:opacity-50"
                >
                  {saving ? '保存中…' : '保存卷信息'}
                </button>
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-f13 font-semibold text-ink">本卷章节</div>
              <div className="flex shrink-0 items-center gap-2">
                <div className="text-meta text-faint">{chapters.length} 章 · {wcLabel(totalWords)} 字</div>
                <button
                  type="button"
                  onClick={createChapter}
                  disabled={saving}
                  className="h-8 rounded-md bg-brand px-3 text-f12 font-medium text-brandfg disabled:opacity-50"
                >
                  新建章
                </button>
              </div>
            </div>
            <div className="grid gap-1.5">
              {chapters.length === 0 ? (
                <div className="py-8 text-center text-f13 text-faint/60">本卷暂无章节。</div>
              ) : chapters.map((chapter) => (
                <button
                  key={chapter.seq}
                  type="button"
                  onClick={() => onSelectNode?.(chapterNode(chapter))}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 rounded-md px-3 py-2 text-left text-f13 hover:bg-hover"
                >
                  <span className="min-w-0 truncate font-medium text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                  <span className="text-meta text-faint">{chapter.label || '未设'}</span>
                  <span className="text-meta text-faint">{wcLabel(chapter.word_count)} 字</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="min-w-0 space-y-3">
          <section className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-2 text-f13 font-semibold text-ink">卷概览</div>
            <div className="grid gap-2 text-f12">
              <div className="flex justify-between gap-3"><span className="text-faint">章节</span><span className="text-ink">{chapters.length}</span></div>
              <div className="flex justify-between gap-3"><span className="text-faint">字数</span><span className="text-ink">{wcLabel(totalWords)} 字</span></div>
              <div className="flex justify-between gap-3"><span className="text-faint">排序</span><span className="text-ink">{volume.sort_order ?? '未设'}</span></div>
            </div>
          </section>
          <section className="rounded-lg border border-line bg-surface px-4 py-4">
            <div className="mb-2 text-f13 font-semibold text-ink">状态分布</div>
            <div className="grid gap-1.5 text-f12">
              {Object.keys(statusCounts).length === 0 ? (
                <div className="text-faint">暂无章节状态。</div>
              ) : Object.entries(statusCounts).map(([label, count]) => (
                <div key={label} className="flex justify-between gap-3">
                  <span className="text-faint">{label}</span>
                  <span className="text-ink">{count}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </section>
  )
}
