import { useMemo, useState } from 'react'
import { Plus, Search, BookText, Trash2 } from 'lucide-react'
import { api } from './api'
import { Btn } from './ui'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'

// 作品库:书卡网格(章数/字数/进度)+ 搜索 + 建 + 删。借鉴 scribe2 Library。
export function Library({ works, reload, onSelect }) {
  const [title, setTitle] = useState('')
  const [q, setQ] = useState('')
  const [delTarget, setDelTarget] = useState(null)
  const toast = useToast()

  const create = async () => {
    if (!title.trim()) return
    const r = await api.createWork(title.trim())
    setTitle(''); await reload(); onSelect({ slug: r.slug, title: r.title })
  }
  const del = (e, w) => {
    e.stopPropagation()
    if (w.slug === 'main') { toast('主书不可删除', { tone: 'danger' }); return }
    setDelTarget(w)
  }
  const list = useMemo(() => (works || []).filter((w) => !q.trim() || w.title.includes(q.trim())), [works, q])

  return (
    <>
    <ConfirmDialog
      open={!!delTarget}
      title={`删除《${delTarget?.title ?? ''}》?`}
      body="该书所有内容(角色/设定/章节)将永久丢失。"
      danger
      confirmText="删除"
      onConfirm={async () => { await api.deleteWork(delTarget.slug); reload() }}
      onClose={() => setDelTarget(null)}
    />
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-4xl mx-auto px-8 py-10">
        <h1 className="prose-serif text-f26 font-semibold text-ink mb-1">作品库</h1>
        <p className="text-faint text-f13 mb-6">每本书独立一库,角色/设定/章节/伏笔互不干扰。</p>

        <div className="flex items-center gap-2 h-10 rounded-xl border border-line bg-surface px-3 mb-5 max-w-md">
          <Search size={15} className="text-faint shrink-0" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索作品…"
            className="flex-1 bg-transparent text-f14 text-ink outline-none placeholder:text-faint/60" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {list.map((w) => {
            const words = w.word_count ?? 0
            const goal = w.total_word_goal ?? 100000  // /works 携带真目标;无则回退默认值
            const pct = Math.min(100, Math.round((words / goal) * 100))
            return (
              <button key={w.slug} onClick={() => onSelect(w)}
                className="group relative text-left rounded-xl border border-line bg-surface p-4 hover:border-brand/50 hover:shadow-sm transition-all cursor-pointer flex flex-col gap-2.5 min-h-[124px]">
                <div className="flex items-start gap-2">
                  <BookText size={16} className="text-brand shrink-0 mt-0.5" />
                  <span className="prose-serif text-f15 font-semibold text-ink leading-snug min-w-0 break-words">{w.title}</span>
                  {w.slug !== 'main' && (
                    <span onClick={(e) => del(e, w)} title="删除作品"
                      className="ml-auto shrink-0 w-6 h-6 rounded-md text-faint/0 group-hover:text-faint hover:!text-danger hover:bg-danger/10 inline-flex items-center justify-center transition-colors">
                      <Trash2 size={13} />
                    </span>
                  )}
                </div>
                <div className="text-f12 text-faint tnum">{w.chapter_count ?? 0} 章 · {words.toLocaleString()} 字</div>
                <div className="mt-auto">
                  <div className="h-1.5 rounded-full bg-soft overflow-hidden">
                    <div className="h-full bg-brand rounded-full transition-all" style={{ width: pct + '%' }} />
                  </div>
                  <div className="text-f10 text-faint mt-1 tnum">约 {pct}% · 目标 {(goal / 10000).toLocaleString()} 万字</div>
                </div>
              </button>
            )
          })}
        </div>

        <div className="mt-7 max-w-md">
          <div className="text-f11 font-semibold uppercase tracking-wider text-faint mb-2">新建作品</div>
          <div className="flex gap-2">
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="书名…"
              onKeyDown={(e) => { if (e.key === 'Enter') create() }}
              className="flex-1 h-10 rounded-xl border border-line bg-surface px-3 text-f14 text-ink outline-none focus:border-brand placeholder:text-faint/60" />
            <Btn variant="primary" size="md" className="h-10 px-4" onClick={create}><Plus size={15} />建</Btn>
          </div>
        </div>
      </div>
    </div>
    </>
  )
}
